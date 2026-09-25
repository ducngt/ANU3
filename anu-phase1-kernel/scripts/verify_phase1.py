from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.db import DecisionRecord, make_engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "verification"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT) + os.pathsep + merged.get("PYTHONPATH", "")
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=ROOT, env=merged, text=True, capture_output=True)


def migration_cycle(database_url: str) -> tuple[bool, str]:
    old = os.environ.get("ANU_DATABASE_URL")
    os.environ["ANU_DATABASE_URL"] = database_url
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        return True, "upgrade -> downgrade -> upgrade PASS at revision 0002"
    except Exception as exc:
        return False, repr(exc)
    finally:
        if old is None:
            os.environ.pop("ANU_DATABASE_URL", None)
        else:
            os.environ["ANU_DATABASE_URL"] = old


def postgres_offline_sql() -> tuple[bool, str]:
    proc = run(
        ["alembic", "upgrade", "head", "--sql"],
        {"ANU_DATABASE_URL": "postgresql://anu:anu@localhost/anu"},
    )
    sql = proc.stdout
    ok = proc.returncode == 0 and "CREATE TABLE trust_credential" in sql and "CREATE TABLE agent_attestation" in sql
    return ok, (sql[-4000:] + proc.stderr[-2000:]).strip()


def backup_restore_evidence(source_url: str, tmp: Path) -> tuple[bool, dict]:
    backup_path = tmp / "anu-backup.db"
    restored_path = tmp / "anu-restored.db"
    restored_url = f"sqlite+pysqlite:///{restored_path}"
    try:
        backup = backup_database(source_url, backup_path)
        restore = restore_database(backup_path, restored_url)
        engine = make_engine(restored_url)
        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            decision_count = session.scalar(select(func.count()).select_from(DecisionRecord)) or 0
        ok = decision_count >= 1
        return ok, {"backup": backup, "restore": restore, "decision_count_after_restore": decision_count}
    except Exception as exc:
        return False, {"error": repr(exc)}


def main() -> int:
    checks: dict[str, str] = {}
    details: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="anu-p1-t03-") as tmp_name:
        tmp = Path(tmp_name)
        db_path = tmp / "verification.db"
        db_url = f"sqlite+pysqlite:///{db_path}"

        ok, detail = migration_cycle(db_url)
        checks["clean_migration_cycle"] = "PASS" if ok else "FAIL"
        details["clean_migration_cycle"] = detail

        tests = run([sys.executable, "-m", "pytest", "-q"])
        checks["automated_tests"] = "PASS" if tests.returncode == 0 else "FAIL"
        details["automated_tests"] = (tests.stdout + tests.stderr).strip()

        trust_pilot_path = tmp / "trust-pilot.json"
        pilot = run([
            sys.executable, "scripts/aru01_trust_pilot.py", "--database-url", db_url,
            "--output", str(trust_pilot_path),
        ])
        checks["aru01_trust_chain_pilot"] = "PASS" if pilot.returncode == 0 else "FAIL"
        details["aru01_trust_chain_pilot"] = (pilot.stdout + pilot.stderr).strip()

        schemas = run([sys.executable, "scripts/export_schemas.py"])
        checks["contract_schema_export"] = "PASS" if schemas.returncode == 0 else "FAIL"
        details["contract_schema_export"] = (schemas.stdout + schemas.stderr).strip()

        pg_ok, pg_detail = postgres_offline_sql()
        checks["postgresql_offline_migration_compile"] = "PASS" if pg_ok else "FAIL"
        details["postgresql_offline_migration_compile"] = pg_detail

        br_ok, br_detail = backup_restore_evidence(db_url, tmp)
        checks["backup_restore_reference"] = "PASS" if br_ok else "FAIL"
        details["backup_restore_reference"] = br_detail

    local_ok = all(v == "PASS" for v in checks.values())
    status = {
        "work_id": "P1-T03-TRUST-AUTHN-HARDENING",
        "status": "LOCAL_VERIFIED_AWAITING_LIVE_POSTGRES" if local_ok else "BLOCKED_TECHNICAL_VERIFICATION",
        "human_gate": "G3_NOT_READY",
        "summary": (
            "Tranche 03 implementation and local verification are complete. Live PostgreSQL migration/backup/restore verification is configured for CI but cannot be executed in the current isolated runtime, so no Human acceptance decision is requested yet."
            if local_ok else
            "Tranche 03 has technical verification failures. Human action is not required; AI must resolve the technical blockers."
        ),
        "checks": checks,
        "external_checks": {
            "live_postgresql_migration": "PENDING_EXTERNAL_CI",
            "live_postgresql_aru01_trust_pilot": "PENDING_EXTERNAL_CI",
            "live_postgresql_backup_restore": "PENDING_EXTERNAL_CI",
        },
        "known_limitations": [
            "The JWT-HS256 authentication adapter is a reference IdP adapter boundary, not an institutional production IdP configuration.",
            "Trust Registry currently validates Ed25519 public-key credentials; certificate-chain, qualified signature and legal-signature profiles remain specification/provider concerns.",
            "Live PostgreSQL runtime evidence requires an environment with PostgreSQL and psycopg; the release includes CI automation for that check, but this isolated build environment has no PostgreSQL runtime/client.",
            "Tranche 03 is not ready for Human G3 until the external PostgreSQL CI evidence is attached and independently verified.",
        ],
        "human_action": "None. This is a technical blocked queue item; AI/CI must complete live PostgreSQL verification before presenting G3.",
    }
    (OUT / "LATEST.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "TECHNICAL-DETAILS-P1-T03.json").write_text(
        json.dumps({"checks": checks, "details": details}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = """# Phase 1 Tranche 03 — G3 Readiness Report

## Status

**G3_NOT_READY — awaiting live PostgreSQL CI evidence.**

No Human technical action is required. The remaining blocker is environmental/technical verification, not a meaning/authority/policy decision.

## Architecture delta

- Added an explicit AuthN adapter boundary that maps verified external credentials to ANU Identity without granting Authority.
- Added a Policy Enforcement Point that composes Authentication + Authority/Delegation + versioned Policy and fails closed.
- Added Trust Registry primitives for public-key credential metadata.
- Added Human Signature verification with independent checks for credential, active role, authority and cryptographic integrity.
- Added Agent Attestation verification with active delegation enforcement for consequential actions.
- Added deterministic artifact integrity hashing.
- Removed eager runtime engine creation so offline migration/architecture tooling does not require a database driver.
- Added backup/restore adapters for SQLite reference environments and PostgreSQL production-target environments.

## Invariants explicitly tested

- `AUTHENTICATION != AUTHORIZATION`
- `AUTHENTICATION != SIGNATURE`
- `SIGNATURE != AUTHORITY`
- `AGENT IDENTITY != PERMANENT AUTHORITY`
- `AGENT ATTESTATION != HUMAN APPROVAL`
- tampering invalidates signature verification
- delegation revocation prevents future consequential Agent attestation

## Verification evidence

"""
    for name, value in checks.items():
        report += f"- {name}: **{value}**\n"
    report += """

## External verification still required

The repository now contains GitHub Actions automation for live PostgreSQL migration, ARU-01 trust-chain pilot and PostgreSQL backup/restore. Those checks cannot be honestly marked PASS from the current isolated runtime because PostgreSQL binaries/service are unavailable here.

## Human decision

**None at this time.** The Handbook requires the AI/CI lane to clear the technical blocked queue before asking Human for G3 acceptance.
"""
    (OUT / "G3-READINESS-P1-T03.md").write_text(report, encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

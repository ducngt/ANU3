from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "verification" / "LATEST.json"


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/independent"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    result = {
        "independent_verifier": "PASS" if proc.returncode == 0 else "FAIL",
        "output": (proc.stdout + proc.stderr).strip(),
    }
    if LATEST.exists():
        status = json.loads(LATEST.read_text(encoding="utf-8"))
        status.setdefault("checks", {})["independent_verifier"] = result["independent_verifier"]
        if proc.returncode != 0:
            status["status"] = "BLOCKED_INDEPENDENT_VERIFICATION"
            status["human_gate"] = "G3_NOT_READY"
            status["human_action"] = "No Human technical action. AI must resolve independent verification failures."
        LATEST.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = ROOT / "docs" / "verification" / "G3-READINESS-P1-T03.md"
        if not report.exists():
            report = ROOT / "docs" / "verification" / "G3-ACCEPTANCE-REPORT.md"
        if report.exists():
            text = report.read_text(encoding="utf-8")
            marker = "- independent_verifier: **"
            line = f"- independent_verifier: **{result['independent_verifier']}**\n"
            if marker not in text:
                text = text.replace("## Security / trust analysis", line + "\n## Security / trust analysis")
            report.write_text(text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

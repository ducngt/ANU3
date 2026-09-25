from __future__ import annotations

import argparse
import json

from anu_kernel.backup import backup_database, restore_database


def main() -> int:
    parser = argparse.ArgumentParser(description="ANU Phase-1 backup/restore adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--database-url", required=True)
    b.add_argument("--output", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--backup", required=True)
    r.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if args.command == "backup":
        result = backup_database(args.database_url, args.output)
    else:
        result = restore_database(args.backup, args.database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

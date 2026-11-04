"""Inspect non-secret deployment paths without connecting to any service."""
import argparse
import json
import sys
from pathlib import Path

from crm.services.operations_readiness import inspect_config


def main():
    parser = argparse.ArgumentParser(description="只读检查；不执行或授权备份")
    parser.add_argument("--config", required=True, help="不含凭据的 JSON 配置路径")
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = inspect_config(config)
    except (OSError, ValueError, UnicodeError):
        result = {"ok": False, "errors": ["配置无法读取或不是有效 JSON"], "warnings": [], "backup_authorized": False}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

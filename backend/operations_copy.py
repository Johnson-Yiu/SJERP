"""Create a verified exclusive backup copy; never delete an existing backup."""
import argparse
import json
import sys

from crm.services.operations_copy import verified_copy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        result = verified_copy(args.source, args.destination, args.sha256)
    except Exception as error:
        # Paths and OS exception details may expose deployment information.
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"status": "VERIFIED_COPY", **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

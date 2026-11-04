import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase

from crm.services.operations_trust import load_receipt_trust


class ReceiptTrustTests(TestCase):
    def test_operator_writable_trust_anchor_never_accepted(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-untrusted-anchor-") as folder:
            root = Path(folder)
            anchor = root / "trust.json"
            anchor.write_text(json.dumps({"executable": "/synthetic", "public_key": "/synthetic",
                                          "pinned_fingerprint": "a" * 64, "max_age_seconds": 3600}), encoding="utf-8")
            # On Windows the independent ownership check itself fails closed.
            # On Linux, even root running tests must reject writable parents.
            root.chmod(0o777)
            try:
                with self.assertRaises((ValueError, RuntimeError)):
                    load_receipt_trust(anchor)
            finally:
                root.chmod(0o700)

    def test_relative_anchor_never_accepted(self):
        with self.assertRaises((ValueError, RuntimeError)):
            load_receipt_trust("relative-trust.json")

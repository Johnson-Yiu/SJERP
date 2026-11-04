from unittest import TestCase
from unittest.mock import Mock

from crm.services.operations_postgres import verify_media_references


class FinanceBackupReferenceTests(TestCase):
    def verify(self, rows, files):
        connection = Mock()
        connection.execute.side_effect = [[], [], [], [], rows]
        return verify_media_references(connection, {"files": files})

    def test_matching_private_voucher_is_counted(self):
        self.assertEqual(self.verify(
            [("finance-vouchers/synthetic.pdf", 17, "a" * 64)],
            [{"path": "finance-vouchers/synthetic.pdf", "size": 17, "sha256": "a" * 64}]), 1)

    def test_missing_or_changed_private_voucher_refuses(self):
        rows = [("finance-vouchers/synthetic.pdf", 17, "a" * 64)]
        for files in ([],
                      [{"path": rows[0][0], "size": 18, "sha256": "a" * 64}],
                      [{"path": rows[0][0], "size": 17, "sha256": "b" * 64}]):
            with self.subTest(files=files), self.assertRaises(RuntimeError):
                self.verify(rows, files)

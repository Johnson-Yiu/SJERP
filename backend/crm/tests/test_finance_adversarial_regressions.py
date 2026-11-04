"""Run the delivered adversarial defect assertions in ordinary test discovery.

The historical reproduction file remains unchanged, including its original
failure evidence. These imports expose its TestCase classes to Django's loader.
"""
import importlib.util
from pathlib import Path


_source = (
    Path(__file__).resolve().parents[3]
    / "docs/uat-evidence/finance-adversarial-review-20261104/defect_repros.py"
)
_spec = importlib.util.spec_from_file_location("finance_delivered_defect_repros", _source)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

ConfirmedDefectReproductions = _module.ConfirmedDefectReproductions
AuthorizedRoleDefectReproduction = _module.AuthorizedRoleDefectReproduction

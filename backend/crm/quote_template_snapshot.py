"""Capture and validate the exact template assets used by saved quotations."""

import base64
import hashlib
import hmac
import json
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from .quotation_template_config import quotation_templates


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRINT_TEMPLATE_PATH = Path(__file__).resolve().parent / "pi_print_template.html"


class QuoteTemplateSnapshotError(ValueError):
    """A template is unavailable, incomplete, or fails its integrity check."""


def _metadata_digest(snapshot):
    values = {key: snapshot[key] for key in (
        "version", "template_id", "config", "sha256", "seller", "bank", "notice", "print_template", "print_sha256"
    )}
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def capture_template(template_id):
    """Capture bytes and rendering configuration together at the save boundary."""
    try:
        config = quotation_templates[template_id]
        content = (PROJECT_ROOT / config.file).read_bytes()
        print_template = PRINT_TEMPLATE_PATH.read_text(encoding="utf-8")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            sheet = workbook[config.sheet]
            seller = dict(zip(
                ("name", "saler", "address", "email", "phone"),
                (str(sheet[f"I{row}"].value or "") for row in range(3, 8)),
            ))
            start = config.lower_block.rows["bank_header"] + 1
            bank = [[str(sheet[f"A{row}"].value or ""), str(sheet[f"C{row}"].value or "")]
                    for row in range(start, start + 9)]
            notice = str(sheet[f"A{start + 9}"].value or "")
        finally:
            workbook.close()
    except (KeyError, OSError, ValueError) as exc:
        raise QuoteTemplateSnapshotError("报价模板不可用，请检查模板配置。") from exc
    if not seller["name"]:
        raise QuoteTemplateSnapshotError("报价模板缺少卖方名称。")
    snapshot = {
        "version": 1,
        "template_id": template_id,
        "config": json.loads(json.dumps(asdict(config))),
        "bytes_base64": base64.b64encode(content).decode("ascii"),
        "sha256": hashlib.sha256(content).hexdigest(),
        "seller": seller,
        "bank": bank,
        "notice": notice,
        "print_template": print_template,
        "print_sha256": hashlib.sha256(print_template.encode("utf-8")).hexdigest(),
    }
    snapshot["metadata_sha256"] = _metadata_digest(snapshot)
    return snapshot


def validated_template_bytes(snapshot):
    """Fail closed when a saved asset is missing or has been corrupted."""
    try:
        if snapshot["version"] != 1 or not snapshot["seller"]["name"]:
            raise ValueError("missing seller or unsupported version")
        content = base64.b64decode(snapshot["bytes_base64"], validate=True)
        expected = snapshot["sha256"]
        if not isinstance(expected, str) or not hmac.compare_digest(
            hashlib.sha256(content).hexdigest(), expected
        ):
            raise ValueError("digest mismatch")
        if not isinstance(snapshot["config"], dict):
            raise ValueError("missing configuration")
        if not hmac.compare_digest(hashlib.sha256(snapshot["print_template"].encode("utf-8")).hexdigest(), snapshot["print_sha256"]):
            raise ValueError("print template digest mismatch")
        if not hmac.compare_digest(_metadata_digest(snapshot), snapshot["metadata_sha256"]):
            raise ValueError("metadata digest mismatch")
        return content
    except (KeyError, TypeError, ValueError) as exc:
        raise QuoteTemplateSnapshotError("报价的卖方或模板来源缺失或损坏，需核实原件。") from exc


def resolve_quote_template(quote, template_id):
    from .models import QuoteTemplateAsset
    digest = (quote.pi_template_snapshots or {}).get(template_id)
    if not isinstance(digest, str):
        raise QuoteTemplateSnapshotError("报价的卖方或模板来源缺失或损坏，需核实原件。")
    asset = QuoteTemplateAsset.objects.filter(pk=digest).first()
    if asset is None:
        raise QuoteTemplateSnapshotError("报价的卖方或模板来源缺失或损坏，需核实原件。")
    snapshot = asset.snapshot
    validated_template_bytes(snapshot)
    if snapshot["template_id"] != template_id or not hmac.compare_digest(snapshot["metadata_sha256"], digest):
        raise QuoteTemplateSnapshotError("报价模板版本校验失败，需核实原件。")
    return snapshot

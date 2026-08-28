import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings

from .quotation_export_dto import build_quotation_export_dto


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKER_PATH = PROJECT_ROOT / "scripts" / "generate_quote_xlsx.mjs"
TWO_PLACES = Decimal("0.01")


class QuoteExportError(Exception):
    pass


def _whole_number_words(value):
    if value == 0:
        return "ZERO"

    ones = [
        "", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
        "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
        "SEVENTEEN", "EIGHTEEN", "NINETEEN",
    ]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]

    def below_thousand(number):
        words = []
        if number >= 100:
            words.extend([ones[number // 100], "HUNDRED"])
            number %= 100
        if number >= 20:
            words.append(tens[number // 10])
            if number % 10:
                words.append(ones[number % 10])
        elif number:
            words.append(ones[number])
        return words

    words = []
    for divisor, label in ((1_000_000_000, "BILLION"), (1_000_000, "MILLION"), (1_000, "THOUSAND")):
        if value >= divisor:
            words.extend(below_thousand(value // divisor))
            words.append(label)
            value %= divisor
    words.extend(below_thousand(value))
    return " ".join(words)


def _amount_words(amount, currency):
    rounded = Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    whole = int(rounded)
    cents = int((rounded - whole) * 100)
    currency_name = {
        "USD": "US DOLLARS",
        "EUR": "EUROS",
        "GBP": "POUNDS STERLING",
        "CNY": "CHINA YUAN",
        "RMB": "CHINA YUAN",
    }.get(currency.upper(), currency.upper())
    words = f"SAY TOTAL {currency_name} {_whole_number_words(whole)}"
    if cents:
        words += f" AND CENTS {_whole_number_words(cents)}"
    return f"{words} ONLY"


def build_pi_export_payload(quote, *, template_id=None):
    """Render a saved quotation through the selected workbook template."""
    dto = build_quotation_export_dto(quote, template_id=template_id)
    total_amount = Decimal(dto.totals["total_amount"])
    if total_amount < 0:
        raise QuoteExportError("PI total amount cannot be negative.")
    payload = dto.as_renderer_payload()
    payload["totals"]["amount_words"] = _amount_words(total_amount, quote.currency)
    temporary = tempfile.TemporaryDirectory(prefix="quote-export-")
    try:
        temporary_path = Path(temporary.name)
        input_path = temporary_path / "payload.json"
        output_path = temporary_path / f"{quote.quote_no}.xlsx"
        input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        node_binary = getattr(settings, "QUOTE_XLSX_NODE_BINARY", None) or os.environ.get("QUOTE_XLSX_NODE_BINARY") or "node"
        try:
            completed = subprocess.run(
                [
                    node_binary,
                    str(WORKER_PATH),
                    "--input-json",
                    str(input_path),
                    "--output-xlsx",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise QuoteExportError("PI workbook generation could not start.") from exc

        if completed.returncode != 0 or not output_path.is_file():
            detail = (completed.stderr or completed.stdout or "Unknown worker error").strip()[-1000:]
            raise QuoteExportError(f"PI workbook generation failed: {detail}")
        return output_path.read_bytes()
    finally:
        temporary.cleanup()

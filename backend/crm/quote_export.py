import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings


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


def _money(value):
    return str(Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def _export_payload(quote):
    products = []
    subtotal = Decimal("0")
    for item in quote.items.all():
        amount = item.amount
        subtotal += amount
        image_path = ""
        if item.image_snapshot:
            try:
                image_path = item.image_snapshot.path
            except (NotImplementedError, ValueError):
                image_path = ""
        products.append({
            "sku": item.sales_model_snapshot,
            "model": item.sales_model_snapshot,
            "sku_code": item.sku_code_snapshot,
            "product_name": item.product_name_snapshot,
            "description": item.description or item.product_name_snapshot,
            "quantity": str(item.quantity),
            "unit": item.unit_snapshot,
            "unit_price": str(item.unit_price),
            "amount": _money(amount),
            "image_path": image_path,
        })

    total_amount = Decimal(quote.total_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    if total_amount < 0:
        raise QuoteExportError("PI total amount cannot be negative.")
    deposit_amount = (total_amount * quote.deposit_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    balance_amount = total_amount - deposit_amount
    validity_days = (quote.valid_until - quote.quote_date).days if quote.valid_until else 30
    return {
        "invoice_no": quote.quote_no,
        "buyer": {
            "company_name": quote.buyer_company_name,
            "recipient": quote.recipient_name,
            "address": quote.buyer_address,
            "tax_id": "",
            "email": quote.buyer_email,
            "phone": quote.buyer_phone,
        },
        "terms": {
            "quote_date": quote.quote_date.isoformat(),
            "validity_days": max(validity_days, 0),
            "lead_time_days": quote.lead_time_days or 10,
            "trading_terms": quote.trading_terms,
            "shipping_details": quote.shipping_details,
            "notes": quote.notes,
        },
        "totals": {
            "currency": quote.currency,
            "subtotal": _money(subtotal),
            "shipping_fee": _money(quote.shipping_fee),
            "discount": _money(quote.discount),
            "total_amount": _money(total_amount),
            "amount_words": _amount_words(total_amount, quote.currency),
        },
        "payment_splits": {
            "deposit_ratio": str(quote.deposit_ratio),
            "deposit_amount": _money(deposit_amount),
            "balance_ratio": str(Decimal("1") - quote.deposit_ratio),
            "balance_amount": _money(balance_amount),
        },
        "products": products,
    }


def build_pi_export_payload(quote):
    temporary = tempfile.TemporaryDirectory(prefix="quote-export-")
    try:
        temporary_path = Path(temporary.name)
        input_path = temporary_path / "payload.json"
        output_path = temporary_path / f"{quote.quote_no}.xlsx"
        input_path.write_text(json.dumps(_export_payload(quote), ensure_ascii=False), encoding="utf-8")

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

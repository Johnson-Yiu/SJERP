"""Capture actual HTTP PI preview/export responses from the isolated server."""
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openpyxl import load_workbook

out = Path(__file__).resolve().parent
fixture = json.loads((out / "fixture.json").read_text(encoding="utf-8"))
base = os.environ.get("ISS020_BASE_URL", "http://127.0.0.1:28341")


def get(path):
    request = Request(f"{base}{path}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.headers, response.read()
    except HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def export(quote_id, filename):
    status, headers, content = get(f"/api/quotes/{quote_id}/export/")
    if status == 200:
        (out / filename).write_bytes(content)
        workbook = load_workbook(io.BytesIO(content), data_only=False)
        sheet = workbook["PI"]
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            media = [name for name in archive.namelist() if name.startswith("xl/media/")]
        amount_cell = next((cell.value for cell in (sheet["A15"], sheet["A16"]) if cell.value and "SAY TOTAL" in str(cell.value)), None)
        formula_cells = [
            cell.coordinate
            for row in sheet.iter_rows()
            for cell in row
            if isinstance(cell.value, str) and cell.value.startswith("=")
        ]
        return {
            "status": status,
            "content_type": headers.get_content_type(),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "file": filename,
            "quote_no": sheet["L9"].value,
            "buyer": sheet["B3"].value,
            "recipient": sheet["B4"].value,
            "email": sheet["B7"].value,
            "currency_header": sheet["L10"].value,
            "amount_words": amount_cell,
            "media": media,
            "formula_cells": formula_cells,
            "print_area": str(sheet.print_area),
            "page_orientation": sheet.page_setup.orientation,
            "fit_to_width": sheet.page_setup.fitToWidth,
            "fit_to_height": sheet.page_setup.fitToHeight,
        }
    return {"status": status, "content_type": headers.get_content_type(), "bytes": len(content), "body": content.decode("utf-8", "replace")}


def json_get(path):
    status, headers, content = get(path)
    return {"status": status, "content_type": headers.get_content_type(), "body": json.loads(content.decode("utf-8"))}


result = {
    "base_url": base,
    "root_pi_data": json_get(f"/api/quotes/{fixture['root_quote']}/pi-data/"),
    "revision_pi_data": json_get(f"/api/quotes/{fixture['revision_quote']}/pi-data/"),
    "root_export": export(fixture["root_quote"], "version-a.xlsx"),
    "revision_export": export(fixture["revision_quote"], "version-b-empty-email.xlsx"),
    "incomplete_export": export(fixture["incomplete_quote"], "incomplete-no-file.xlsx"),
}
(out / "api-evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))

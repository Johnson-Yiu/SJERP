import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function argumentValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1 || !process.argv[index + 1]) {
    throw new Error(`Missing required argument: ${name}`);
  }
  return process.argv[index + 1];
}


function percentText(value) {
  const percent = Number(value) * 100;
  return Number.isInteger(percent) ? `${percent}%` : `${percent.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}%`;
}


function currencyAmount(currency, value) {
  return `${currency} ${Number(value).toFixed(2)}`;
}


function notesText(payload) {
  const { terms, payment_splits: payment, totals } = payload;
  const rows = [
    "NOTES:",
    `1. Lead time: ${terms.lead_time_days} Days`,
    `2. Price Valid Date: ${terms.validity_days} Days.`,
    "3. Payment terms:",
    `${percentText(payment.deposit_ratio)} (${currencyAmount(totals.currency, payment.deposit_amount)}) payment in advance, `
      + `${percentText(payment.balance_ratio)} (${currencyAmount(totals.currency, payment.balance_amount)}) balance payment should be paid before shipping`,
    `4. Trading terms: ${terms.trading_terms || "N/A"}`,
    `5. Shipping details: ${terms.shipping_details || "N/A"}`,
    "6. The price is EXCLUDE customs duties and VAT. If the goods generate the customs taxes and VAT taxes in buyer's local, the buyer should pay by themselves.",
  ];
  if (terms.notes) rows.push(`7. Additional notes: ${terms.notes}`);
  return rows.join("\n");
}


async function addProductImage(sheet, imagePath, rowNumber) {
  if (!imagePath) return;
  try {
    const bytes = await fs.readFile(imagePath);
    const extension = path.extname(imagePath).toLowerCase();
    const mimeType = {
      ".gif": "image/gif",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".webp": "image/webp",
    }[extension];
    if (!mimeType) return;
    sheet.images.add({
      dataUrl: `data:${mimeType};base64,${bytes.toString("base64")}`,
      anchor: {
        from: { row: rowNumber - 1, col: 1, rowOffsetPx: 4, colOffsetPx: 4 },
        extent: { widthPx: 120, heightPx: 90 },
      },
    });
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}


function expandProductArea(sheet, additionalRows) {
  if (additionalRows <= 0) return;

  const lowerBlockValues = sheet.getRange("A13:M34").values;
  const lowerBlockMerges = [
    "A13:L13",
    "A14:L14",
    "A15:M15",
    "A16:M20",
    "A21:M21",
    ...Array.from({ length: 9 }, (_, index) => `A${22 + index}:B${22 + index}`),
    ...Array.from({ length: 9 }, (_, index) => `C${22 + index}:M${22 + index}`),
    "A31:M33",
    "A34:M34",
  ];
  for (const range of lowerBlockMerges) sheet.unmergeCells(range);

  for (let sourceRow = 34; sourceRow >= 13; sourceRow -= 1) {
    sheet.getRange(`A${sourceRow + additionalRows}:M${sourceRow + additionalRows}`).copyFrom(
      sheet.getRange(`A${sourceRow}:M${sourceRow}`),
      "all",
    );
  }
  sheet.getRange(`A${13 + additionalRows}:M${34 + additionalRows}`).values = lowerBlockValues;

  for (let index = 0; index < additionalRows; index += 1) {
    const rowNumber = 13 + index;
    sheet.getRange(`A${rowNumber}:M${rowNumber}`).copyFrom(sheet.getRange("A12:M12"), "all");
    sheet.mergeCells(`D${rowNumber}:I${rowNumber}`);
    sheet.getRange(`A${rowNumber}:M${rowNumber}`).format = {
      fill: "#FF0000",
      font: { name: "Arial", size: 11 },
      borders: { preset: "all", style: "thin", color: "#000000" },
      horizontalAlignment: "center",
      verticalAlignment: "center",
      wrapText: true,
      rowHeight: 95,
    };
  }

  const shifted = (row) => row + additionalRows;
  sheet.mergeCells(`A${shifted(13)}:L${shifted(13)}`);
  sheet.mergeCells(`A${shifted(14)}:L${shifted(14)}`);
  sheet.mergeCells(`A${shifted(15)}:M${shifted(15)}`);
  sheet.mergeCells(`A${shifted(16)}:M${shifted(20)}`);
  sheet.mergeCells(`A${shifted(21)}:M${shifted(21)}`);
  for (let row = 22; row <= 30; row += 1) {
    sheet.mergeCells(`A${shifted(row)}:B${shifted(row)}`);
    sheet.mergeCells(`C${shifted(row)}:M${shifted(row)}`);
  }
  sheet.mergeCells(`A${shifted(31)}:M${shifted(33)}`);
  sheet.mergeCells(`A${shifted(34)}:M${shifted(34)}`);

  const rowHeights = new Map([
    [13, 30], [14, 30], [15, 30], [19, 86], [21, 30],
    [22, 18], [23, 18], [24, 18], [25, 18], [26, 18],
    [27, 18], [28, 18], [29, 18], [30, 18], [31, 22],
    [32, 22], [33, 22], [34, 25],
  ]);
  for (const [row, height] of rowHeights) {
    sheet.getRange(`A${shifted(row)}:M${shifted(row)}`).format.rowHeight = height;
  }
}


const inputPath = argumentValue("--input-json");
const outputPath = argumentValue("--output-xlsx");
const workerDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.dirname(workerDirectory);
const templatePath = path.join(projectRoot, "文档", "PI模板Proforma Invoice Sunjack Lighting.xlsx");
const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const sheet = workbook.worksheets.getItem("PI");

const productStartRow = 11;
const templateProductRows = 2;
const additionalRows = Math.max(0, payload.products.length - templateProductRows);
expandProductArea(sheet, additionalRows);

sheet.getRange("B3").values = [[payload.buyer.company_name]];
sheet.getRange("B4").values = [[payload.buyer.recipient]];
sheet.getRange("B5").values = [[payload.buyer.address]];
sheet.getRange("B6").values = [[payload.buyer.tax_id]];
sheet.getRange("B7").values = [[payload.buyer.email]];
sheet.getRange("B8").values = [[payload.buyer.phone]];
sheet.getRange("I8").values = [[payload.terms.quote_date]];
sheet.getRange("L9").values = [[payload.invoice_no]];
sheet.getRange("L10").values = [[`Unit Price\n${payload.totals.currency}`]];
sheet.getRange("M10").values = [[`Total\n${payload.totals.currency}`]];

const visibleProductRows = Math.max(templateProductRows, payload.products.length);
for (let index = 0; index < visibleProductRows; index += 1) {
  const rowNumber = productStartRow + index;
  sheet.getRange(`A${rowNumber}:M${rowNumber}`).clear({ applyTo: "contents" });
  const product = payload.products[index];
  if (!product) continue;
  sheet.getRange(`A${rowNumber}`).values = [[index + 1]];
  sheet.getRange(`C${rowNumber}`).values = [[product.sku]];
  sheet.getRange(`D${rowNumber}`).values = [[product.description || product.product_name]];
  sheet.getRange(`J${rowNumber}`).values = [[Number(product.quantity)]];
  sheet.getRange(`K${rowNumber}`).values = [[product.unit]];
  sheet.getRange(`L${rowNumber}`).values = [[Number(product.unit_price)]];
  sheet.getRange(`M${rowNumber}`).values = [[Number(product.amount)]];
  await addProductImage(sheet, product.image_path, rowNumber);
}

const shippingRow = 13 + additionalRows;
const totalRow = 14 + additionalRows;
const wordsRow = 15 + additionalRows;
const notesRow = 16 + additionalRows;
const bankHeaderRow = 21 + additionalRows;
const bankEndRow = 34 + additionalRows;
sheet.getRange(`M${shippingRow}`).values = [[Number(payload.totals.shipping_fee)]];
sheet.getRange(`M${totalRow}`).values = [[Number(payload.totals.total_amount)]];
sheet.getRange(`A${wordsRow}`).values = [[payload.totals.amount_words]];
sheet.getRange(`A${notesRow}`).values = [[notesText(payload)]];

const peachFill = "#FCE4D6";
const thinBlackBorders = { preset: "all", style: "thin", color: "#000000" };
sheet.getRange(`A${shippingRow}:L${shippingRow}`).format = {
  fill: peachFill,
  font: { name: "Arial", color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "right",
  verticalAlignment: "center",
};
sheet.getRange(`M${shippingRow}`).format = {
  fill: "#FF0000",
  font: { name: "Arial", color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "right",
  verticalAlignment: "center",
};
sheet.getRange(`A${totalRow}:M${totalRow}`).format = {
  fill: peachFill,
  font: { name: "Arial", color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "right",
  verticalAlignment: "center",
};
sheet.getRange(`A${wordsRow}:M${wordsRow}`).format = {
  fill: peachFill,
  font: { name: "Arial", color: "#FF0000" },
  borders: thinBlackBorders,
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange(`A${bankHeaderRow}:M${bankHeaderRow}`).format = {
  fill: peachFill,
  font: { name: "Arial", bold: true, italic: false, color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange(`A${bankHeaderRow + 1}:M${bankHeaderRow + 9}`).format = {
  font: { name: "Arial", bold: false, italic: false, color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "left",
  verticalAlignment: "center",
};
sheet.getRange(`A${bankHeaderRow + 10}:M${bankHeaderRow + 12}`).format.font = {
  name: "Arial",
  bold: true,
  italic: false,
  color: "#000000",
};
sheet.getRange(`A${bankEndRow}:M${bankEndRow}`).format = {
  font: { name: "Arial", bold: true, italic: false, color: "#000000" },
  borders: thinBlackBorders,
  horizontalAlignment: "center",
  verticalAlignment: "center",
};

sheet.getRange(`J${productStartRow}:J${productStartRow + visibleProductRows - 1}`).format.numberFormat = "0.00";
sheet.getRange(`L${productStartRow}:M${productStartRow + visibleProductRows - 1}`).format.numberFormat = "0.00";
sheet.getRange(`M${shippingRow}:M${totalRow}`).format.numberFormat = "0.00";

const usedRange = sheet.getUsedRange();
usedRange.format.font = { name: "Arial" };
for (const headingRange of [
  "A1:M1",
  "A2:F2",
  "H2:M2",
  "J9:M9",
  "A10:M10",
  `A${bankHeaderRow}:M${bankHeaderRow}`,
  `A${31 + additionalRows}:M${33 + additionalRows}`,
  `A${bankEndRow}:M${bankEndRow}`,
]) {
  sheet.getRange(headingRange).format.font = { name: "Arial", bold: true };
}

const keyRange = `A1:M${bankEndRow}`;
await workbook.inspect({
  kind: "table",
  range: `PI!${keyRange}`,
  include: "values,formulas",
  tableMaxRows: bankEndRow,
  tableMaxCols: 13,
  maxChars: 5000,
});
const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "PI export formula error scan",
});
if (formulaErrors.ndjson.includes('"kind":"match"')) {
  throw new Error(`Formula error found in generated PI: ${formulaErrors.ndjson}`);
}
const preview = await workbook.render({ sheetName: "PI", range: keyRange, scale: 1, format: "png" });
await preview.arrayBuffer();

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

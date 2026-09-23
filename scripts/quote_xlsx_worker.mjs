import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import JSZip from "jszip";
import { quotationTemplates } from "./quotation_template_config.mjs";

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1 || !process.argv[index + 1]) throw new Error(`Missing required argument: ${name}`);
  return process.argv[index + 1];
}

function percentText(value) {
  const percent = Number(value) * 100;
  return Number.isInteger(percent) ? `${percent}%` : `${percent.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}%`;
}

function notesText(payload) {
  const { terms, payment_splits: payment, totals } = payload;
  const money = value => `${totals.currency} ${Number(value).toFixed(2)}`;
  const rows = [
    "NOTES:", `1. Lead time: ${terms.lead_time_days} Days`, `2. Price Valid Date: ${terms.validity_days} Days.`,
    "3. Payment terms:",
    `${percentText(payment.deposit_ratio)} (${money(payment.deposit_amount)}) payment in advance, ${percentText(payment.balance_ratio)} (${money(payment.balance_amount)}) balance payment should be paid before shipping`,
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
    const mimeType = { ".gif": "image/gif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp" }[extension];
    if (!mimeType) return;
    sheet.images.add({
      dataUrl: `data:${mimeType};base64,${bytes.toString("base64")}`,
      anchor: { from: { row: rowNumber - 1, col: 1, rowOffsetPx: 4, colOffsetPx: 4 }, extent: { widthPx: 120, heightPx: 90 } },
    });
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}

// Shift the template's lower block and clone its designated item row. Copying
// "all" preserves workbook-owned styles; this renderer never defines styles.
function expandProductArea(sheet, config, additionalRows) {
  if (additionalRows <= 0) return;
  const { item, lowerBlock } = config;
  const lowerBlockValues = sheet.getRange(`A${lowerBlock.startRow}:M${lowerBlock.endRow}`).values;
  for (const range of lowerBlock.merges) sheet.unmergeCells(range);
  for (let row = lowerBlock.endRow; row >= lowerBlock.startRow; row -= 1) {
    sheet.getRange(`A${row + additionalRows}:M${row + additionalRows}`).copyFrom(sheet.getRange(`A${row}:M${row}`), "all");
  }
  sheet.getRange(`A${lowerBlock.startRow + additionalRows}:M${lowerBlock.endRow + additionalRows}`).values = lowerBlockValues;
  for (let index = 0; index < additionalRows; index += 1) {
    const row = lowerBlock.startRow + index;
    sheet.getRange(`A${row}:M${row}`).copyFrom(sheet.getRange(`A${item.sourceRow}:M${item.sourceRow}`), "all");
    sheet.mergeCells(`D${row}:I${row}`);
  }
  for (const range of lowerBlock.merges) sheet.mergeCells(range.replace(/(\d+)/g, value => String(Number(value) + additionalRows)));
}

function setValue(sheet, address, value) { sheet.getRange(address).values = [[value]]; }

function rowXml(xml, rowNumber) {
  return xml.match(new RegExp("<(?:\\w+:)?row\\b([^>]*\\br=\"" + rowNumber + "\"[^>]*)>([\\s\\S]*?)<\\/(?:\\w+:)?row>"));
}

// artifact-tool correctly copies values and merges but does not retain every
// imported row-level style after rows are moved. Restore styles from the
// original template XML: added product rows use the designated item row, while
// every shifted lower-block row keeps its own source-row formatting.
async function inheritItemRowStyles(xlsxBytes, config, itemRows) {
  const zip = await JSZip.loadAsync(xlsxBytes);
  const worksheet = zip.file(config.worksheetXmlPath);
  if (!worksheet) throw new Error("Worksheet XML not found: " + config.worksheetXmlPath);
  let xml = await worksheet.async("string");
  const templateZip = await JSZip.loadAsync(await fs.readFile(path.join(projectRoot, config.file)));
  const templateWorksheet = templateZip.file(config.worksheetXmlPath);
  if (!templateWorksheet) throw new Error("Template worksheet XML not found: " + config.worksheetXmlPath);
  const templateXml = await templateWorksheet.async("string");

  function restoreRowStyle(sourceRowNumber, targetRowNumber) {
    const source = rowXml(templateXml, sourceRowNumber);
    const target = rowXml(xml, targetRowNumber);
    if (!source || !target) return;
    const sourceTag = source[1];
    const sourceStyles = new Map(
      [...source[2].matchAll(new RegExp("<(?:\\w+:)?c\\b([^>]*\\br=\"([A-Z]+)" + sourceRowNumber + "\"[^>]*)>", "g"))]
      .map(([, attributes, column]) => [column, attributes.match(/\bs="(\d+)"/)?.[1]])
      .filter(([, style]) => style !== undefined),
    );
    const rowLayout = sourceTag.match(/\b(ht|customHeight)="[^"]*"/g) || [];
    const targetTag = target[1]
      .replace(/\s(?:ht|customHeight)="[^"]*"/g, "")
      .concat(rowLayout.length ? " " + rowLayout.join(" ") : "");
    const targetBody = target[2].replace(
      new RegExp("<(?:\\w+:)?c\\b([^>]*\\br=\"([A-Z]+)" + targetRowNumber + "\"[^>]*)>", "g"),
      (cell, attributes, column) => {
        const style = sourceStyles.get(column);
        if (!style) return cell;
        const openTag = cell.match(/^<(?:\w+:)?c/)[0];
        const close = cell.endsWith("/>") ? "/>" : ">";
        const cleanAttributes = attributes.replace(/\ss="\d+"/, "").replace(/\/\s*$/, "");
        return openTag + cleanAttributes + " s=\"" + style + "\"" + close;
      },
    );
    const openTag = target[0].match(/^<(?:\w+:)?row/)[0];
    const closeTag = "</" + openTag.slice(1) + ">";
    xml = xml.replace(target[0], openTag + targetTag + ">" + targetBody + closeTag);
  }

  for (const rowNumber of itemRows) restoreRowStyle(config.item.sourceRow, rowNumber);
  const additionalRows = itemRows.length;
  for (let row = config.lowerBlock.startRow; row <= config.lowerBlock.endRow; row += 1) {
    restoreRowStyle(row, row + additionalRows);
  }
  zip.file(config.worksheetXmlPath, xml);
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

const inputPath = argumentValue("--input-json");
const outputPath = argumentValue("--output-xlsx");
const workerDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.dirname(workerDirectory);
const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
const config = quotationTemplates[payload.template_id];
if (!config) throw new Error(`Unknown quotation template: ${payload.template_id}`);

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(projectRoot, config.file)));
const sheet = workbook.worksheets.getItem(config.sheet);
const additionalRows = Math.max(0, payload.products.length - config.item.templateRows);
expandProductArea(sheet, config, additionalRows);

const fieldValues = {
  buyerCompany: payload.buyer.company_name, buyerRecipient: payload.buyer.recipient, buyerAddress: payload.buyer.address,
  buyerTaxId: payload.buyer.tax_id, buyerEmail: payload.buyer.email, buyerPhone: payload.buyer.phone,
  quoteDate: payload.terms.quote_date, invoiceNo: payload.invoice_no,
  unitPriceHeader: `Unit Price\n${payload.totals.currency}`, totalHeader: `Total\n${payload.totals.currency}`,
};
for (const [field, value] of Object.entries(fieldValues)) setValue(sheet, config.fields[field], value);

const visibleRows = Math.max(config.item.templateRows, payload.products.length);
for (let index = 0; index < visibleRows; index += 1) {
  const row = config.item.startRow + index;
  sheet.getRange(`A${row}:M${row}`).clear({ applyTo: "contents" });
  const product = payload.products[index];
  if (!product) continue;
  setValue(sheet, `A${row}`, index + 1); setValue(sheet, `C${row}`, product.model || product.sku);
  setValue(sheet, `D${row}`, product.description || product.product_name); setValue(sheet, `J${row}`, Number(product.quantity));
  setValue(sheet, `K${row}`, product.unit); setValue(sheet, `L${row}`, Number(product.unit_price)); setValue(sheet, `M${row}`, Number(product.amount));
  await addProductImage(sheet, product.image_path, row);
}

const shifted = row => row + additionalRows;
const rows = config.lowerBlock.rows;
setValue(sheet, `M${shifted(rows.shipping)}`, Number(payload.totals.shipping_fee));
if (rows.discount) setValue(sheet, `M${shifted(rows.discount)}`, Number(payload.totals.discount));
setValue(sheet, `M${shifted(rows.total)}`, Number(payload.totals.total_amount));
setValue(sheet, `A${shifted(rows.amountWords)}`, payload.totals.amount_words);
setValue(sheet, `A${shifted(rows.notes)}`, notesText(payload));

const keyRange = `A1:M${shifted(rows.end)}`;
const formulaErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "quotation export formula error scan" });
if (formulaErrors.ndjson.includes('"kind":"match"')) throw new Error(`Formula error found in generated workbook: ${formulaErrors.ndjson}`);
await (await workbook.render({ sheetName: config.sheet, range: keyRange, scale: 1, format: "png" })).arrayBuffer();
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const renderedWorkbook = await inheritItemRowStyles(
  await fs.readFile(outputPath),
  config,
  Array.from({ length: additionalRows }, (_, index) => config.lowerBlock.startRow + index),
);
await fs.writeFile(outputPath, renderedWorkbook);

// Signal success only once the final workbook has been fully written.
process.send?.({ type: "complete" });

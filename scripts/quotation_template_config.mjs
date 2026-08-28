// Central mappings for the standard English workbooks. The artifact library
// does not expose named ranges reliably, so locations live here rather than
// being scattered through the renderer.  Visual styling belongs in the xlsx.
export const quotationTemplates = {
  standard_en_no_discount: {
    file: "templates/quotation/报价单模板_无折扣.xlsx",
    sheet: "PI",
    worksheetXmlPath: "xl/worksheets/sheet1.xml",
    columns: "A:M",
    fields: {
      buyerCompany: "B3", buyerRecipient: "B4", buyerAddress: "B5",
      buyerTaxId: "B6", buyerEmail: "B7", buyerPhone: "B8",
      quoteDate: "I8", invoiceNo: "L9", unitPriceHeader: "L10",
      totalHeader: "M10",
    },
    item: { startRow: 11, templateRows: 2, sourceRow: 12 },
    lowerBlock: {
      startRow: 13, endRow: 34,
      merges: [
        "A13:L13", "A14:L14", "A15:M15", "A16:M20", "A21:M21",
        ...Array.from({ length: 9 }, (_, index) => `A${22 + index}:B${22 + index}`),
        ...Array.from({ length: 9 }, (_, index) => `C${22 + index}:M${22 + index}`),
        "A31:M33", "A34:M34",
      ],
      rows: { shipping: 13, total: 14, amountWords: 15, notes: 16, bankHeader: 21, end: 34 },
    },
  },
  standard_en_with_discount: {
    file: "templates/quotation/报价单模板_有折扣.xlsx",
    sheet: "PI",
    worksheetXmlPath: "xl/worksheets/sheet1.xml",
    columns: "A:M",
    fields: {
      buyerCompany: "B3", buyerRecipient: "B4", buyerAddress: "B5",
      buyerTaxId: "B6", buyerEmail: "B7", buyerPhone: "B8",
      quoteDate: "I8", invoiceNo: "L9", unitPriceHeader: "L10",
      totalHeader: "M10",
    },
    item: { startRow: 11, templateRows: 2, sourceRow: 12 },
    lowerBlock: {
      startRow: 13, endRow: 35,
      merges: [
        "A13:L13", "A14:L14", "A15:L15", "A16:M16", "A17:M21", "A22:M22",
        ...Array.from({ length: 9 }, (_, index) => `A${23 + index}:B${23 + index}`),
        ...Array.from({ length: 9 }, (_, index) => `C${23 + index}:M${23 + index}`),
        "A32:M34", "A35:M35",
      ],
      rows: { shipping: 13, discount: 14, total: 15, amountWords: 16, notes: 17, bankHeader: 22, end: 35 },
    },
  },
};

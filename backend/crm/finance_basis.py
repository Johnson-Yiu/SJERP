"""Presentation metadata only; never calculates or changes financial amounts."""
BOOK_RMB_BASIS = "book_rmb_reference"
BOOK_RMB_VERSION = 1
BOOK_RMB_NOTE = '账面人民币折算参考：已确认流水按既有人民币金额及流水汇率汇总，包含原币为CNY的既有流水；不代表银行实际到账、已完成结汇或银行账户余额。流水发生日期不等同于银行到账日。'

def book_rmb_metadata():
    return {"basis": BOOK_RMB_BASIS, "version": BOOK_RMB_VERSION, "note": BOOK_RMB_NOTE, "date_basis": "transaction_date", "includes_cny": True}

"""Canonical presentation labels for the persisted customer lifecycle values."""

CUSTOMER_STATUS_DISPLAY = {
    "lead": "线索",
    "contact": "已联系",
    "opportunity": "商机",
    "customer": "正式客户",
    "company": "返单客户",
}


def customer_status_display(value):
    return CUSTOMER_STATUS_DISPLAY.get(value, value)

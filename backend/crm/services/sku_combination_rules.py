"""Small, product-scoped implication rules for SKU parameter combinations."""
from itertools import product as cartesian
from math import prod
from rest_framework.exceptions import ValidationError
from crm.sku_identity import category_attributes, raw_parameter_value, normalize_parameter_token, _with_unit


def definitions(product):
    return {f"{a.category_id}:{a.key}": a for a in category_attributes(product) if a.include_in_sku or a.include_in_sales_model}


def token(value, attribute):
    return normalize_parameter_token(_with_unit(value, attribute.unit))


def prepare(product, rules):
    attrs = definitions(product)
    if not isinstance(rules, list) or len(rules) > 20:
        raise ValidationError({"rules": "最多支持 20 条组合规则。"})
    result = []
    for index, rule in enumerate(rules, 1):
        if not isinstance(rule, dict):
            raise ValidationError({"rules": f"第 {index} 条规则格式错误。"})
        target, when = rule.get("target"), rule.get("when", "")
        op = rule.get("op")
        if not isinstance(target, str) or not isinstance(when, str) or not isinstance(op, str) or target not in attrs or (when and when not in attrs) or op not in {"eq", "neq", "in"}:
            raise ValidationError({"rules": f"第 {index} 条：请选择有效的参数与规则类型。"})
        def values(field, key):
            raw = rule.get(field, [])
            if not isinstance(raw, list) or not raw or len(raw) > 30 or any(not isinstance(v, str) or not v.strip() for v in raw):
                raise ValidationError({"rules": f"第 {index} 条：请填写{field == 'values' and '约束' or '触发'}值。"})
            return list(dict.fromkeys(token(v, attrs[key]) for v in raw))
        allowed = values("values", target)
        triggers = values("when_values", when) if when else []
        if op in {"eq", "neq"} and len(allowed) != 1:
            raise ValidationError({"rules": f"第 {index} 条：“必须等于/不能等于”只能填写一个值；多值请使用“仅允许这些值”。"})
        result.append({"target": target, "op": op, "values": allowed, "when": when, "when_values": triggers})
    return result


def triggered(rule, values):
    return not rule["when"] or values.get(rule["when"]) in rule["when_values"]


def accepts(rule, values):
    if not triggered(rule, values):
        return True
    value = values.get(rule["target"])
    return value not in rule["values"] if rule["op"] == "neq" else value in rule["values"]


def validate_rules(product, rules):
    prepared = prepare(product, rules)
    domains = {}
    for rule in prepared:
        domains.setdefault(rule["target"], set()).update(rule["values"])
        if rule["when"]:
            domains.setdefault(rule["when"], set()).update(rule["when_values"])
    # One representative of all unmentioned values makes this independent of today's inputs.
    for domain in domains.values():
        domain.add(None)
    if prod(len(v) for v in domains.values()) > 100000:
        raise ValidationError({"rules": "规则涉及的参数和值过多，请减少规则后重试。"})
    keys = list(domains)
    valid_triggers, possible_pairs, valid_pairs = set(), set(), set()
    any_valid = False
    for combination in cartesian(*(domains[k] for k in keys)):
        values = dict(zip(keys, combination))
        active = [i for i, rule in enumerate(prepared) if triggered(rule, values)]
        pairs = {(a, b) for a in active for b in active if a < b}
        possible_pairs.update(pairs)
        if all(accepts(rule, values) for rule in prepared):
            any_valid = True
            valid_triggers.update(active)
            valid_pairs.update(pairs)
    conflicts = [f"第 {i + 1} 条规则触发后没有可行组合，与其他约束冲突。" for i in range(len(prepared)) if i not in valid_triggers]
    conflicts += [f"第 {a + 1} 条与第 {b + 1} 条规则同时触发时无可行组合。" for a, b in sorted(possible_pairs - valid_pairs)]
    if conflicts or not any_valid:
        raise ValidationError({"rules": conflicts or ["规则相互矛盾，没有有效组合。"]})
    return prepared


def validate_combination(product, values):
    if not product.combination_rules:
        return
    rules = prepare(product, product.combination_rules)
    attrs = definitions(product)
    normalized = {key: token(raw_parameter_value(values, key, a.name), a) for key, a in attrs.items()}
    invalid = [str(i + 1) for i, rule in enumerate(rules) if not accepts(rule, normalized)]
    if invalid:
        raise ValidationError({"combination_rules": f"此 SKU 不满足组合规则第 { '、'.join(invalid) } 条，不能创建或更改参数。"})

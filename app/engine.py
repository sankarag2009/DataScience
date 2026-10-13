def field_value(data, path):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current

def evaluate(data, rule):
    actual, op, expected = field_value(data, rule["field"]), rule["operator"], rule.get("value")
    try:
        if op == "EXISTS": passed = actual is not None and actual != ""
        elif actual is None: return {"id": rule["id"], "field": rule["field"], "passed": None, "reason": rule.get("reason", ""), "actual": None}
        elif op == "EQUALS": passed = actual == expected
        elif op == "NOT_EQUALS": passed = actual != expected
        elif op == "IN": passed = actual in expected
        elif op == "NOT_IN": passed = actual not in expected
        elif op == "CONTAINS": passed = expected in actual
        elif op == "GREATER_THAN": passed = float(actual) > float(expected)
        elif op == "GREATER_THAN_OR_EQUAL": passed = float(actual) >= float(expected)
        elif op == "LESS_THAN": passed = float(actual) < float(expected)
        elif op == "LESS_THAN_OR_EQUAL": passed = float(actual) <= float(expected)
        elif op == "TRUE": passed = actual is True
        elif op == "FALSE": passed = actual is False
        else: return {"id": rule["id"], "field": rule["field"], "passed": None, "reason": "Unsupported operator", "actual": actual}
        return {"id": rule["id"], "field": rule["field"], "passed": bool(passed), "reason": rule.get("reason", ""), "actual": actual}
    except (TypeError, ValueError):
        return {"id": rule["id"], "field": rule["field"], "passed": None, "reason": "Value could not be evaluated", "actual": actual}

def screen(candidate, drug, protocol):
    data = {
        "diagnosis": candidate.diagnosis, "disease_stage": candidate.disease_stage,
        "prior_therapy_lines": candidate.prior_therapy_lines, "ecog_score": candidate.ecog_score,
        "biomarkers": candidate.biomarkers or {}, "labs": candidate.labs or {},
        "comorbidities": candidate.comorbidities or [], "medications": candidate.medications or [],
        "allergies": candidate.allergies or [], "history": candidate.history or {}
    }
    marker = (candidate.biomarkers or {}).get(drug.target_attribute)
    if marker is True or (isinstance(marker, str) and marker.upper() in {"POSITIVE", "PRESENT", "DETECTED"}):
        target = "POSITIVE"
    elif marker is False or (isinstance(marker, str) and marker.upper() in {"NEGATIVE", "ABSENT", "NOT_DETECTED"}):
        target = "NEGATIVE"
    else:
        target = "INDETERMINATE"

    inc = [evaluate(data, r) for r in (protocol.inclusion or [])]
    exc = [evaluate(data, r) for r in (protocol.exclusion or [])]
    val = [evaluate(data, r) for r in (protocol.validation or [])]
    results = ([{"type":"INCLUSION", **x} for x in inc] +
               [{"type":"EXCLUSION", **x} for x in exc] +
               [{"type":"VALIDATION", **x} for x in val])
    reasons = []
    triggered = [x for x in exc if x["passed"] is True]
    failed_inc = [x for x in inc if x["passed"] is False]
    unresolved = [x for x in inc + exc + val if x["passed"] is None]
    failed_val = [x for x in val if x["passed"] is False]
    for x in triggered: reasons.append(f"Exclusion triggered {x['id']}: {x['reason']}")
    for x in failed_inc: reasons.append(f"Inclusion not met {x['id']}: {x['reason']}")
    for x in failed_val: reasons.append(f"Additional validation failed {x['id']}: {x['reason']}")
    for x in unresolved: reasons.append(f"Missing/unevaluable evidence {x['id']}: {x['reason']}")
    if target == "INDETERMINATE": reasons.append(f"Target biomarker '{drug.target_attribute}' is missing or inconclusive.")

    if triggered:
        safety, eligibility, decision = "EXCLUDED", "EXCLUDED", "HOLD"
    elif failed_inc:
        safety, eligibility, decision = ("REVIEW_REQUIRED" if unresolved else "ELIGIBLE"), "NOT_ELIGIBLE", "DEFER"
    elif unresolved or failed_val or target == "INDETERMINATE":
        safety, eligibility, decision = "REVIEW_REQUIRED", "REVIEW_REQUIRED", "HOLD"
    elif target == "NEGATIVE":
        safety, eligibility, decision = "ELIGIBLE", "NOT_ELIGIBLE_FOR_TARGET_COHORT", "DEFER"
        reasons.append("Target-negative; retain for a comparison cohort if permitted by the protocol.")
    else:
        safety, eligibility, decision = "ELIGIBLE", "ELIGIBLE", "DISPATCH_RECOMMENDATION"
        reasons.append("Configured rules passed; authorized human review is still required.")
    return dict(target_status=target, safety_status=safety, eligibility_status=eligibility,
                decision=decision, reasons=reasons or ["No additional reasons."], rule_results=results)

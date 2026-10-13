from types import SimpleNamespace
from app.engine import evaluate, screen

def test_missing_rule_field_is_indeterminate():
    r=evaluate({"biomarkers":{}},{"id":"T1","field":"biomarkers.X","operator":"EQUALS","value":"POSITIVE","reason":"target"})
    assert r["passed"] is None

def test_target_positive_does_not_override_exclusion():
    c=SimpleNamespace(diagnosis="disease_x",disease_stage=None,prior_therapy_lines=1,ecog_score=1,
        biomarkers={"TARGET":"POSITIVE"},labs={},comorbidities=["excluded"],medications=[],allergies=[],history={})
    d=SimpleNamespace(target_attribute="TARGET")
    p=SimpleNamespace(inclusion=[{"id":"I","field":"diagnosis","operator":"EQUALS","value":"disease_x","reason":"diagnosis"}],
        exclusion=[{"id":"E","field":"comorbidities","operator":"CONTAINS","value":"excluded","reason":"condition"}],validation=[])
    out=screen(c,d,p)
    assert out["target_status"]=="POSITIVE"
    assert out["eligibility_status"]=="EXCLUDED"

def test_missing_target_is_not_negative():
    c=SimpleNamespace(diagnosis="disease_x",disease_stage=None,prior_therapy_lines=1,ecog_score=None,
        biomarkers={},labs={},comorbidities=[],medications=[],allergies=[],history={})
    d=SimpleNamespace(target_attribute="TARGET")
    p=SimpleNamespace(inclusion=[],exclusion=[],validation=[])
    assert screen(c,d,p)["target_status"]=="INDETERMINATE"

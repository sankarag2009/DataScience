from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import Candidate, Drug, Protocol, Screening, Feedback, Audit
from .engine import screen

Base.metadata.create_all(bind=engine)
app = FastAPI(title="SilicoBioScreen API", version="0.1.0",
 description="Research prototype only; not validated for clinical decisions.")

class CandidateIn(BaseModel):
    external_id: str
    diagnosis: str
    disease_stage: str | None = None
    prior_therapy_lines: int | None = Field(default=None, ge=0)
    ecog_score: float | None = Field(default=None, ge=0, le=5)
    biomarkers: dict = {}
    labs: dict = {}
    comorbidities: list = []
    medications: list = []
    allergies: list = []
    history: dict = {}

class DrugIn(BaseModel):
    name: str
    development_code: str | None = None
    active_ingredient: str | None = None
    molecular_target: str
    target_attribute: str
    mechanism_of_action: str | None = None
    clearance_pathways: dict = {}
    cyp_ddi_profile: list = []
    safety_liabilities: list = []

class Rule(BaseModel):
    id: str
    field: str
    operator: str
    value: object = None
    reason: str = "Protocol criterion"

class ProtocolIn(BaseModel):
    name: str
    version: str = "1.0"
    drug_id: int
    inclusion: list[Rule] = []
    exclusion: list[Rule] = []
    validation: list[Rule] = []
    active: bool = True

class ScreenIn(BaseModel):
    candidate_id: int
    drug_id: int
    protocol_id: int

class FeedbackIn(BaseModel):
    screening_id: int
    outcome: str
    root_cause: str | None = None
    reviewer: str = "unassigned"
    notes: str | None = None

def audit(db, entity, entity_id, action, details=None):
    db.add(Audit(entity=entity, entity_id=str(entity_id), action=action, details=details or {}))

def rowdict(row):
    return {col.name: getattr(row, col.name) for col in row.__table__.columns}

@app.get("/health")
def health():
    return {"status":"ok", "app":"SilicoBioScreen", "mode":"research-prototype"}

@app.post("/candidates", status_code=201)
def create_candidate(p: CandidateIn, db: Session = Depends(get_db)):
    if db.scalar(select(Candidate).where(Candidate.external_id == p.external_id)):
        raise HTTPException(409, "external_id already exists")
    obj = Candidate(**p.model_dump())
    db.add(obj); db.flush()
    audit(db, "candidate", obj.id, "CREATE", {"external_id": obj.external_id})
    db.commit(); db.refresh(obj)
    return rowdict(obj)

@app.get("/candidates")
def candidates(db: Session = Depends(get_db)):
    return [rowdict(x) for x in db.scalars(select(Candidate).order_by(Candidate.id.desc())).all()]

@app.post("/drugs", status_code=201)
def create_drug(p: DrugIn, db: Session = Depends(get_db)):
    obj = Drug(**p.model_dump())
    db.add(obj); db.flush()
    audit(db, "drug", obj.id, "CREATE", {"name": obj.name})
    db.commit(); db.refresh(obj)
    return rowdict(obj)

@app.get("/drugs")
def drugs(db: Session = Depends(get_db)):
    return [rowdict(x) for x in db.scalars(select(Drug).order_by(Drug.id.desc())).all()]

@app.post("/protocols", status_code=201)
def create_protocol(p: ProtocolIn, db: Session = Depends(get_db)):
    if not db.get(Drug, p.drug_id): raise HTTPException(404, "Drug not found")
    data = p.model_dump()
    for key in ("inclusion", "exclusion", "validation"):
        data[key] = [x.model_dump() for x in data[key]]
    obj = Protocol(**data)
    db.add(obj); db.flush()
    audit(db, "protocol", obj.id, "CREATE", {"name": obj.name, "version": obj.version})
    db.commit(); db.refresh(obj)
    return rowdict(obj)

@app.get("/protocols")
def protocols(db: Session = Depends(get_db)):
    return [rowdict(x) for x in db.scalars(select(Protocol).order_by(Protocol.id.desc())).all()]

@app.post("/screenings", status_code=201)
def create_screening(p: ScreenIn, db: Session = Depends(get_db)):
    c, d, pr = db.get(Candidate, p.candidate_id), db.get(Drug, p.drug_id), db.get(Protocol, p.protocol_id)
    if not c or not d or not pr: raise HTTPException(404, "Candidate, drug, or protocol not found")
    if pr.drug_id != d.id: raise HTTPException(400, "Protocol is configured for a different drug")
    if not pr.active: raise HTTPException(400, "Protocol is inactive")
    result = screen(c, d, pr)
    obj = Screening(candidate_id=c.id, drug_id=d.id, protocol_id=pr.id,
        target_status=result["target_status"], safety_status=result["safety_status"],
        eligibility_status=result["eligibility_status"], decision=result["decision"],
        reasons=result["reasons"], rule_results=result["rule_results"], protocol_version=pr.version)
    db.add(obj); db.flush()
    audit(db, "screening", obj.id, "SCREEN", {"target_status": obj.target_status,
        "eligibility_status": obj.eligibility_status, "protocol_version": pr.version})
    db.commit(); db.refresh(obj)
    return rowdict(obj)

@app.get("/screenings")
def screenings(db: Session = Depends(get_db)):
    return [rowdict(x) for x in db.scalars(select(Screening).order_by(Screening.id.desc())).all()]

@app.post("/feedback", status_code=201)
def feedback(p: FeedbackIn, db: Session = Depends(get_db)):
    if p.outcome not in {"ACCEPTED", "REJECTED"}:
        raise HTTPException(422, "outcome must be ACCEPTED or REJECTED")
    if not db.get(Screening, p.screening_id): raise HTTPException(404, "Screening not found")
    obj = Feedback(**p.model_dump()); db.add(obj); db.flush()
    audit(db, "feedback", obj.id, "CREATE", {"screening_id": obj.screening_id, "outcome": obj.outcome})
    db.commit(); db.refresh(obj)
    return rowdict(obj)

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    tp = fp = tn = fn = 0
    feedback_rows = list(db.scalars(select(Feedback)).all())
    for f in feedback_rows:
        s = db.get(Screening, f.screening_id)
        if not s: continue
        predicted = s.decision == "DISPATCH_RECOMMENDATION"
        actual = f.outcome == "ACCEPTED"
        if predicted and actual: tp += 1
        elif predicted and not actual: fp += 1
        elif not predicted and not actual: tn += 1
        else: fn += 1
    n = tp + fp + tn + fn
    return {"feedback_count": len(feedback_rows), "confusion_matrix":{"TP":tp,"FP":fp,"TN":tn,"FN":fn},
        "accuracy":(tp+tn)/n if n else None, "precision":tp/(tp+fp) if tp+fp else None,
        "recall":tp/(tp+fn) if tp+fn else None,
        "note":"Descriptive prototype metrics only; feedback never changes rules automatically."}

@app.get("/audit")
def audit_events(db: Session = Depends(get_db)):
    return [rowdict(x) for x in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(500)).all()]

@app.post("/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    c = db.scalar(select(Candidate).where(Candidate.external_id == "DEMO-CANDIDATE-001"))
    if not c:
        c = Candidate(external_id="DEMO-CANDIDATE-001", diagnosis="metastatic_colorectal_cancer",
            disease_stage="metastatic", prior_therapy_lines=2, ecog_score=1,
            biomarkers={"KRAS_G12C":"POSITIVE"}, labs={"egfr":92,"alt":22},
            comorbidities=[], medications=[], allergies=[], history={"record_age_days":30,"synthetic_demo":True})
        db.add(c); db.flush(); audit(db,"candidate",c.id,"CREATE_DEMO",{"synthetic":True})
    d = db.scalar(select(Drug).where(Drug.name == "DEMO KRAS G12C inhibitor"))
    if not d:
        d = Drug(name="DEMO KRAS G12C inhibitor", development_code="DEMO-001",
            active_ingredient="Synthetic placeholder", molecular_target="KRAS G12C",
            target_attribute="KRAS_G12C", mechanism_of_action="Synthetic example only",
            clearance_pathways={"hepatic":"unknown","renal":"unknown"}, cyp_ddi_profile=[],
            safety_liabilities=["Placeholder only"])
        db.add(d); db.flush(); audit(db,"drug",d.id,"CREATE_DEMO",{"synthetic":True})
    pr = db.scalar(select(Protocol).where(Protocol.name == "DEMO protocol"))
    if not pr:
        pr = Protocol(name="DEMO protocol", version="demo-1.0", drug_id=d.id,
            inclusion=[
                {"id":"INC-1","field":"diagnosis","operator":"EQUALS","value":"metastatic_colorectal_cancer","reason":"Synthetic diagnosis requirement"},
                {"id":"INC-2","field":"prior_therapy_lines","operator":"GREATER_THAN_OR_EQUAL","value":1,"reason":"Synthetic prior-treatment requirement"}],
            exclusion=[{"id":"EXC-1","field":"comorbidities","operator":"CONTAINS","value":"protocol_prohibited_condition","reason":"Synthetic exclusion placeholder"}],
            validation=[{"id":"VAL-1","field":"history.record_age_days","operator":"LESS_THAN_OR_EQUAL","value":180,"reason":"Synthetic recency check"}], active=True)
        db.add(pr); db.flush(); audit(db,"protocol",pr.id,"CREATE_DEMO",{"synthetic":True})
    db.commit()
    return {"message":"Synthetic demo records created/confirmed", "candidate_id":c.id, "drug_id":d.id, "protocol_id":pr.id,
            "warning":"Synthetic placeholders only; not clinical rules."}

from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now():
    return datetime.now(timezone.utc)

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    diagnosis: Mapped[str] = mapped_column(String(200))
    disease_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prior_therapy_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ecog_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    biomarkers: Mapped[dict] = mapped_column(JSON, default=dict)
    labs: Mapped[dict] = mapped_column(JSON, default=dict)
    comorbidities: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    history: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Drug(Base):
    __tablename__ = "drugs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    development_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active_ingredient: Mapped[str | None] = mapped_column(String(200), nullable=True)
    molecular_target: Mapped[str] = mapped_column(String(200))
    target_attribute: Mapped[str] = mapped_column(String(200))
    mechanism_of_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    clearance_pathways: Mapped[dict] = mapped_column(JSON, default=dict)
    cyp_ddi_profile: Mapped[list] = mapped_column(JSON, default=list)
    safety_liabilities: Mapped[list] = mapped_column(JSON, default=list)

class Protocol(Base):
    __tablename__ = "protocols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    drug_id: Mapped[int] = mapped_column(Integer, index=True)
    inclusion: Mapped[list] = mapped_column(JSON, default=list)
    exclusion: Mapped[list] = mapped_column(JSON, default=list)
    validation: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Screening(Base):
    __tablename__ = "screenings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(Integer, index=True)
    drug_id: Mapped[int] = mapped_column(Integer, index=True)
    protocol_id: Mapped[int] = mapped_column(Integer, index=True)
    target_status: Mapped[str] = mapped_column(String(30))
    safety_status: Mapped[str] = mapped_column(String(30))
    eligibility_status: Mapped[str] = mapped_column(String(40))
    decision: Mapped[str] = mapped_column(String(40))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    rule_results: Mapped[list] = mapped_column(JSON, default=list)
    protocol_version: Mapped[str] = mapped_column(String(50))

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screening_id: Mapped[int] = mapped_column(Integer, index=True)
    outcome: Mapped[str] = mapped_column(String(30))
    root_cause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewer: Mapped[str] = mapped_column(String(100), default="unassigned")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

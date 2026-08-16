from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    process_data = relationship("ProcessData", back_populates="scenario")
    anomaly_events = relationship("AnomalyEvent", back_populates="scenario")


class ProcessData(Base):
    __tablename__ = "process_data"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    process_name = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    variable_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)

    scenario = relationship("Scenario", back_populates="process_data")


class VariableThreshold(Base):
    __tablename__ = "variable_thresholds"

    id = Column(Integer, primary_key=True)
    variable_name = Column(String, unique=True, nullable=False)
    golden_value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    check_upper = Column(Boolean, nullable=False, default=True)
    unit = Column(String, nullable=False)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    situation = Column(Text, nullable=False)
    cause = Column(Text, nullable=False)
    quality_impact = Column(Text, nullable=False)
    defect_tags = Column(JSON, nullable=False)
    response = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    manual_text = Column(Text, nullable=False)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(String, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    process_name = Column(String, nullable=False)
    detected_at = Column(DateTime, nullable=False)
    last_updated_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Float, default=0)
    severity_grade = Column(String, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    status = Column(String, default="미확인")
    variables = Column(JSON, nullable=False)

    scenario = relationship("Scenario", back_populates="anomaly_events")
    cause_analyses = relationship("CauseAnalysis", back_populates="anomaly_event")
    quality_predictions = relationship("QualityPrediction", back_populates="anomaly_event")
    recommended_actions = relationship("RecommendedAction", back_populates="anomaly_event")
    action_records = relationship("ActionRecord", back_populates="anomaly_event")


class CauseAnalysis(Base):
    __tablename__ = "cause_analyses"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(String, ForeignKey("anomaly_events.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    contribution_pct = Column(Float, nullable=False)
    cause_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    matched_case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)

    anomaly_event = relationship("AnomalyEvent", back_populates="cause_analyses")
    matched_case = relationship("Case")


class QualityPrediction(Base):
    __tablename__ = "quality_predictions"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(String, ForeignKey("anomaly_events.id"), nullable=False)
    impact_label = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    confidence_pct = Column(Float, nullable=False)

    anomaly_event = relationship("AnomalyEvent", back_populates="quality_predictions")


class RecommendedAction(Base):
    __tablename__ = "recommended_actions"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(String, ForeignKey("anomaly_events.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    priority = Column(String, nullable=False)
    action_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    score = Column(Float, nullable=False)

    anomaly_event = relationship("AnomalyEvent", back_populates="recommended_actions")


class ActionRecord(Base):
    __tablename__ = "action_records"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(String, ForeignKey("anomaly_events.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    selected_action_id = Column(Integer, ForeignKey("recommended_actions.id"), nullable=True)
    action_content = Column(Text, nullable=False)
    extra_notes = Column(Text, nullable=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_sent = Column(Boolean, default=False)
    manager_confirmed = Column(Boolean, default=False)
    tentative_result = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    anomaly_event = relationship("AnomalyEvent", back_populates="action_records")
    worker = relationship("User", foreign_keys=[worker_id])
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    selected_action = relationship("RecommendedAction")

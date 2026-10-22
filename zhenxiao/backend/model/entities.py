from sqlalchemy import BigInteger, Column, Integer, String, Text, DateTime, Date, func

from .database import Base


class Session(Base):
    __tablename__ = "sessions"
    id         = Column(String(36), primary_key=True)
    title      = Column(String(120), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"
    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(36), index=True)
    role       = Column(String(16))          # user / assistant
    content    = Column(Text)
    metadata_  = Column("metadata", Text, nullable=True)    # JSON 字符串
    created_at = Column(DateTime, server_default=func.now())


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    user_id            = Column(String(64), primary_key=True)
    age                = Column(Integer, nullable=True)
    gender             = Column(String(8), nullable=True)
    chronic_diseases   = Column(String(512), nullable=True)
    allergy_history    = Column(String(512), nullable=True)
    medication_history = Column(String(512), nullable=True)
    updated_at         = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Encounter(Base):
    __tablename__ = "encounters"
    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id      = Column(String(36), nullable=True)
    user_id         = Column(String(64), index=True, nullable=True)
    scene           = Column(String(32))   # triage/consultation/medication
    chief_complaint = Column(Text)
    risk_level      = Column(String(16), nullable=True)
    department      = Column(String(64), nullable=True)
    summary         = Column(Text, nullable=True)
    metadata_       = Column("metadata", Text, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())


class Appointment(Base):
    __tablename__ = "appointments"
    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id      = Column(String(64), index=True)
    department   = Column(String(64))
    doctor       = Column(String(64))
    doctor_title = Column(String(64), nullable=True)
    visit_date   = Column(Date)
    period       = Column(String(8))
    time_slot    = Column(String(32))
    status       = Column(String(16), default="已预约")
    created_at   = Column(DateTime, server_default=func.now())

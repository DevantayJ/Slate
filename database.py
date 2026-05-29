from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./slate.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Models ────────────────────────────────────────────────────

class Settings(Base):
    __tablename__ = "settings"
    id               = Column(Integer, primary_key=True, default=1)
    business_name    = Column(String, default="LOVE AND ESCAPISM LTD")
    owner_name       = Column(String, default="Raheem")
    email            = Column(String, default="raheem@devantayj.com")
    notify_email     = Column(String, default="raheem@devantayj.com")
    phone            = Column(String, default="075 3805 942")
    website          = Column(String, default="www.devantayj.com")
    account_name     = Column(String, default="LOVE AND ESCAPISM LTD")
    account_number   = Column(String, default="29755267")
    sort_code        = Column(String, default="04-06-05")
    sendgrid_api_key = Column(String, default="")
    app_first_used   = Column(DateTime, nullable=True)
    bank_prompt_sent = Column(Boolean, default=False)


class Client(Base):
    __tablename__ = "clients"
    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, nullable=False)
    email        = Column(String, nullable=False)
    address1     = Column(String, default="")
    address2     = Column(String, default="")
    city_postcode = Column(String, default="")
    created_at   = Column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id                  = Column(Integer, primary_key=True, index=True)
    invoice_number      = Column(String, unique=True, nullable=False)
    client_id           = Column(Integer, nullable=False)
    client_name         = Column(String, nullable=False)   # denormalised for speed
    client_email        = Column(String, nullable=False)
    date_created        = Column(String, nullable=False)   # DD/MM/YYYY
    event_date          = Column(String, default="")
    job_description     = Column(String, default="")
    usage               = Column(String, default="Social Media + Website")
    final_delivery_date = Column(String, default="")
    due_date            = Column(String, nullable=False)   # DD/MM/YYYY
    total_amount        = Column(Float, default=0)
    deposit_amount      = Column(Float, default=0)
    final_payment       = Column(Float, default=0)
    amount_due          = Column(Float, default=0)
    late_fee_rate       = Column(Float, default=0.10)
    late_fee_applied    = Column(Boolean, default=False)
    # status: draft | sent | opened | paid | overdue
    status              = Column(String, default="draft")
    sent_at             = Column(DateTime, nullable=True)
    opened_at           = Column(DateTime, nullable=True)
    paid_at             = Column(DateTime, nullable=True)
    notes               = Column(Text, default="")
    created_at          = Column(DateTime, default=datetime.utcnow)


class Expense(Base):
    __tablename__ = "expenses"
    id          = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    amount      = Column(Float, nullable=False)
    category    = Column(String, default="Other")
    date        = Column(String, nullable=False)   # DD/MM/YYYY
    notes       = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.utcnow)


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    id          = Column(Integer, primary_key=True, index=True)
    description = Column(String, unique=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"
    id           = Column(Integer, primary_key=True, index=True)
    invoice_id   = Column(Integer, nullable=False)
    reminder_type = Column(String, nullable=False)  # pre_due | due_day | late_fee | weekly | receipt
    scheduled_for = Column(DateTime, nullable=False)
    sent_at      = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


DEFAULT_JOB_DESCRIPTIONS = [
    "Event Photography",
    "Portrait Photography",
    "Commercial Photography",
    "Product Photography",
    "Wedding Photography",
    "Editorial Photography",
    "Music Video Photography",
    "Brand Campaign Photography",
]

def create_tables():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Seed default settings row
    if not db.query(Settings).first():
        db.add(Settings())
        db.commit()
    # Seed default job descriptions
    for desc in DEFAULT_JOB_DESCRIPTIONS:
        if not db.query(JobDescription).filter(JobDescription.description == desc).first():
            db.add(JobDescription(description=desc))
    db.commit()
    db.close()

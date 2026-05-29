from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import io, json

from database import get_db, create_tables, Settings, Client, Invoice, Expense, JobDescription
from pdf_generator import generate_invoice_pdf
from email_service import send_invoice_email, send_payment_receipt
from scheduler import start_scheduler

app = FastAPI(title="Slate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    create_tables()
    start_scheduler()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_app():
    return FileResponse("static/index.html")


# ── Pydantic schemas ──────────────────────────────────────────

class SettingsUpdate(BaseModel):
    business_name:    Optional[str]
    owner_name:       Optional[str]
    email:            Optional[str]
    notify_email:     Optional[str]
    phone:            Optional[str]
    website:          Optional[str]
    account_name:     Optional[str]
    account_number:   Optional[str]
    sort_code:        Optional[str]
    sendgrid_api_key: Optional[str]

class ClientCreate(BaseModel):
    name:          str
    email:         str
    address1:      Optional[str] = ""
    address2:      Optional[str] = ""
    city_postcode: Optional[str] = ""

class ClientUpdate(ClientCreate):
    pass

class InvoiceCreate(BaseModel):
    client_id:           int
    event_date:          Optional[str] = ""
    job_description:     str
    usage:               Optional[str] = "Social Media + Website"
    final_delivery_date: Optional[str] = ""
    due_date:            str           # DD/MM/YYYY
    total_amount:        float
    deposit_amount:      float
    final_payment:       float
    amount_due:          float
    notes:               Optional[str] = ""

class ExpenseCreate(BaseModel):
    description: str
    amount:      float
    category:    Optional[str] = "Other"
    date:        str            # DD/MM/YYYY
    notes:       Optional[str] = ""

class JobDescriptionCreate(BaseModel):
    description: str


# ── Helpers ───────────────────────────────────────────────────

def _fmt(amount: float) -> str:
    s = f"£{amount:,.2f}"
    return s[:-3] if s.endswith(".00") else s

def _invoice_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%d%m%y")
    count = db.query(Invoice).filter(
        Invoice.invoice_number.like(f"{today}%")
    ).count()
    suffix = chr(65 + count)  # A, B, C …
    return f"{today}{suffix}"


# ── Settings ──────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    return {
        "business_name":    s.business_name,
        "owner_name":       s.owner_name,
        "email":            s.email,
        "notify_email":     s.notify_email,
        "phone":            s.phone,
        "website":          s.website,
        "account_name":     s.account_name,
        "account_number":   s.account_number,
        "sort_code":        s.sort_code,
        "sendgrid_api_key": "••••••" if s.sendgrid_api_key else "",
    }

@app.put("/api/settings")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    for field, value in data.dict(exclude_none=True).items():
        if field == "sendgrid_api_key" and value.startswith("•"):
            continue
        setattr(s, field, value)
    if not s.app_first_used:
        s.app_first_used = datetime.utcnow()
    db.commit()
    return {"ok": True}


# ── Clients ───────────────────────────────────────────────────

@app.get("/api/clients")
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.name).all()

@app.post("/api/clients", status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    c = Client(**data.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.put("/api/clients/{cid}")
def update_client(cid: int, data: ClientUpdate, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == cid).first()
    if not c:
        raise HTTPException(404, "Client not found")
    for k, v in data.dict().items():
        setattr(c, k, v)
    db.commit()
    return c

@app.delete("/api/clients/{cid}")
def delete_client(cid: int, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == cid).first()
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"ok": True}


# ── Invoices ──────────────────────────────────────────────────

@app.get("/api/invoices")
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return [_invoice_dict(i) for i in invoices]

@app.get("/api/invoices/{iid}")
def get_invoice(iid: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404)
    return _invoice_dict(inv)

def _invoice_dict(inv: Invoice) -> dict:
    return {
        "id":                  inv.id,
        "invoice_number":      inv.invoice_number,
        "client_id":           inv.client_id,
        "client_name":         inv.client_name,
        "client_email":        inv.client_email,
        "date_created":        inv.date_created,
        "event_date":          inv.event_date,
        "job_description":     inv.job_description,
        "usage":               inv.usage,
        "final_delivery_date": inv.final_delivery_date,
        "due_date":            inv.due_date,
        "total_amount":        inv.total_amount,
        "deposit_amount":      inv.deposit_amount,
        "final_payment":       inv.final_payment,
        "amount_due":          inv.amount_due,
        "late_fee_applied":    inv.late_fee_applied,
        "status":              inv.status,
        "sent_at":             inv.sent_at.isoformat() if inv.sent_at else None,
        "opened_at":           inv.opened_at.isoformat() if inv.opened_at else None,
        "paid_at":             inv.paid_at.isoformat() if inv.paid_at else None,
        "notes":               inv.notes,
    }

@app.post("/api/invoices", status_code=201)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    inv = Invoice(
        invoice_number      = _invoice_number(db),
        client_id           = client.id,
        client_name         = client.name,
        client_email        = client.email,
        date_created        = datetime.utcnow().strftime("%d/%m/%Y"),
        event_date          = data.event_date,
        job_description     = data.job_description,
        usage               = data.usage,
        final_delivery_date = data.final_delivery_date,
        due_date            = data.due_date,
        total_amount        = data.total_amount,
        deposit_amount      = data.deposit_amount,
        final_payment       = data.final_payment,
        amount_due          = data.amount_due,
        notes               = data.notes,
        status              = "draft",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return _invoice_dict(inv)

@app.put("/api/invoices/{iid}")
def update_invoice(iid: int, data: InvoiceCreate, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404)
    if inv.status != "draft":
        raise HTTPException(400, "Only draft invoices can be edited")
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if client:
        inv.client_name  = client.name
        inv.client_email = client.email
    for k, v in data.dict().items():
        if hasattr(inv, k):
            setattr(inv, k, v)
    db.commit()
    return _invoice_dict(inv)

@app.delete("/api/invoices/{iid}")
def delete_invoice(iid: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404)
    db.delete(inv)
    db.commit()
    return {"ok": True}


# ── Send invoice ──────────────────────────────────────────────

@app.post("/api/invoices/{iid}/send")
def send_invoice(iid: int, db: Session = Depends(get_db)):
    inv      = db.query(Invoice).filter(Invoice.id == iid).first()
    settings = db.query(Settings).first()
    if not inv:
        raise HTTPException(404)
    if not settings.sendgrid_api_key:
        raise HTTPException(400, "SendGrid API key not configured in Settings")

    client = db.query(Client).filter(Client.id == inv.client_id).first()
    pdf = generate_invoice_pdf(
        invoice_number  = inv.invoice_number,
        invoice_date    = inv.date_created,
        client_name     = inv.client_name,
        client_address1 = client.address1 if client else "",
        client_address2 = f"{client.city_postcode}" if client else "",
        job_description = inv.job_description,
        event_date      = inv.event_date,
        usage           = inv.usage,
        final_delivery  = inv.final_delivery_date,
        total           = _fmt(inv.total_amount),
        deposit         = _fmt(inv.deposit_amount),
        final_payment   = _fmt(inv.final_payment),
        amount_due      = _fmt(inv.amount_due),
        business_name   = settings.account_name,
        account_number  = settings.account_number,
        sort_code       = settings.sort_code,
        phone           = settings.phone,
        email           = settings.email,
        website         = settings.website,
    )

    ok = send_invoice_email(
        api_key        = settings.sendgrid_api_key,
        from_email     = settings.email,
        to_email       = inv.client_email,
        client_name    = inv.client_name,
        invoice_number = inv.invoice_number,
        total          = _fmt(inv.total_amount),
        due_date       = inv.due_date,
        pdf_bytes      = pdf,
        owner_name     = settings.owner_name,
        business_name  = settings.business_name,
    )

    if ok:
        inv.status  = "sent"
        inv.sent_at = datetime.utcnow()
        db.commit()
    return {"ok": ok}


# ── Mark paid ─────────────────────────────────────────────────

@app.post("/api/invoices/{iid}/mark-paid")
def mark_paid(iid: int, db: Session = Depends(get_db)):
    inv      = db.query(Invoice).filter(Invoice.id == iid).first()
    settings = db.query(Settings).first()
    if not inv:
        raise HTTPException(404)

    inv.status  = "paid"
    inv.paid_at = datetime.utcnow()
    db.commit()

    if settings and settings.sendgrid_api_key:
        send_payment_receipt(
            api_key        = settings.sendgrid_api_key,
            from_email     = settings.email,
            to_email       = inv.client_email,
            client_name    = inv.client_name,
            invoice_number = inv.invoice_number,
            amount_paid    = _fmt(inv.total_amount),
            owner_name     = settings.owner_name,
            business_name  = settings.business_name,
        )
    return {"ok": True}


# ── Download PDF ──────────────────────────────────────────────

@app.get("/api/invoices/{iid}/pdf")
def download_pdf(iid: int, db: Session = Depends(get_db)):
    inv      = db.query(Invoice).filter(Invoice.id == iid).first()
    settings = db.query(Settings).first()
    if not inv:
        raise HTTPException(404)

    client = db.query(Client).filter(Client.id == inv.client_id).first()
    pdf = generate_invoice_pdf(
        invoice_number  = inv.invoice_number,
        invoice_date    = inv.date_created,
        client_name     = inv.client_name,
        client_address1 = client.address1 if client else "",
        client_address2 = client.city_postcode if client else "",
        job_description = inv.job_description,
        event_date      = inv.event_date,
        usage           = inv.usage,
        final_delivery  = inv.final_delivery_date,
        total           = _fmt(inv.total_amount),
        deposit         = _fmt(inv.deposit_amount),
        final_payment   = _fmt(inv.final_payment),
        amount_due      = _fmt(inv.amount_due),
        business_name   = settings.account_name,
        account_number  = settings.account_number,
        sort_code       = settings.sort_code,
        phone           = settings.phone,
        email           = settings.email,
        website         = settings.website,
    )
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Invoice_{inv.invoice_number}.pdf"},
    )


# ── SendGrid open-tracking webhook ────────────────────────────

@app.post("/webhook/email-events")
async def email_events(request: Request, db: Session = Depends(get_db)):
    events = await request.json()
    for event in events:
        if event.get("event") == "open":
            # SendGrid passes custom args via unique_args
            inv_number = event.get("invoice_number")
            if inv_number:
                inv = db.query(Invoice).filter(
                    Invoice.invoice_number == inv_number
                ).first()
                if inv and not inv.opened_at:
                    inv.opened_at = datetime.utcnow()
                    if inv.status == "sent":
                        inv.status = "opened"
                    db.commit()
    return {"ok": True}


# ── Expenses ──────────────────────────────────────────────────

@app.get("/api/expenses")
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.date.desc()).all()

@app.post("/api/expenses", status_code=201)
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    e = Expense(**data.dict())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e

@app.put("/api/expenses/{eid}")
def update_expense(eid: int, data: ExpenseCreate, db: Session = Depends(get_db)):
    e = db.query(Expense).filter(Expense.id == eid).first()
    if not e:
        raise HTTPException(404)
    for k, v in data.dict().items():
        setattr(e, k, v)
    db.commit()
    return e

@app.delete("/api/expenses/{eid}")
def delete_expense(eid: int, db: Session = Depends(get_db)):
    e = db.query(Expense).filter(Expense.id == eid).first()
    if not e:
        raise HTTPException(404)
    db.delete(e)
    db.commit()
    return {"ok": True}


# ── Job Descriptions ──────────────────────────────────────────

@app.get("/api/job-descriptions")
def list_job_descriptions(db: Session = Depends(get_db)):
    return [j.description for j in
            db.query(JobDescription).order_by(JobDescription.description).all()]

@app.post("/api/job-descriptions", status_code=201)
def create_job_description(data: JobDescriptionCreate, db: Session = Depends(get_db)):
    desc = data.description.strip()
    if not desc:
        raise HTTPException(400, "Description cannot be empty")
    existing = db.query(JobDescription).filter(
        JobDescription.description == desc
    ).first()
    if existing:
        return {"description": desc, "created": False}
    db.add(JobDescription(description=desc))
    db.commit()
    return {"description": desc, "created": True}

@app.delete("/api/job-descriptions/{desc}")
def delete_job_description(desc: str, db: Session = Depends(get_db)):
    j = db.query(JobDescription).filter(JobDescription.description == desc).first()
    if not j:
        raise HTTPException(404)
    db.delete(j)
    db.commit()
    return {"ok": True}


# ── Reports ───────────────────────────────────────────────────

def _parse_dd_mm_yyyy(date_str: str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        return None

@app.get("/api/reports/monthly/{year}/{month}")
def report_monthly(year: int, month: int, db: Session = Depends(get_db)):
    invoices = db.query(Invoice).filter(Invoice.status == "paid").all()
    expenses = db.query(Expense).all()

    income = sum(
        i.total_amount for i in invoices
        if (d := _parse_dd_mm_yyyy(i.date_created)) and d.year == year and d.month == month
    )
    spend = sum(
        e.amount for e in expenses
        if (d := _parse_dd_mm_yyyy(e.date)) and d.year == year and d.month == month
    )
    return {"year": year, "month": month, "income": income, "expenses": spend, "net": income - spend}

@app.get("/api/reports/biannual/{year}/{half}")
def report_biannual(year: int, half: int, db: Session = Depends(get_db)):
    months = range(1, 7) if half == 1 else range(7, 13)
    invoices = db.query(Invoice).filter(Invoice.status == "paid").all()
    expenses = db.query(Expense).all()

    monthly = []
    for m in months:
        income = sum(
            i.total_amount for i in invoices
            if (d := _parse_dd_mm_yyyy(i.date_created)) and d.year == year and d.month == m
        )
        spend = sum(
            e.amount for e in expenses
            if (d := _parse_dd_mm_yyyy(e.date)) and d.year == year and d.month == m
        )
        monthly.append({"month": m, "income": income, "expenses": spend, "net": income - spend})

    total_income = sum(r["income"] for r in monthly)
    total_spend  = sum(r["expenses"] for r in monthly)
    return {"year": year, "half": half, "monthly": monthly,
            "total_income": total_income, "total_expenses": total_spend,
            "total_net": total_income - total_spend}

@app.get("/api/reports/annual/{year}")
def report_annual(year: int, db: Session = Depends(get_db)):
    invoices = db.query(Invoice).filter(Invoice.status == "paid").all()
    expenses = db.query(Expense).all()

    monthly = []
    for m in range(1, 13):
        income = sum(
            i.total_amount for i in invoices
            if (d := _parse_dd_mm_yyyy(i.date_created)) and d.year == year and d.month == m
        )
        spend = sum(
            e.amount for e in expenses
            if (d := _parse_dd_mm_yyyy(e.date)) and d.year == year and d.month == m
        )
        monthly.append({"month": m, "income": income, "expenses": spend, "net": income - spend})

    total_income = sum(r["income"] for r in monthly)
    total_spend  = sum(r["expenses"] for r in monthly)
    return {"year": year, "monthly": monthly,
            "total_income": total_income, "total_expenses": total_spend,
            "total_net": total_income - total_spend}

"""
Slate scheduler — runs background jobs for all reminders.

Jobs:
  daily_payment_check   09:00  — check for invoices due tomorrow → nudge Raheem
  daily_client_reminder 09:30  — send due-today / overdue reminders to clients
  weekly_log_nudge      Mon 08:00 — nudge Raheem to log transactions
  bank_prompt_check     daily  — fire 30-day bank prompt once
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from database import SessionLocal, Invoice, Settings, Reminder
from email_service import (
    send_payment_check_nudge,
    send_payment_reminder,
    send_weekly_log_nudge,
    send_bank_connection_prompt,
)
from pdf_generator import generate_invoice_pdf


def _parse_date(date_str: str) -> datetime:
    """Parse DD/MM/YYYY to datetime."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        return None


def _fmt_currency(amount: float) -> str:
    return f"£{amount:,.2f}".replace(".00", "")


def daily_payment_check():
    """
    Runs at 09:00 daily.
    For each sent/opened invoice where due_date is TOMORROW and not paid,
    send Raheem a nudge to check his bank before the client reminder fires.
    """
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        if not settings or not settings.sendgrid_api_key:
            return

        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%d/%m/%Y")
        invoices = db.query(Invoice).filter(
            Invoice.status.in_(["sent", "opened"]),
            Invoice.due_date == tomorrow,
        ).all()

        for inv in invoices:
            send_payment_check_nudge(
                api_key       = settings.sendgrid_api_key,
                from_email    = settings.email,
                notify_email  = settings.notify_email,
                client_name   = inv.client_name,
                invoice_number= inv.invoice_number,
                amount_due    = _fmt_currency(inv.amount_due),
                due_date      = inv.due_date,
            )
    finally:
        db.close()


def daily_client_reminder():
    """
    Runs at 09:30 daily.
    - Due today and unpaid → send client reminder (mention late fee coming)
    - 2 days overdue → apply late fee, send updated invoice
    - 7/14/21/28 days overdue → weekly follow-up
    """
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        if not settings or not settings.sendgrid_api_key:
            return

        today = datetime.utcnow().date()
        invoices = db.query(Invoice).filter(
            Invoice.status.in_(["sent", "opened", "overdue"])
        ).all()

        for inv in invoices:
            due = _parse_date(inv.due_date)
            if not due:
                continue
            due_date = due.date()
            days_overdue = (today - due_date).days

            if days_overdue == 0:
                # Due today — friendly reminder
                send_payment_reminder(
                    api_key        = settings.sendgrid_api_key,
                    from_email     = settings.email,
                    to_email       = inv.client_email,
                    client_name    = inv.client_name,
                    invoice_number = inv.invoice_number,
                    amount_due     = _fmt_currency(inv.amount_due),
                    due_date       = inv.due_date,
                    is_overdue     = False,
                    owner_name     = settings.owner_name,
                    business_name  = settings.business_name,
                )
                inv.status = "overdue"
                db.commit()

            elif days_overdue == 2 and not inv.late_fee_applied:
                # Apply 10% late fee
                late_fee = round(inv.amount_due * inv.late_fee_rate, 2)
                inv.amount_due     = round(inv.amount_due + late_fee, 2)
                inv.late_fee_applied = True
                inv.status         = "overdue"
                db.commit()

                # Generate updated invoice PDF with new amount
                pdf = generate_invoice_pdf(
                    invoice_number  = inv.invoice_number,
                    invoice_date    = inv.date_created,
                    client_name     = inv.client_name,
                    client_address1 = "",
                    client_address2 = "",
                    job_description = inv.job_description,
                    event_date      = inv.event_date,
                    usage           = inv.usage,
                    final_delivery  = inv.final_delivery_date,
                    total           = _fmt_currency(inv.total_amount),
                    deposit         = _fmt_currency(inv.deposit_amount),
                    final_payment   = _fmt_currency(inv.final_payment),
                    amount_due      = _fmt_currency(inv.amount_due),
                    business_name   = settings.account_name,
                    account_number  = settings.account_number,
                    sort_code       = settings.sort_code,
                    phone           = settings.phone,
                    email           = settings.email,
                    website         = settings.website,
                )
                send_payment_reminder(
                    api_key        = settings.sendgrid_api_key,
                    from_email     = settings.email,
                    to_email       = inv.client_email,
                    client_name    = inv.client_name,
                    invoice_number = inv.invoice_number,
                    amount_due     = _fmt_currency(inv.amount_due),
                    due_date       = inv.due_date,
                    is_overdue     = True,
                    owner_name     = settings.owner_name,
                    business_name  = settings.business_name,
                )

            elif days_overdue > 2 and days_overdue % 7 == 0:
                # Weekly follow-up
                send_payment_reminder(
                    api_key        = settings.sendgrid_api_key,
                    from_email     = settings.email,
                    to_email       = inv.client_email,
                    client_name    = inv.client_name,
                    invoice_number = inv.invoice_number,
                    amount_due     = _fmt_currency(inv.amount_due),
                    due_date       = inv.due_date,
                    is_overdue     = True,
                    owner_name     = settings.owner_name,
                    business_name  = settings.business_name,
                )
    finally:
        db.close()


def weekly_log_nudge():
    """Runs Monday 08:00 — nudge Raheem to log transactions."""
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        if not settings or not settings.sendgrid_api_key:
            return
        send_weekly_log_nudge(
            api_key      = settings.sendgrid_api_key,
            from_email   = settings.email,
            notify_email = settings.notify_email,
        )
    finally:
        db.close()


def bank_prompt_check():
    """
    Runs daily — fires once after 30 days of first use.
    """
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        if not settings or not settings.sendgrid_api_key or settings.bank_prompt_sent:
            return
        if not settings.app_first_used:
            settings.app_first_used = datetime.utcnow()
            db.commit()
            return
        days_since = (datetime.utcnow() - settings.app_first_used).days
        if days_since >= 30:
            sent = send_bank_connection_prompt(
                api_key      = settings.sendgrid_api_key,
                from_email   = settings.email,
                notify_email = settings.notify_email,
            )
            if sent:
                settings.bank_prompt_sent = True
                db.commit()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_payment_check,  CronTrigger(hour=9,  minute=0))
    scheduler.add_job(daily_client_reminder, CronTrigger(hour=9,  minute=30))
    scheduler.add_job(weekly_log_nudge,      CronTrigger(day_of_week="mon", hour=8, minute=0))
    scheduler.add_job(bank_prompt_check,     CronTrigger(hour=10, minute=0))
    scheduler.start()
    return scheduler

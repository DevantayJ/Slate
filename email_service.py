import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition, TrackingSettings, OpenTracking
)


def _client(api_key: str) -> SendGridAPIClient:
    return SendGridAPIClient(api_key)


def _make_pdf_attachment(pdf_bytes: bytes, filename: str) -> Attachment:
    encoded = base64.b64encode(pdf_bytes).decode()
    return Attachment(
        FileContent(encoded),
        FileName(filename),
        FileType("application/pdf"),
        Disposition("attachment"),
    )


# ── Send invoice to client ────────────────────────────────────

def send_invoice_email(
    api_key: str,
    from_email: str,
    to_email: str,
    client_name: str,
    invoice_number: str,
    total: str,
    due_date: str,
    pdf_bytes: bytes,
    owner_name: str = "Raheem",
    business_name: str = "Love and Escapism",
) -> bool:
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f"Invoice #{invoice_number} — {business_name}",
        html_content=f"""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:40px;max-width:600px;margin:0 auto;">
          <h2 style="letter-spacing:4px;font-weight:300;font-size:13px;color:#aaa;text-transform:uppercase;">{business_name}</h2>
          <hr style="border:none;border-top:1px solid #333;margin:16px 0 32px;">
          <p style="font-size:15px;margin-bottom:16px;">Hi {client_name},</p>
          <p style="color:#ccc;line-height:1.8;margin-bottom:16px;">
            It was a pleasure working with you — thank you for having me. Please find your invoice attached.
            I've included a summary below for easy reference.
          </p>
          <div style="background:#1a1a1a;border-radius:8px;padding:24px;margin:24px 0;">
            <p style="margin:0 0 6px;color:#aaa;font-size:11px;letter-spacing:2px;text-transform:uppercase;">Invoice #{invoice_number}</p>
            <p style="margin:0 0 12px;font-size:26px;font-weight:bold;">{total}</p>
            <p style="margin:0;color:#aaa;font-size:13px;">Payment due: <span style="color:#fff">{due_date}</span></p>
          </div>
          <p style="color:#ccc;line-height:1.8;margin-bottom:16px;">
            Payment can be made via bank transfer using the details on the invoice.
            Once received, I'll send over a confirmation straight away.
          </p>
          <p style="color:#ccc;line-height:1.8;margin-bottom:16px;">
            Please note that by making payment you confirm you've read and agreed to the terms and conditions
            on page 2 of the attached PDF.
          </p>
          <p style="color:#ccc;line-height:1.8;">
            If you have any questions at all, feel free to reply to this email — I'm always happy to help.
          </p>
          <p style="margin-top:36px;line-height:1.8;">Warm regards,<br>
          <strong style="font-size:16px;">{owner_name}</strong><br>
          <span style="color:#aaa;font-size:12px;">{business_name}</span></p>
          <hr style="border:none;border-top:1px solid #222;margin:36px 0 16px;">
          <p style="color:#444;font-size:11px;text-align:center;letter-spacing:3px;">L O V E  A N D  E S C A P I S M</p>
        </div>
        """,
    )
    message.attachment = _make_pdf_attachment(pdf_bytes, f"Invoice_{invoice_number}.pdf")
    tracking = TrackingSettings()
    tracking.open_tracking = OpenTracking(enable=True)
    message.tracking_settings = tracking
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


# ── Notify Raheem: check bank before reminder goes out ────────

def send_payment_check_nudge(
    api_key: str,
    from_email: str,
    notify_email: str,
    client_name: str,
    invoice_number: str,
    amount_due: str,
    due_date: str,
) -> bool:
    message = Mail(
        from_email=from_email,
        to_emails=notify_email,
        subject=f"[Slate] Check bank — {client_name} payment due tomorrow",
        html_content=f"""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:32px;max-width:500px;margin:0 auto;">
          <h3 style="letter-spacing:3px;font-weight:300;font-size:12px;color:#aaa;">SLATE · PAYMENT REMINDER</h3>
          <hr style="border:none;border-top:1px solid #333;margin:12px 0 24px;">
          <p>A reminder email is scheduled to go out to <strong>{client_name}</strong> tomorrow for invoice
          <strong>#{invoice_number}</strong> ({amount_due} due on {due_date}).</p>
          <p style="color:#ccc;">If they've already paid, open Slate and mark the invoice as paid before the reminder sends — otherwise they'll receive it automatically.</p>
          <a href="#" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#fff;color:#000;text-decoration:none;font-weight:bold;border-radius:4px;">Open Slate</a>
          <hr style="border:none;border-top:1px solid #333;margin:32px 0 12px;">
          <p style="color:#555;font-size:11px;text-align:center;letter-spacing:2px;">S L A T E</p>
        </div>
        """,
    )
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


# ── Client payment reminder ───────────────────────────────────

def send_payment_reminder(
    api_key: str,
    from_email: str,
    to_email: str,
    client_name: str,
    invoice_number: str,
    amount_due: str,
    due_date: str,
    is_overdue: bool = False,
    owner_name: str = "Raheem",
    business_name: str = "Love and Escapism",
) -> bool:
    if is_overdue:
        subject = f"Overdue: Invoice #{invoice_number} — {business_name}"
        intro = f"This is a reminder that invoice <strong>#{invoice_number}</strong> for <strong>{amount_due}</strong> was due on {due_date} and remains unpaid."
        note = "Please note a 10% late fee has been applied to your updated invoice attached below."
    else:
        subject = f"Payment Reminder: Invoice #{invoice_number} — {business_name}"
        intro = f"This is a friendly reminder that invoice <strong>#{invoice_number}</strong> for <strong>{amount_due}</strong> is due today ({due_date})."
        note = "Please ensure payment is made by end of day to avoid a 10% late fee being applied."

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=f"""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:40px;max-width:600px;margin:0 auto;">
          <h2 style="letter-spacing:4px;font-weight:300;font-size:13px;color:#aaa;text-transform:uppercase;">LOVE AND ESCAPISM</h2>
          <hr style="border:none;border-top:1px solid #333;margin:16px 0 32px;">
          <p style="font-size:15px;">Hi {client_name},</p>
          <p style="color:#ccc;line-height:1.7;">{intro}</p>
          <p style="color:#ccc;line-height:1.7;">{note}</p>
          <div style="background:#1a1a1a;border-radius:8px;padding:24px;margin:24px 0;">
            <p style="margin:0 0 8px;color:#aaa;font-size:12px;letter-spacing:2px;">INVOICE #{invoice_number}</p>
            <p style="margin:0;font-size:20px;font-weight:bold;">{amount_due} due</p>
          </div>
          <p style="color:#ccc;line-height:1.7;">If you've already arranged payment, please disregard this message.</p>
          <p style="margin-top:32px;">Kind regards,<br><strong>{owner_name}</strong><br>
          <span style="color:#aaa;font-size:12px;">{business_name}</span></p>
          <hr style="border:none;border-top:1px solid #333;margin:32px 0 16px;">
          <p style="color:#555;font-size:11px;text-align:center;letter-spacing:2px;">L O V E  A N D  E S C A P I S M</p>
        </div>
        """,
    )
    tracking = TrackingSettings()
    tracking.open_tracking = OpenTracking(enable=True)
    message.tracking_settings = tracking
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


# ── Payment received receipt ──────────────────────────────────

def send_payment_receipt(
    api_key: str,
    from_email: str,
    to_email: str,
    client_name: str,
    invoice_number: str,
    amount_paid: str,
    owner_name: str = "Raheem",
    business_name: str = "Love and Escapism",
) -> bool:
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f"Payment Received — Invoice #{invoice_number}",
        html_content=f"""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:40px;max-width:600px;margin:0 auto;">
          <h2 style="letter-spacing:4px;font-weight:300;font-size:13px;color:#aaa;text-transform:uppercase;">LOVE AND ESCAPISM</h2>
          <hr style="border:none;border-top:1px solid #333;margin:16px 0 32px;">
          <p style="font-size:15px;">Hi {client_name},</p>
          <p style="color:#ccc;line-height:1.7;">
            Thank you — your payment of <strong>{amount_paid}</strong> has been received for invoice
            <strong>#{invoice_number}</strong>. We're all squared away.
          </p>
          <p style="color:#ccc;line-height:1.7;">
            We look forward to delivering your images. If you have any questions in the meantime, feel free to reach out.
          </p>
          <p style="margin-top:32px;">Thank you again,<br><strong>{owner_name}</strong><br>
          <span style="color:#aaa;font-size:12px;">{business_name}</span></p>
          <hr style="border:none;border-top:1px solid #333;margin:32px 0 16px;">
          <p style="color:#555;font-size:11px;text-align:center;letter-spacing:2px;">L O V E  A N D  E S C A P I S M</p>
        </div>
        """,
    )
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


# ── Weekly transaction log nudge ──────────────────────────────

def send_weekly_log_nudge(
    api_key: str,
    from_email: str,
    notify_email: str,
) -> bool:
    message = Mail(
        from_email=from_email,
        to_emails=notify_email,
        subject="[Slate] Weekly reminder — log your transactions",
        html_content="""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:32px;max-width:500px;margin:0 auto;">
          <h3 style="letter-spacing:3px;font-weight:300;font-size:12px;color:#aaa;">SLATE · WEEKLY NUDGE</h3>
          <hr style="border:none;border-top:1px solid #333;margin:12px 0 24px;">
          <p>Quick reminder to log any expenses or income from this week in Slate so your records stay up to date.</p>
          <p style="color:#ccc;">Takes two minutes now. Saves hours at tax time.</p>
          <a href="#" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#fff;color:#000;text-decoration:none;font-weight:bold;border-radius:4px;">Open Slate</a>
          <hr style="border:none;border-top:1px solid #333;margin:32px 0 12px;">
          <p style="color:#555;font-size:11px;text-align:center;letter-spacing:2px;">S L A T E</p>
        </div>
        """,
    )
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


# ── 30-day bank connection prompt ─────────────────────────────

def send_bank_connection_prompt(
    api_key: str,
    from_email: str,
    notify_email: str,
) -> bool:
    message = Mail(
        from_email=from_email,
        to_emails=notify_email,
        subject="[Slate] Ready to connect your bank account?",
        html_content="""
        <div style="font-family:Arial,sans-serif;background:#000;color:#fff;padding:32px;max-width:500px;margin:0 auto;">
          <h3 style="letter-spacing:3px;font-weight:300;font-size:12px;color:#aaa;">SLATE · ONE MONTH IN</h3>
          <hr style="border:none;border-top:1px solid #333;margin:12px 0 24px;">
          <p>You've been using Slate for a month — nice work staying on top of things.</p>
          <p style="color:#ccc;line-height:1.7;">
            When you're ready, you can connect your bank account so Slate automatically pulls in your transactions
            and marks invoices as paid — no manual logging needed.
          </p>
          <p style="color:#ccc;">Head to Settings in Slate to get started.</p>
          <a href="#" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#fff;color:#000;text-decoration:none;font-weight:bold;border-radius:4px;">Open Settings</a>
          <hr style="border:none;border-top:1px solid #333;margin:32px 0 12px;">
          <p style="color:#555;font-size:11px;text-align:center;letter-spacing:2px;">S L A T E</p>
        </div>
        """,
    )
    try:
        _client(api_key).send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False

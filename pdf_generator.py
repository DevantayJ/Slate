import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black

W, H = A4

BANNER_BG = HexColor('#3A3A3A')
FOOTER_BG = HexColor('#252525')
MID_TEXT  = HexColor('#AAAAAA')
LINE_COL  = HexColor('#555555')
WHITE     = white
BLACK     = black


def sp(text):
    """Single-space letter tracking."""
    return " ".join(list(str(text)))


def wrap_text(c, text, x, y, max_width, font, size, color, line_gap=11):
    c.setFont(font, size)
    c.setFillColor(color)
    words = str(text).split()
    line, lines = "", []
    for word in words:
        candidate = (line + " " + word).strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_gap
    return y


def draw_bullet(c, text, x, y, max_width, size=7.5, gap=11):
    c.setFont("Helvetica", size)
    c.setFillColor(WHITE)
    c.drawString(x, y, "•")
    y = wrap_text(c, text, x + 10, y, max_width - 10, "Helvetica", size, WHITE, line_gap=gap)
    return y


def generate_invoice_pdf(
    invoice_number: str,
    invoice_date: str,
    client_name: str,
    client_address1: str,
    client_address2: str,
    job_description: str,
    event_date: str,
    usage: str,
    final_delivery: str,
    total: str,
    deposit: str,
    final_payment: str,
    amount_due: str,
    business_name: str = "LOVE AND ESCAPISM LTD",
    account_number: str = "29755267",
    sort_code: str     = "04-06-05",
    phone: str         = "075 3805 942",
    email: str         = "raheem@devantayj.com",
    website: str       = "www.devantayj.com",
) -> bytes:
    """Generate invoice PDF and return as bytes."""
    buf = io.BytesIO()
    cv  = canvas.Canvas(buf, pagesize=A4)

    # ── PAGE 1 ────────────────────────────────────────────────
    cv.setFillColor(BLACK)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    LEFT  = 44
    RIGHT = W - 44

    # Brand header
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica", 9)
    cv.drawCentredString(W / 2, H - 28, sp("LOVE AND ESCAPISM"))

    # DATE – top right
    cv.setFont("Helvetica", 7)
    cv.drawRightString(W - 38, H - 22, sp("DATE"))
    cv.setFont("Helvetica", 8.5)
    cv.drawRightString(W - 38, H - 35, sp(invoice_date))

    # Divider
    cv.setStrokeColor(LINE_COL)
    cv.setLineWidth(0.4)
    cv.line(38, H - 43, W - 38, H - 43)

    # Banner
    BAN_T = H - 52
    BAN_H = 108
    BAN_B = BAN_T - BAN_H
    cv.setFillColor(BANNER_BG)
    cv.rect(28, BAN_B, W - 56, BAN_H, fill=1, stroke=0)

    cv.setFillColor(WHITE)
    cv.setFont("Helvetica", 36)
    cv.drawString(44, BAN_B + 64, "I N V O I C E")
    cv.setFont("Helvetica", 8)
    cv.drawString(44, BAN_B + 44, sp(f"INVOICE #{invoice_number}"))

    # Invoice To
    cv.setFont("Helvetica", 6.5)
    cv.drawRightString(W - 44, BAN_B + 96, sp("INVOICE TO"))
    cv.setFont("Helvetica", 8.5)
    cv.drawRightString(W - 44, BAN_B + 80, sp(client_name.upper()))
    cv.setFont("Helvetica", 7)
    if client_address1:
        cv.drawRightString(W - 44, BAN_B + 65, sp(client_address1))
    if client_address2:
        cv.drawRightString(W - 44, BAN_B + 51, sp(client_address2))

    # Job details
    BODY_Y = BAN_B - 52

    def detail_row(label, value, y):
        cv.setFont("Helvetica-Bold", 9)
        cv.setFillColor(WHITE)
        cv.drawString(LEFT, y, sp(label))
        cv.setFont("Helvetica", 9)
        cv.drawString(LEFT + 165, y, sp(value))

    detail_row("JOB DESCRIPTION", job_description, BODY_Y)
    detail_row("EVENT DATE",      event_date,       BODY_Y - 22)
    detail_row("USAGE",           usage,            BODY_Y - 44)
    detail_row("FINAL DELIVERY",  final_delivery,   BODY_Y - 66)

    # Payment table
    TBL_Y = BODY_Y - 128
    C1, C2, C3 = 130, 295, 460

    cv.setFillColor(MID_TEXT)
    cv.setFont("Helvetica", 7.5)
    for cx, lbl in [(C1, "TOTAL"), (C2, "DEPOSIT"), (C3, "FINAL PAYMENT")]:
        cv.drawCentredString(cx, TBL_Y, sp(lbl))

    cv.setStrokeColor(WHITE)
    cv.setLineWidth(0.8)
    cv.line(LEFT, TBL_Y - 8, RIGHT, TBL_Y - 8)

    cv.setFillColor(WHITE)
    cv.setFont("Helvetica", 13)
    for cx, val in [(C1, total), (C2, deposit), (C3, final_payment)]:
        cv.drawCentredString(cx, TBL_Y - 30, str(val))

    cv.line(LEFT, TBL_Y - 44, RIGHT, TBL_Y - 44)

    cv.setFillColor(MID_TEXT)
    cv.setFont("Helvetica", 9)
    cv.drawCentredString(W / 2, TBL_Y - 68, "Additional")

    cv.setStrokeColor(WHITE)
    cv.line(LEFT, TBL_Y - 92, RIGHT, TBL_Y - 92)

    DUE_Y = TBL_Y - 118
    cv.setFillColor(MID_TEXT)
    cv.setFont("Helvetica", 7.5)
    cv.drawCentredString(360, DUE_Y,      sp("DUE"))
    cv.drawCentredString(360, DUE_Y - 22, sp("TOTAL"))

    cv.setFillColor(WHITE)
    cv.setFont("Helvetica", 13)
    cv.drawString(410, DUE_Y,      str(amount_due))
    cv.drawString(410, DUE_Y - 22, str(total))

    # Terms
    TERMS_Y = DUE_Y - 65
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 7.5)
    for ln in [
        "By paying this invoice, the Client acknowledges that they have read,",
        "understood, and accepted the terms and conditions below.",
    ]:
        cv.drawCentredString(W / 2, TERMS_Y, ln)
        TERMS_Y -= 14

    ul = "Please note that payment of the deposit is required to secure your slot."
    ul_w = cv.stringWidth(ul, "Helvetica-Bold", 7.5)
    ul_x = (W - ul_w) / 2
    TERMS_Y -= 3
    cv.drawString(ul_x, TERMS_Y, ul)
    cv.setLineWidth(0.4)
    cv.setStrokeColor(WHITE)
    cv.line(ul_x, TERMS_Y - 1.5, ul_x + ul_w, TERMS_Y - 1.5)

    # Footer
    FTR_H = 90
    cv.setFillColor(FOOTER_BG)
    cv.rect(0, 0, W, FTR_H, fill=1, stroke=0)

    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(30, FTR_H - 16, sp("PAYMENT INFORMATION"))

    y_fp = FTR_H - 30
    for bold, normal, indent in [
        ("NAME: ",      business_name,  62),
        ("ACCOUNT: ",   account_number, 72),
        ("SORT CODE: ", sort_code,      84),
    ]:
        cv.setFont("Helvetica-Bold", 7.5)
        cv.drawString(30, y_fp, bold)
        cv.setFont("Helvetica", 7.5)
        cv.drawString(indent, y_fp, normal)
        y_fp -= 13

    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawRightString(W - 30, FTR_H - 16, sp("CONTACTS"))
    cv.setFont("Helvetica", 7.5)
    for i, line in enumerate([phone, email, website]):
        cv.drawRightString(W - 30, FTR_H - 30 - i * 13, line)

    # ── PAGE 2  T&C ───────────────────────────────────────────
    cv.showPage()
    cv.setFillColor(BLACK)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    cv.setFillColor(WHITE)
    cv.setFont("Helvetica", 9)
    cv.drawCentredString(W / 2, H - 28, sp("LOVE AND ESCAPISM"))
    cv.setStrokeColor(HexColor('#444444'))
    cv.setLineWidth(0.4)
    cv.line(38, H - 38, W - 38, H - 38)

    MAX_W = W - 76
    y = H - 60

    def tc_head(text):
        nonlocal y
        cv.setFont("Helvetica-Bold", 8.5)
        cv.setFillColor(WHITE)
        cv.drawString(38, y, text)
        y -= 13

    def tc_body(text):
        nonlocal y
        y = wrap_text(cv, text, 38, y, MAX_W, "Helvetica", 7.5, WHITE, line_gap=11)

    def tc_bullet(text):
        nonlocal y
        y = draw_bullet(cv, text, 38, y, MAX_W, size=7.5, gap=11)

    tc_head("Services Provided:")
    tc_body("Love and Escapism agrees to provide the services and deliverables as described in the invoice above")
    y -= 5

    tc_head("Payments and Deposit:")
    tc_bullet("A non-refundable deposit of 50% is required to secure the booking. The date and time of the photography session will be reserved only upon receipt of this deposit. The deposit will be deducted from the total package price. For payments below £250, full payment is required upfront.")
    tc_bullet("The remaining balance must be paid in full before the delivery of the final edited images. A 10% late fee will incur after delivery.")
    y -= 5

    tc_head("Cancellation and Rescheduling:")
    tc_body("a) In the event of cancellation by the Client:")
    tc_bullet("Cancellation made after the session has been reserved will result in the forfeiture of the non-refundable deposit.")
    tc_bullet("Cancellation made less than 48 hours before the scheduled date will require the Client to pay the full agreed-upon package price.")
    tc_body("b) In the event of rescheduling by the Client:")
    tc_bullet("Rescheduling made 48 hours or more before the scheduled date will require a rescheduling fee of 25% of the total fee.")
    tc_bullet("Rescheduling made less than 48 hours before the scheduled date may result in the forfeiture of the non-refundable deposit or require an additional fee, as agreed upon by both parties.")
    tc_bullet("In case of an emergency, the client will be able to reschedule the booking within a 14-day time period if proof of said emergency can be provided.")
    y -= 5

    tc_head("Copyright, Usage and Limitation of Liability:")
    tc_bullet("Love and Escapism retains full copyright ownership of all images, whether in digital or print form, unless otherwise agreed upon in writing.")
    tc_bullet("The Client is granted usage exclusively as agreed upon and as explained in writing above. Any usage outside the initial agreement is strictly prohibited unless discussed and approved in writing by Love and Escapism.")
    tc_bullet("The Client agrees to credit Love and Escapism whenever the images are shared or published, including on social media platforms, websites, and blogs.")
    tc_bullet("The Client grants Love and Escapism permission to use the images for advertising, marketing, or promotional purposes unless otherwise specified in writing by the Client.")
    tc_bullet("Love and Escapism will exercise reasonable care and professionalism during the provision of services. However, in the event of unforeseen circumstances or technical malfunctions, Love and Escapism's liability will be limited to a refund of the paid amount.")
    tc_bullet("Love and Escapism is not responsible for any loss, damage, or injury caused to persons or property during the provision of services, including but not limited to accidents, equipment failure, or force majeure events.")
    tc_bullet("The Client agrees to indemnify and hold Love and Escapism harmless against any claims, damages, expenses, or legal actions arising from the Client's use or misuse of the images or breach of these terms and conditions.")
    y -= 6

    y = wrap_text(cv, (
        "This agreement constitutes the entire understanding between the Photographer "
        "and the Client and supersedes any prior agreements or understandings, whether "
        "written or verbal."
    ), 38, y, MAX_W, "Helvetica-Bold", 8, WHITE, line_gap=12)

    cv.setFont("Helvetica", 8.5)
    cv.setFillColor(WHITE)
    cv.drawCentredString(W / 2, 28, sp("LOVE AND ESCAPISM"))

    cv.save()
    buf.seek(0)
    return buf.read()

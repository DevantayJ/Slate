# Slate — Setup Guide

## What you need first

- Python 3.10 or later (free — download from python.org)
- A SendGrid account (free — sendgrid.com, 100 emails/day)
- Your email domain verified in SendGrid (takes ~5 minutes)

---

## Step 1 — Install Python dependencies

Open Terminal, navigate to the `slate` folder, then run:

```bash
pip install -r requirements.txt
```

---

## Step 2 — Set up SendGrid

1. Go to **sendgrid.com** and create a free account
2. Go to **Settings → Sender Authentication** and verify `raheem@devantayj.com`
   (SendGrid will send a confirmation email — click the link)
3. Go to **Settings → API Keys** → Create API Key → Full Access
4. Copy the key — you'll only see it once

---

## Step 3 — Run Slate locally

```bash
cd slate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at **http://localhost:8000**

Go to **Settings** in the app and paste your SendGrid API key. Fill in your business details. Done.

---

## Step 4 — Install on your phone (PWA)

**iPhone:**
1. Open `http://localhost:8000` in Safari
2. Tap the Share button (square with arrow)
3. Tap "Add to Home Screen"
4. Tap Add

Slate now appears on your home screen like a native app.

---

## Step 5 — Deploy to Render (access from anywhere)

Deploying puts Slate on the internet so you can use it from your phone on the go.

1. Create a free account at **render.com**
2. Create a new **Web Service**
3. Upload the `slate` folder (or connect a GitHub repo)
4. Set these values:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Once deployed, you'll get a URL like `https://slate-xxxx.onrender.com`
6. Open that URL in Safari on your phone → Add to Home Screen → done

> **Note:** Free Render instances sleep after 15 minutes of inactivity. The first
> load after sleeping takes ~30 seconds. Upgrade to a paid plan ($7/month) to
> keep it always-on once you're using it daily.

---

## Step 6 — Configure SendGrid webhook (open tracking)

So Slate knows when a client has opened their invoice:

1. In SendGrid: **Settings → Mail Settings → Event Webhook**
2. Set the HTTP POST URL to: `https://your-render-url.onrender.com/webhook/email-events`
3. Tick **Opened** under Engagement Events
4. Save

---

## How reminders work (automatic)

| Time | What happens |
|------|-------------|
| Daily 9:00am | You get a nudge if a client's payment is due tomorrow — check your bank before the reminder fires |
| Daily 9:30am | Client gets a reminder if payment is due today; late fee applied on day 2 overdue; weekly follow-ups after that |
| Monday 8:00am | You get a nudge to log any transactions from the week |
| 30 days after first use | You get a prompt to consider connecting your bank account |

All reminders stop automatically the moment you mark an invoice as paid.

---

## File structure

```
slate/
├── main.py          — FastAPI backend (all routes)
├── database.py      — Database models
├── pdf_generator.py — Invoice PDF generation
├── email_service.py — SendGrid email functions
├── scheduler.py     — Automated reminders
├── requirements.txt — Python dependencies
├── slate.db         — Your data (created automatically on first run)
└── static/
    ├── index.html   — The full app
    ├── manifest.json — PWA config
    └── sw.js        — Service worker (offline support)
```

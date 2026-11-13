# KilimoRada 
 
KilimoRada helps Kenyan farmers on basic phones get trusted farming information through **USSD and SMS**, with no smartphone or internet needed.
 
Farmers dial a USSD code to check input and market prices, see the weather, ask an AI expert, find verified agrovets, and report or verify fake fertilizer and seed batch codes. Extension officers use a web dashboard to manage farmers, reply to reports by SMS, post prices and send alerts.
 
**Live API:** https://kilimo-rada-api.onrender.com/api/health
**API docs (Swagger):** https://kilimo-rada-api.onrender.com/apidocs
 
---
 
## Features
 
**For farmers (USSD + SMS)**
- Fertilizer, seed, fuel and market prices
- Live weather for Kiambu, Nakuru and Uasin Gishu
- Ask an AI expert (answer arrives by SMS, max 3 questions per hour)
- List of verified agrovets
- Report fake batch codes or scam phone numbers (auto-flagged after 3 reports)
- Verify a batch code: GENUINE, FAKE or not in records
- English and Kiswahili
- "SMS me this" on every result
**For officers (web API)**
- Sign up and log in with two-step login (email code)
- Two roles: **admin** and **officer**
- Manage farmers, reports, market prices and broadcasts
- Reply to farmer reports by SMS
- Admins manage the batch code registry and verified agrovets
- Dashboard stats
---
 
## Tech Stack
 
| Part | Tools |
|---|---|
| Backend | Python, Flask, SQLAlchemy, Flask-Migrate, Marshmallow |
| Database | PostgreSQL (Supabase) |
| Auth | Flask sessions + bcrypt + email one-time code |
| USSD / SMS | Africa's Talking |
| AI | Google Gemini |
| Email | SendGrid |
| Images | Cloudinary |
| Docs | Swagger (Flasgger) |
| Tests | Pytest |
| Hosting | Render |
 
---
 
## Run It Locally
 
**1. Clone and open the server folder**
```bash
git clone https://github.com/<your-team>/kilimorada.git
cd kilimorada/server
```
 
**2. Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate          # Mac/Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell
```
 
**3. Install packages**
```bash
pip install -r requirements.txt
```
 
**4. Create your `.env` file**
```bash
cp .env.example .env
```
Then fill it in (see the table below).
 
**5. Set up the database**
```bash
flask db upgrade
```
**6. Start the server**
```bash
python app.py
```
Open http://localhost:5555/api/health and http://localhost:5555/apidocs
 
---
 
## Environment Variables
 
| Name | What it is |
|---|---|
| `FLASK_APP` | `app.py` |
| `SECRET_KEY` | Long random string for sessions |
| `DATABASE_URL` | PostgreSQL connection string (Supabase session pooler) |
| `TWO_FACTOR_ENABLED` | `true` or `false` (use `false` while developing) |
| `AT_USERNAME` | `sandbox` for testing |
| `AT_API_KEY` | Africa's Talking API key (needed for SMS) |
| `GEMINI_API_KEY` | Google Gemini key (needed for Ask Expert) |
| `GEMINI_MODEL` | e.g. `gemini-3.7-flash` |
| `SENDGRID_API_KEY` | SendGrid key (needed for login code emails) |
| `MAIL_FROM` | Verified sender email |
| `CLOUDINARY_URL` | Cloudinary URL (needed for profile pictures) |
 
If a key is missing, that feature prints to the terminal instead of sending. Never commit your `.env` file.
 
---
 
## USSD Menu
 
```
KilimoRada
1. Fertilizer        6. Weather
2. Seeds             7. Agrovets
3. Fuel              8. Report Fake
4. Market Prices     9. Verify Batch
5. Ask Expert        10. Kiswahili
                     11. Register (new numbers only)
```
`0` = back, `00` = main menu
 
**Africa's Talking callback URL:** `https://<your-app>.onrender.com/api/ussd`
 
---
 
## Main API Routes
 
All routes start with `/api`. Full details and a "try it out" page are at `/apidocs`.
 
| Area | Routes |
|---|---|
| Auth | `POST /signup`, `POST /login`, `POST /verify-otp`, `POST /resend-otp`, `GET /me`, `DELETE /logout` |
| Users | `GET /users`, `PATCH /users/<id>/role`, `PATCH /users/me`, `GET /dashboard` |
| Farmers | `GET/POST /farmers`, `GET/PATCH/DELETE /farmers/<id>` |
| Reports | `GET/POST /reports`, `GET/PATCH/DELETE /reports/<id>`, `POST /reports/<id>/reply` |
| Prices | `GET/POST /prices`, `PATCH/DELETE /prices/<id>` |
| Broadcasts | `GET/POST /broadcasts` |
| Trust | `/batch-codes`, `/agrovets`, `/input-reports`, `/ai-questions`, `/ussd-stats` |
| USSD | `POST /ussd`, `POST /ussd/events` |
 
**Who can do what**
- Not logged in: sign up, log in, USSD
- Officer: view and manage farmers, reports, prices, broadcasts
- Owner only: edit or delete their own market prices
- Admin only: manage users, delete farmers and reports, manage batch codes and agrovets
---
 
## Run the Tests
 
```bash
cd server
pytest
```
Tests use a temporary database and never send real SMS, emails or AI requests.
 
---
 

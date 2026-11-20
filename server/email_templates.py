"""Branded HTML emails for KilimoRada.
Email apps (Gmail, Outlook) ignore most CSS, so this uses tables and inline styles only."""
import os
from html import escape

GREEN = "#15803D"
LIGHT_GREEN = "#F0FDF4"
BORDER = "#DCFCE7"
TEXT = "#334155"
MUTED = "#64748B"


def _frontend_url():
    return os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _logo_url():
    # Must be a public PNG (Gmail blocks SVG). Defaults to the logo in client/public.
    return os.environ.get("EMAIL_LOGO_URL") or f"{_frontend_url()}/icon-192.png"


def _button(text, link):
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 8px;">
      <tr>
        <td style="background:{GREEN};border-radius:8px;">
          <a href="{link}" target="_blank"
             style="display:inline-block;padding:12px 24px;font-size:15px;font-weight:600;
                    color:#ffffff;text-decoration:none;border-radius:8px;">{escape(text)}</a>
        </td>
      </tr>
    </table>"""


def _code_box(code):
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;">
      <tr>
        <td align="center"
            style="background:{LIGHT_GREEN};border:1px solid {BORDER};border-radius:10px;padding:20px;">
          <span style="font-family:'Courier New',monospace;font-size:34px;font-weight:700;
                       letter-spacing:10px;color:{GREEN};">{escape(code)}</span>
        </td>
      </tr>
    </table>"""


def layout(title, body_html, preheader=""):
    """Wraps any content in the KilimoRada email frame (logo header, white card, footer)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#F7F9F8;font-family:Inter,Segoe UI,Arial,sans-serif;">
  <span style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</span>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#F7F9F8;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
               style="max-width:520px;background:#ffffff;border:1px solid #E2E8F0;border-radius:14px;overflow:hidden;">
          <tr>
            <td style="background:{LIGHT_GREEN};border-bottom:1px solid {BORDER};padding:20px 28px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <img src="{_logo_url()}" width="40" height="40" alt="KilimoRada"
                         style="display:block;border:0;border-radius:8px;">
                  </td>
                  <td style="vertical-align:middle;padding-left:12px;font-size:18px;font-weight:700;
                             letter-spacing:0.5px;color:{GREEN};">KilimoRada</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;color:{TEXT};font-size:15px;line-height:1.6;">
              <h1 style="margin:0 0 12px;font-size:20px;color:#0F172A;">{escape(title)}</h1>
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:18px 28px;border-top:1px solid #F1F5F9;color:{MUTED};font-size:12px;line-height:1.5;">
              KilimoRada &middot; Farmer support dashboard for extension officers<br>
              You received this email because of activity on your KilimoRada account.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------- the 5 emails ----------
def verify_email(name, code, minutes):
    body = f"""
      <p style="margin:0;">Hi {escape(name)},</p>
      <p style="margin:12px 0 0;">Welcome to KilimoRada. Enter this code to verify your email address:</p>
      {_code_box(code)}
      <p style="margin:0;color:{MUTED};font-size:13px;">
        The code expires in {minutes} minutes. If you did not sign up, you can ignore this email.
      </p>"""
    return "Verify your KilimoRada email", layout("Verify your email", body, f"Your code is {code}")


def login_code(name, code, minutes):
    body = f"""
      <p style="margin:0;">Hi {escape(name)},</p>
      <p style="margin:12px 0 0;">Use this code to finish logging in:</p>
      {_code_box(code)}
      <p style="margin:0;color:{MUTED};font-size:13px;">
        The code expires in {minutes} minutes. If you did not try to log in, change your password.
      </p>"""
    return "Your KilimoRada login code", layout("Your login code", body, f"Your code is {code}")


def new_officer_waiting(admin_name, officer):
    rows = "".join(
        f"""<tr>
              <td style="padding:6px 0;color:{MUTED};width:90px;">{label}</td>
              <td style="padding:6px 0;color:#0F172A;font-weight:600;">{escape(value or "-")}</td>
            </tr>"""
        for label, value in (
            ("Name", officer.name),
            ("Email", officer.email),
            ("County", officer.county),
            ("Ward", officer.ward),
        )
    )
    body = f"""
      <p style="margin:0;">Hi {escape(admin_name)},</p>
      <p style="margin:12px 0 0;">A new officer verified their email and is waiting for your approval:</p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
             style="margin:16px 0 0;border-top:1px solid #F1F5F9;border-bottom:1px solid #F1F5F9;font-size:14px;">
        {rows}
      </table>
      {_button("Review in dashboard", f"{_frontend_url()}/users")}"""
    return "New officer waiting for approval", layout("New officer waiting", body, f"{officer.name} wants to join")


def account_approved(name):
    body = f"""
      <p style="margin:0;">Hi {escape(name)},</p>
      <p style="margin:12px 0 0;">
        Good news: an admin approved your KilimoRada account. You can now log in and start
        replying to farmer reports in your area.
      </p>
      {_button("Log in", f"{_frontend_url()}/login")}"""
    return "Your KilimoRada account is approved", layout("You're approved", body, "You can now log in")


def account_rejected(name):
    body = f"""
      <p style="margin:0;">Hi {escape(name)},</p>
      <p style="margin:12px 0 0;">
        Your request to join KilimoRada was not approved. If you think this is a mistake,
        please contact your county agriculture office.
      </p>"""
    return "Your KilimoRada signup", layout("Signup not approved", body, "Your signup was not approved")
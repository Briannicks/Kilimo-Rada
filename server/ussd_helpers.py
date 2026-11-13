"""Helpers for the USSD: navigation, safe text, weather, AI answers, background SMS."""
import json
import os
import re
import secrets
import string
import threading
import time
import urllib.request
from datetime import timedelta

from flask import Response, current_app

from config import db
from models import AiQuestion, Farmer, InputReport, MarketPrice, Report, utcnow
from services import send_sms
from ussd_text import COUNTIES, TEXT

MAX_USSD_CHARS = 182
MAX_SMS_ANSWER = 140
_weather_cache = {}  # county -> (time fetched, data)


# ---------- navigation and safe text ----------
def clean_steps(text):
    """Applies 0 = back and 00 = main menu to the inputs joined by '*'."""
    steps = []
    for step in (text or "").split("*"):
        step = step.strip()
        if step == "00":
            steps = []
        elif step == "0":
            if steps:
                steps.pop()
        elif step:
            steps.append(step)
    return steps


def safe_text(text):
    """Removes & < > brackets and other characters USSD gateways reject."""
    return re.sub(r"[^A-Za-z0-9 .,:;!?%'\-/+\n#]", "", text or "")


def con(body):
    return Response(("CON " + safe_text(body))[:MAX_USSD_CHARS], mimetype="text/plain")


def end(body):
    return Response(("END " + safe_text(body))[:MAX_USSD_CHARS], mimetype="text/plain")


# ---------- background work (so USSD replies instantly) ----------
def run_in_background(function, *args):
    app = current_app._get_current_object()

    def task():
        with app.app_context():
            function(*args)

    threading.Thread(target=task, daemon=True).start()


def sms_later(phone, message):
    run_in_background(send_sms, [phone], safe_text(message))


# ---------- prices from the database ----------
def price_lines(item, limit=3):
    prices = (
        MarketPrice.query.filter(MarketPrice.crop.ilike(item))
        .order_by(MarketPrice.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [f"{p.market} KES {p.price:,} per {p.unit}" for p in prices]


def price_text(item, lang):
    t = TEXT[lang]
    lines = price_lines(item)
    if not lines:
        return t["no_price"].format(item=item)
    return t["prices_for"].format(item=item) + "\n" + "\n".join(lines)


# ---------- live weather (Open-Meteo, free, no key) ----------
def weather_text(county, lang):
    t = TEXT[lang]
    cached = _weather_cache.get(county)
    if cached and time.time() - cached[0] < 30 * 60:
        data = cached[1]
    else:
        lat, lon = COUNTIES[county]
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=Africa%2FNairobi&forecast_days=1"
        )
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                data = json.loads(response.read())["daily"]
            _weather_cache[county] = (time.time(), data)
        except Exception as error:
            print(f"Weather failed: {error}")
            return t["weather_fail"]
    return t["weather"].format(
        county=county,
        tmin=round(data["temperature_2m_min"][0]),
        tmax=round(data["temperature_2m_max"][0]),
        rain=data["precipitation_probability_max"][0],
    )


# ---------- Ask Expert (Gemini) ----------
def questions_this_hour(phone):
    since = utcnow() - timedelta(hours=1)
    return AiQuestion.query.filter(AiQuestion.phone == phone, AiQuestion.created_at >= since).count()


def ask_gemini(question, lang):
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")
    if not api_key or not model:
        return TEXT[lang]["expert_unavailable"]
    language = "Kiswahili" if lang == "sw" else "English"
    prompt = (
        "You are a Kenyan agricultural extension officer answering a farmer by SMS. "
        f"Reply in {language}, plain text only, no symbols or emojis, under 140 characters. "
        "Give practical, safe advice. If unsure, tell them to visit their local extension officer.\n"
        f"Question: {question}"
    )
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        answer = safe_text((response.text or "").replace("\n", " ")).strip()
        return answer[:MAX_SMS_ANSWER] or TEXT[lang]["expert_unavailable"]
    except Exception as error:
        print(f"Gemini failed: {error}")
        return TEXT[lang]["expert_unavailable"]


def answer_question(question_id):
    """Runs in the background: get AI answer, save it, SMS it, and put it in the officers' inbox."""
    question = db.session.get(AiQuestion, question_id)
    question.answer = ask_gemini(question.question, question.language)
    db.session.commit()
    send_sms([question.phone], f"KilimoRada: {question.answer}")

    # Registered farmers' questions also go to the reports inbox so an officer can check the AI answer
    farmer = Farmer.query.filter_by(phone=question.phone).first()
    if farmer:
        db.session.add(Report(
            farmer=farmer,
            category="other",
            description=f"Ask Expert: {question.question}",
            reply=f"AI answer sent: {question.answer}",
        ))
        db.session.commit()


# ---------- fake input reports ----------
def new_reference():
    while True:
        ref = "KR" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        if not InputReport.query.filter_by(reference=ref).first():
            return ref


def report_count(value):
    return InputReport.query.filter_by(kind="batch_code", value=value.upper()).count()
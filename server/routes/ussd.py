import re

from flask import Blueprint, current_app, request

from config import db
from models import Agrovet, AiQuestion, Farmer, InputReport, UssdProfile, VerifiedProduct
from ussd_helpers import (
    MAX_USSD_CHARS, answer_question, clean_steps, con, end, new_reference, price_lines, price_text,
    questions_this_hour, report_count, run_in_background, sms_later, weather_text,
)
from ussd_text import COUNTIES, FERTILIZERS, FUELS, PRODUCE, SEEDS, TEXT

bp = Blueprint("ussd", __name__)

FLAG_AFTER_REPORTS = 3
MAX_QUESTIONS_PER_HOUR = 3


# ---------- small helpers ----------
def get_profile(phone):
    profile = UssdProfile.query.filter_by(phone=phone).first()
    if not profile:
        profile = UssdProfile(phone=phone, language="en")
        db.session.add(profile)
        db.session.commit()
    return profile


def main_menu(lang, farmer):
    t = TEXT[lang]
    lines = [f"{i}. {name}" for i, name in enumerate(t["menu"], start=1)]
    if not farmer:
        lines.append(f"11. {t['register']}")
    return "KilimoRada\n" + "\n".join(lines)


def show_with_sms(phone, lang, text, rest):
    """Shows a result with '1. SMS me this'. If the farmer picks 1, it is sent by SMS."""
    t = TEXT[lang]
    if not rest:
        room = MAX_USSD_CHARS - len("CON \n") - len(t["sms_options"])
        return con(f"{text[:room]}\n{t['sms_options']}")
    if rest[0] == "1":
        sms_later(phone, f"KilimoRada: {text}")
        return end(t["sms_sent"])
    return end(t["invalid"])


def pick_list(phone, lang, items, rest, make_text):
    """Menu of 3 items -> result -> optional SMS."""
    t = TEXT[lang]
    if not rest:
        options = "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))
        return con(f"{t['choose']}\n{options}\n{t['back']}")
    if not rest[0].isdigit() or not 1 <= int(rest[0]) <= len(items):
        return end(t["invalid"])
    item = items[int(rest[0]) - 1]
    return show_with_sms(phone, lang, make_text(item, lang), rest[1:])


# ---------- one function per main-menu option ----------
def fertilizer(phone, lang, farmer, rest):
    return pick_list(phone, lang, FERTILIZERS, rest, price_text)


def seeds(phone, lang, farmer, rest):
    return pick_list(phone, lang, SEEDS, rest, price_text)


def fuel(phone, lang, farmer, rest):
    t = TEXT[lang]
    lines = []
    for item in FUELS:
        latest = price_lines(item, limit=1)
        if latest:
            lines.append(f"{item}: {latest[0]}")
    text = t["fuel_title"] + "\n" + "\n".join(lines) if lines else t["no_fuel"]
    return show_with_sms(phone, lang, text, rest)


def market_prices(phone, lang, farmer, rest):
    return pick_list(phone, lang, PRODUCE, rest, price_text)


def ask_expert(phone, lang, farmer, rest):
    t = TEXT[lang]
    if not rest:
        return con(t["ask_prompt"])
    question = " ".join(rest).strip()
    if len(question) > 80:
        return end(t["ask_too_long"])
    if questions_this_hour(phone) >= MAX_QUESTIONS_PER_HOUR:
        return end(t["ask_limit"])
    saved = AiQuestion(phone=phone, question=question, language=lang)
    db.session.add(saved)
    db.session.commit()
    run_in_background(answer_question, saved.id)
    return end(t["ask_done"])


def weather(phone, lang, farmer, rest):
    return pick_list(phone, lang, list(COUNTIES), rest, weather_text)


def agrovets(phone, lang, farmer, rest):
    t = TEXT[lang]
    shops = Agrovet.query.order_by(Agrovet.created_at.desc()).limit(3).all()
    if not shops:
        return end(t["no_agrovets"])
    lines = [f"{s.name}, {s.ward} {s.phone}" for s in shops]
    return show_with_sms(phone, lang, t["agrovets_title"] + "\n" + "\n".join(lines), rest)


def report_fake(phone, lang, farmer, rest):
    t = TEXT[lang]
    if not rest:
        return con(t["report_menu"])
    kinds = {"1": "batch_code", "2": "scam_number"}
    kind = kinds.get(rest[0])
    if not kind:
        return end(t["invalid"])
    if len(rest) == 1:
        return con(t["report_code"] if kind == "batch_code" else t["report_number"])

    value = rest[1].strip()
    if kind == "batch_code":
        value = re.sub(r"\s", "", value).upper()
    else:
        value = Farmer.normalize_phone(value)
    try:
        report = InputReport(reference=new_reference(), phone=phone, kind=kind, value=value)
        db.session.add(report)
        db.session.commit()
    except ValueError:
        db.session.rollback()
        return end(t["invalid"])
    sms_later(phone, t["report_sms"].format(value=report.value, ref=report.reference))
    return end(t["report_done"].format(ref=report.reference))


def verify_batch(phone, lang, farmer, rest):
    t = TEXT[lang]
    if not rest:
        return con(t["verify_prompt"])
    code = re.sub(r"\s", "", rest[0]).upper()
    product = VerifiedProduct.query.filter_by(batch_code=code).first()
    reports = report_count(code)

    if (product and product.status == "fake") or reports >= FLAG_AFTER_REPORTS:
        return end(t["fake"].format(code=code, count=reports))
    if product:
        return end(t["genuine"].format(code=code, product=product.product, maker=product.manufacturer))
    return end(t["unknown"].format(code=code))


def toggle_language(phone, lang, farmer, rest):
    profile = get_profile(phone)
    profile.language = "sw" if profile.language == "en" else "en"
    db.session.commit()
    return end(TEXT[profile.language]["lang_set"])


def register(phone, lang, farmer, rest):
    t = TEXT[lang]
    if farmer:
        return end(t["already"].format(name=farmer.name))
    prompts = [t["reg_name"], t["reg_ward"], t["reg_crop"]]
    if len(rest) < 3:
        return con(prompts[len(rest)])
    try:
        farmer = Farmer(name=rest[0], phone=phone, ward=rest[1], main_crop=rest[2], registered_via="ussd")
        db.session.add(farmer)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return end(str(error))
    return end(t["reg_done"].format(name=farmer.name, crop=farmer.main_crop))


OPTIONS = {
    "1": fertilizer, "2": seeds, "3": fuel, "4": market_prices, "5": ask_expert,
    "6": weather, "7": agrovets, "8": report_fake, "9": verify_batch,
    "10": toggle_language, "11": register,
}


# ---------- routes ----------
@bp.post("/ussd")
def ussd():
    """USSD callback for Africa's Talking
    ---
    tags: [USSD]
    consumes: [application/x-www-form-urlencoded]
    parameters:
      - {name: sessionId, in: formData, type: string}
      - {name: phoneNumber, in: formData, type: string}
      - {name: text, in: formData, type: string}
    responses:
      200: {description: Plain-text USSD screen starting with CON or END}
    """
    phone = Farmer.normalize_phone(request.form.get("phoneNumber", ""))
    steps = clean_steps(request.form.get("text", ""))
    lang = get_profile(phone).language
    farmer = Farmer.query.filter_by(phone=phone).first()

    if not steps:
        return con(main_menu(lang, farmer))

    handler = OPTIONS.get(steps[0])
    if not handler:
        return end(TEXT[lang]["invalid"])
    return handler(phone, lang, farmer, steps[1:])


@bp.post("/ussd/events")
def ussd_events():
    """Africa's Talking session events (logs failed sessions)
    ---
    tags: [USSD]
    responses:
      200: {description: Logged}
    """
    status = request.form.get("status", "")
    session_id = request.form.get("sessionId", "")
    if status.lower() == "failed":
        current_app.logger.warning(
            f"USSD session {session_id} failed: {request.form.get('errorMessage', '')}"
        )
    else:
        current_app.logger.info(f"USSD session {session_id}: {status}")
    return "", 200
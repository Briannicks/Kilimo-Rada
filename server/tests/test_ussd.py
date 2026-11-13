import json
import sys

import pytest

from config import db
from models import AiQuestion, Farmer, InputReport, MarketPrice, Report, VerifiedProduct

PHONE = "+254700000099"


def dial(client, text, phone=PHONE):
    response = client.post("/api/ussd", data={"sessionId": "s1", "phoneNumber": phone, "text": text})
    body = response.get_data(as_text=True)
    assert response.mimetype == "text/plain"
    assert len(body) <= 182, f"{text!r} is {len(body)} chars"
    assert "&" not in body
    return body


@pytest.fixture
def prices(admin):
    db.session.add_all([
        MarketPrice(crop="DAP", market="Nakuru", unit="50kg bag", price=3500, owner=admin),
        MarketPrice(crop="Petrol", market="Nairobi", unit="litre", price=180, owner=admin),
        MarketPrice(crop="Maize", market="Eldoret", unit="90kg bag", price=3600, owner=admin),
    ])
    db.session.commit()


@pytest.fixture
def fake_weather(monkeypatch):
    class FakeResponse:
        def read(self):
            return json.dumps({"daily": {
                "temperature_2m_min": [13.4], "temperature_2m_max": [25.6],
                "precipitation_probability_max": [70],
            }}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    helpers = sys.modules["ussd_helpers"]
    helpers._weather_cache.clear()
    monkeypatch.setattr(helpers.urllib.request, "urlopen", lambda url, timeout: FakeResponse())


@pytest.fixture
def fake_ai(monkeypatch):
    monkeypatch.setattr(sys.modules["ussd_helpers"], "ask_gemini",
                        lambda question, lang: "Use certified seed and plant early.")



def test_main_menu(client):
    body = dial(client, "")
    assert body.startswith("CON KilimoRada")
    assert "11. Register" in body


def test_back_and_main_menu(client):
    assert "1. DAP" in dial(client, "1*1*0")       # 0 goes back to the fertilizer list
    assert "KilimoRada" in dial(client, "1*1*00")  # 00 goes to the main menu


def test_invalid_option(client):
    assert dial(client, "99").startswith("END")



def test_fertilizer_price_from_database(client, prices):
    body = dial(client, "1*1")
    assert "Nakuru KES 3,500 per 50kg bag" in body
    assert "1. SMS me this" in body


def test_no_price_posted_yet(client):
    assert "No CAN price posted yet" in dial(client, "1*2")


def test_sms_me_this(client, prices, sms_outbox):
    assert "Sent to your phone" in dial(client, "1*1*1")
    assert sms_outbox[0]["to"] == [PHONE]
    assert "3,500" in sms_outbox[0]["message"]


def test_fuel_prices(client, prices):
    assert "Petrol" in dial(client, "3")


def test_market_prices(client, prices):
    assert "Eldoret KES 3,600" in dial(client, "4*1")



def test_weather(client, fake_weather):
    assert "Nakuru today: 13 to 26 C, rain chance 70" in dial(client, "6*2")



def test_ask_expert_sends_answer_by_sms(client, fake_ai, sms_outbox):
    assert "arrive by SMS" in dial(client, "5*How do I store maize?")
    question = AiQuestion.query.first()
    assert question.answer == "Use certified seed and plant early."
    assert sms_outbox[0]["to"] == [PHONE]


def test_registered_farmer_question_goes_to_inbox(client, fake_ai, sms_outbox):
    db.session.add(Farmer(name="Kip Rono", phone=PHONE, registered_via="ussd"))
    db.session.commit()
    dial(client, "5*When should I plant beans?")
    assert Report.query.first().description == "Ask Expert: When should I plant beans?"


def test_ask_expert_limit(client, fake_ai, sms_outbox):
    for i in range(3):
        dial(client, f"5*Question {i}")
    assert "3 questions this hour" in dial(client, "5*One more")


def test_question_too_long(client):
    assert "too long" in dial(client, "5*" + "x" * 81)



def test_no_agrovets_yet(client):
    assert "No verified agrovets" in dial(client, "7")



def test_report_fake_code(client, sms_outbox):
    body = dial(client, "8*1*abc 123")
    assert "Ref KR" in body
    report = InputReport.query.first()
    assert report.value == "ABC123"
    assert report.reference in sms_outbox[0]["message"]


def test_report_scam_number(client, sms_outbox):
    dial(client, "8*2*0711999888")
    assert InputReport.query.first().value == "+254711999888"


def test_verify_genuine_fake_and_unknown(client, admin):
    db.session.add_all([
        VerifiedProduct(batch_code="DAP2026A01", product="DAP 50kg", manufacturer="Yara", added_by=admin),
        VerifiedProduct(batch_code="DAPX99", product="DAP 50kg", manufacturer="Unknown", status="fake"),
    ])
    db.session.commit()
    assert "GENUINE" in dial(client, "9*dap2026a01")
    assert "FAKE" in dial(client, "9*DAPX99")
    assert "not in our records" in dial(client, "9*ZZZ999")


def test_auto_flag_after_three_reports(client, sms_outbox):
    for phone in ("+254700000001", "+254700000002", "+254700000003"):
        dial(client, "8*1*BAD123", phone)
    assert "FAKE" in dial(client, "9*BAD123")



def test_language_toggle(client):
    assert "Kiswahili" in dial(client, "10")
    assert "Mbolea" in dial(client, "")
    assert "English" in dial(client, "10")
    assert "Fertilizer" in dial(client, "")


def test_register_by_ussd(client):
    assert "full name" in dial(client, "11")
    assert "Asante Kip Rono" in dial(client, "11*Kip Rono*Tinet*Maize")
    farmer = Farmer.query.filter_by(phone=PHONE).first()
    assert farmer.registered_via == "ussd"
    assert "11. Register" not in dial(client, "")


def test_events_endpoint(client):
    response = client.post("/api/ussd/events", data={"sessionId": "s1", "status": "Failed", "errorMessage": "x"})
    assert response.status_code == 200
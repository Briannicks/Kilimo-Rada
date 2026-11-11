from flask import Blueprint, Response, request

bp = Blueprint("ussd", __name__)


def reply(text):
    """Africa's Talking expects plain text starting with CON (continue) or END (finish)."""
    return Response(text, mimetype="text/plain")


@bp.post("/ussd")
def ussd():
    """USSD callback for Africa's Talking (menu only today; database tomorrow)
    ---
    tags: [USSD]
    consumes: [application/x-www-form-urlencoded]
    parameters:
      - {name: sessionId, in: formData, type: string}
      - {name: serviceCode, in: formData, type: string}
      - {name: phoneNumber, in: formData, type: string}
      - {name: text, in: formData, type: string}
    responses:
      200:
        description: Plain-text USSD screen
    """
    text = request.form.get("text", "")
    steps = text.split("*") if text else []

    # Main menu
    if not steps:
        return reply(
            "CON Karibu KilimoRada\n"
            "1. Register\n"
            "2. Report a problem\n"
            "3. Check market prices"
        )

    choice = steps[0]

    # 1. Register: name -> ward -> crop
    if choice == "1":
        if len(steps) == 1:
            return reply("CON Enter your full name:")
        if len(steps) == 2:
            return reply("CON Enter your ward:")
        if len(steps) == 3:
            return reply("CON Enter your main crop (e.g. Maize):")
        name, ward, crop = steps[1], steps[2], steps[3]
        # tomorrow: 
        return reply(f"END Asante {name}! You are registered for {crop} updates in {ward}.")

    # 2. Report a problem: category -> description
    if choice == "2":
        if len(steps) == 1:
            return reply(
                "CON What is the problem?\n"
                "1. Pests\n2. Disease\n3. Weather\n4. Other"
            )
        if len(steps) == 2:
            return reply("CON Describe the problem briefly:")
        #tomorrow: 
        return reply("END Thank you. An officer will reply to you by SMS.")

    # 3. Check prices
    if choice == "3":
        if len(steps) == 1:
            return reply("CON Enter crop name (e.g. Maize):")
        crop = steps[1]
        #tomorrow: 
        return reply(f"END Prices for {crop} coming soon.")

    return reply("END Invalid choice. Please try again.")
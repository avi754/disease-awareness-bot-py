import os
from flask import Flask, request, Response
import json
import re

app = Flask(__name__)

# Load curated disease content
with open("content.json", "r", encoding="utf-8") as f:
    CONTENT = json.load(f)

PORT = int(os.environ.get("PORT", "10000"))

# --- helpers ---
DISEASES = ["dengue", "malaria", "tb"]
HI_WORDS = {"hi", "hindi", "हिंदी"}  # simple language switchers

def detect_lang(text: str) -> str:
    t = text.strip().lower()
    return "hi" if t in HI_WORDS or " हिंदी" in t else "en"

def find_disease(text: str):
    s = text.lower()
    if "dengue" in s: return "dengue"
    if "malaria" in s: return "malaria"
    if "tb" in s or "tuberculosis" in s or "टीबी" in s: return "tb"
    return None

def section_from_text(text: str):
    s = text.lower()
    if re.search(r"\b(symptom|symptoms)\b", s): return "symptoms"
    if "prevention" in s or "prevent" in s: return "prevention"
    if "red" in s or "flag" in s or "red-flag" in s: return "red_flags"
    if "dont" in s or "do not" in s or "avoid" in s: return "dont"
    if "help" in s or "helpline" in s: return "help"
    return None

def get_card(lang: str, disease: str, section: str | None):
    data = CONTENT.get(lang, {}).get(disease)
    if not data:
        return "Content not available yet."
    if section and section in data:
        values = ", ".join(data[section])
        title = disease.upper()
        label = section.replace("_", " ").title()
        return f"*{title} — {label}*\n{values}"
    # full compact card
    return (
        f"*{disease.upper()}*\n"
        f"Symptoms: {', '.join(data['symptoms'])}\n"
        f"Prevention: {', '.join(data['prevention'])}\n"
        f"Red-flags: {', '.join(data['red_flags'])}\n"
        f"Help: {', '.join(data['help'])}\n"
        f"More: symptoms / prevention / red / help"
    )

def menu(lang: str):
    if lang == "hi":
        return ("रोग चुनें: Dengue, Malaria, TB\n"
                "उदाहरण: 'dengue symptoms'\n"
                "भाषा बदलें: 'hi' लिखें\n"
                "ध्यान दें: यह जागरूकता हेतु है, निदान नहीं।")
    return ("Choose disease: Dengue, Malaria, TB\n"
            "Example: 'dengue symptoms'\n"
            "Switch language: type 'hi'\n"
            "Note: This is awareness, not diagnosis.")

def twiml_message(text: str) -> str:
    # Twilio expects XML (TwiML) for SMS/WhatsApp replies from a webhook
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{safe}</Message>
</Response>"""

DISCLAIMER_EN = ("⚠️ Health info only. Not a diagnosis. "
                 "If red-flags are present or you feel very unwell, seek urgent care.")

DISCLAIMER_HI = ("⚠️ यह केवल जागरूकता हेतु जानकारी है, निदान नहीं। "
                 "गंभीर लक्षण हों तो तुरंत चिकित्सा सहायता लें।")

@app.post("/twilio/webhook")
def twilio_webhook():
    text = (request.form.get("Body") or "").strip()
    lang = detect_lang(text)

    # quick exits: menu/help
    if re.fullmatch(r"(menu|help|\?)", text.strip().lower()):
        reply = menu(lang)
    else:
        disease = find_disease(text)
        section = section_from_text(text)
        if disease:
            reply = get_card(lang, disease, section)
        else:
            # no disease found -> show menu and a hint
            reply = menu(lang)

    # add a short disclaimer
    reply += ("\n\n" + (DISCLAIMER_HI if lang == "hi" else DISCLAIMER_EN))

    return Response(twiml_message(reply), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

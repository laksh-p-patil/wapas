"""
wapas_logic.py  -  the "backend" of Wapas.

This file has NO screens in it. It only does the work:
  1. Talks to the AI (Gemini, OpenAI or Claude) using your API key.
  2. Reads the bank SMS and pulls out the important details.
  3. Loads and saves the rules table (rules.csv).
  4. Writes letters (with AI, or with a fixed template if the AI is off).
  5. Saves cases in a small database file (wapas_cases.db).

The screens are in app.py. app.py calls the functions in this file.
"""

import json
import re
import sqlite3
import time
from urllib.parse import quote
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).parent
RULES_FILE = APP_DIR / "rules.csv"
DB_FILE = APP_DIR / "wapas_cases.db"

# Model names change over time. If you get a "model not found" error,
# copy a current model name from your AI provider's website into the app's sidebar.
DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash-lite",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
}

# These instructions are sent to the AI every time. They keep it safe and honest.
SYSTEM_PROMPT = """You are Wapas, an assistant that helps people in India whose bank accounts
were frozen during cyber-fraud investigations.
Rules you must always follow:
- Use ONLY the rules given to you in the message. Never invent laws, sections, court cases,
  dates, helpline numbers or facts about the person.
- If information is missing, write it as [square brackets] so the person can fill it in.
- If you are unsure, say so and recommend free legal aid.
- Never ask for OTPs, PINs, passwords, full account numbers or money.
- Use simple, respectful language. This is not legal advice."""

EXAMPLE_SMS = (
    "Dear Customer, your A/c XX4417 at ABC Bank, Gandhi Bazaar branch has been marked "
    "DEBIT FREEZE on 22-09-2026 as per instructions of Cyber Crime PS, Patna "
    "(Ack No. 31509260012345) regarding a disputed credit of Rs.150. "
    "Please contact your branch. - ABC Bank"
)

# The details we try to find in every SMS
DETAIL_FIELDS = ["bank", "branch", "last4", "amount", "freeze_date", "police", "case_no"]


# ---------------------------------------------------------------------------
# 1. Talking to the AI
# ---------------------------------------------------------------------------
def _ask_ai_once(provider, api_key, model, prompt, system, image=None):
    """One attempt at talking to the AI. Raises an error if it fails.
    image = (image_bytes, mime_type) if we are sending a photo, otherwise None."""
    if image and provider != "gemini":
        raise ValueError("Reading screenshots is set up for Gemini only. Please paste the SMS text instead.")
    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        contents = prompt
        if image:
            contents = [types.Part.from_bytes(data=image[0], mime_type=image[1]), prompt]
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0.2),
            )
            return response.text
        except Exception as first_error:
            if _is_busy(first_error) or image:
                raise
            # Backup: Google's newer "Interactions" API
            try:
                interaction = client.interactions.create(model=model, input=system + "\n\n" + prompt)
                return interaction.output_text
            except Exception:
                raise first_error

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model, max_tokens=1500, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    raise ValueError(f"Unknown AI provider: {provider}")


def _is_busy(error):
    """True if the AI company's servers are just busy (worth trying again)."""
    text = str(error).lower()
    return any(word in text for word in ["503", "unavailable", "high demand", "overloaded", "529", "500 internal"])


def ask_ai(provider, api_key, model, prompt, system=SYSTEM_PROMPT, image=None):
    """Send a message to the AI and return (answer_text, error_text).
    If the servers are busy, it waits and tries again (up to 3 tries).
    If something goes wrong, answer_text is None and error_text explains why."""
    if not api_key:
        return None, "No API key yet. Add one in the sidebar or in .streamlit/secrets.toml."
    # Remove spaces or invisible characters that sneak in when copying a model name
    model = re.sub(r"[^A-Za-z0-9._\-/]", "", model or "")
    last_error = None
    for attempt in range(3):
        try:
            return _ask_ai_once(provider, api_key.strip(), model, prompt, system, image), None
        except Exception as error:  # wrong key, no internet, wrong model name, busy servers...
            last_error = error
            if _is_busy(error) and attempt < 2:
                time.sleep(2 * (attempt + 1))  # wait 2 seconds, then 4 seconds
                continue
            break
    return None, f"{type(last_error).__name__}: {last_error}"


# ---------------------------------------------------------------------------
# 2. Reading the bank SMS
# ---------------------------------------------------------------------------
KNOWN_BANKS = ["State Bank of India", "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Canara Bank",
               "Kotak", "Bank of Baroda", "Union Bank", "Punjab National Bank", "PNB",
               "Karnataka Bank", "Indian Bank", "IDFC", "Yes Bank", "ABC Bank"]


def only_last4(value):
    """Keep only the last 4 digits of an account number, so we never store the full number."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-4:] if digits else ""


def extract_without_ai(sms):
    """Backup method: find details using simple text patterns (no AI needed)."""
    text = sms or ""
    found = {field: "" for field in DETAIL_FIELDS}

    for bank in KNOWN_BANKS:
        if bank.lower() in text.lower():
            found["bank"] = bank
            break

    match = re.search(r"([A-Z][A-Za-z ]{2,30}?)\s+branch", text)
    if match:
        found["branch"] = match.group(1).split(",")[-1].strip()

    match = re.search(r"[Xx*]{2,}\s?(\d{4})", text) or re.search(r"a/?c\D{0,12}(\d{4,})", text, re.I)
    if match:
        found["last4"] = only_last4(match.group(1))

    match = re.search(r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d{1,2})?)", text, re.I)
    if match:
        found["amount"] = "₹" + match.group(1).rstrip(".")

    match = re.search(r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b", text)
    if match:
        found["freeze_date"] = match.group(1)

    match = re.search(r"((?:Cyber\s*Crime|Cyber|CEN)[^.,()]*?(?:PS|Police Station|Cell)(?:,\s*[A-Z][a-z]+)?)", text, re.I)
    if match:
        found["police"] = match.group(1).strip()

    match = re.search(r"(?:FIR|Case|Complaint|Ack(?:nowledgement)?)\s*(?:No\.?|Number)?\s*[:#-]?\s*([A-Z0-9/\-]{5,})", text, re.I)
    if match:
        found["case_no"] = match.group(1)

    return found


def extract_details(sms, provider, api_key, model):
    """Pull the details out of the SMS. Tries the AI first, then falls back to patterns.
    Returns (details_dict, method_used, error_or_None)."""
    backup = extract_without_ai(sms)
    prompt = f"""Read this bank SMS and return ONLY a JSON object with these keys:
bank, branch, last4, amount, freeze_date, police, case_no.
- last4 = only the last 4 digits of the account number.
- Use "" for anything not in the SMS. Do not guess.

SMS:
\"\"\"{sms}\"\"\""""
    answer, error = ask_ai(provider, api_key, model, prompt)
    if answer:
        match = re.search(r"\{.*\}", answer, re.S)  # find the {...} part of the answer
        if match:
            try:
                data = json.loads(match.group(0))
                details = {field: str(data.get(field, "") or "").strip() for field in DETAIL_FIELDS}
                details["last4"] = only_last4(details["last4"])
                # If the AI missed something the patterns found, use the pattern result
                for field in DETAIL_FIELDS:
                    if not details[field]:
                        details[field] = backup[field]
                return details, "AI", None
            except json.JSONDecodeError:
                error = "The AI's answer was not in the expected format."
    return backup, "patterns (AI off)", error


# ---------------------------------------------------------------------------
# 3. The rules table
# ---------------------------------------------------------------------------
def load_rules():
    return pd.read_csv(RULES_FILE, dtype=str).fillna("")


def save_rules(rules_df):
    rules_df.fillna("").to_csv(RULES_FILE, index=False)


def rules_for(rules_df, situation):
    """Rules for one situation: 'frozen', 'scammed' or 'lent' (plus rules marked 'all')."""
    wanted = rules_df["applies_to"].str.strip().str.lower().isin([situation, "all"])
    return rules_df[wanted]


def rules_as_text(rules_df):
    return "\n".join(f"- {r['rule']} (Source: {r['source']})" for _, r in rules_df.iterrows())


# ---------------------------------------------------------------------------
# 4. Letters
# ---------------------------------------------------------------------------
def _blank(value, label):
    return value.strip() if value and value.strip() else f"[{label}]"


def _fill_name(letter, name):
    """If the AI left a name placeholder like [Your Name], put the real name in."""
    name = (name or "").strip()
    if not name:
        return letter
    return re.sub(r"\[\s*(your\s+)?(full\s+)?name\s*\]", name, letter, flags=re.I)


def template_letter(d, rules_df):
    """Fixed letter used when the AI is off. It still uses the rules table."""
    letter_rules = rules_for(rules_df, "frozen")
    letter_rules = letter_rules[letter_rules["use_in_letter"].str.lower() == "yes"]
    basis = "\n".join(f"- {r['rule']}" for _, r in letter_rules.iterrows())
    case_part = f" (reference {d['case_no']})" if d.get("case_no") else ""
    return f"""To,
The Branch Manager,
{_blank(d.get('bank'), 'bank name')}, {_blank(d.get('branch'), 'branch')} branch

Date: {date.today().strftime('%d %B %Y')}

Subject: Request to limit the debit freeze on my account ending {_blank(d.get('last4'), 'last 4 digits')} to the disputed amount

Dear Sir/Madam,

I, {_blank(d.get('name'), 'your full name')}, hold the account ending {_blank(d.get('last4'), 'last 4 digits')} at your branch. On {_blank(d.get('freeze_date'), 'date of freeze')}, a debit freeze was placed on my account on instructions from {_blank(d.get('police'), 'police station / cyber cell')}{case_part}.

I understand this is linked to a payment of {_blank(d.get('amount'), 'amount')} that I received from a customer in the normal course of my work. I did not know the payer and had no part in any fraud.

I request you to:
1. Share the details of the freeze instruction: the police station, case or FIR number, date of the request and the legal sections mentioned.
2. Limit the hold to the disputed amount of {_blank(d.get('amount'), 'amount')} only, and allow me to use the rest of my account.

In support of this request:
{basis}

I am ready to cooperate with the police and to provide any documents required.

Yours faithfully,
{_blank(d.get('name'), 'your full name')}
"""


def ai_letter(d, rules_df, provider, api_key, model):
    """Letter written by the AI, using only the rules table. Returns (letter, method, error)."""
    letter_rules = rules_for(rules_df, "frozen")
    letter_rules = letter_rules[letter_rules["use_in_letter"].str.lower() == "yes"]
    facts = {k: d.get(k, "") for k in ["name"] + DETAIL_FIELDS}
    prompt = f"""Write a formal letter from this person to their bank branch manager.
Ask the bank to (1) share the details of the freeze instruction (police station, case/FIR number,
date of request, legal sections), and (2) limit the hold to the disputed amount and release the rest.
Say the money was received in the normal course of work and the person had no part in any fraud.

Person's details (use exactly; write [brackets] for anything empty):
{json.dumps(facts, ensure_ascii=False, indent=2)}

The ONLY rules you may rely on:
{rules_as_text(letter_rules)}

The person's name is: {d.get('name') or '[your full name]'}. Use this exact name in the "From" part
and in the signature.
Keep it under 300 words, in simple formal English. Today's date is {date.today().strftime('%d %B %Y')}.
Return only the letter."""
    answer, error = ask_ai(provider, api_key, model, prompt)
    if answer:
        return _fill_name(answer.strip(), d.get("name")), "AI", None
    return template_letter(d, rules_df), "fixed template (AI off)", error


def template_followup(case):
    return f"""To,
The Branch Manager,
{_blank(case.get('bank'), 'bank name')}, {_blank(case.get('branch'), 'branch')} branch

Date: {date.today().strftime('%d %B %Y')}

Subject: Reminder about my request dated {case.get('created')} regarding the debit freeze on account ending {_blank(case.get('last4'), 'last 4 digits')}

Dear Sir/Madam,

On {case.get('created')}, I wrote to request the details of the freeze instruction on my account and that the hold be limited to the disputed amount of {_blank(case.get('amount'), 'amount')}. I have not yet received a reply.

I request an update within 7 days. If I do not hear back, I will use the official grievance redressal mechanism and seek free legal aid.

Yours faithfully,
{_blank(case.get('name'), 'your full name')}
"""


def ai_followup(case, provider, api_key, model):
    prompt = f"""Write a short, polite follow-up letter (under 150 words) to a bank branch manager.
The person wrote on {case.get('created')} asking for the details of a debit freeze on their account
ending {case.get('last4')} and asking that only the disputed amount ({case.get('amount')}) be held.
No reply has come. Ask for an update within 7 days and say they will otherwise use the official
grievance redressal mechanism and seek free legal aid.
The person's name is: {case.get('name') or '[your full name]'}. Sign the letter with this name.
Details: {json.dumps(case, ensure_ascii=False, default=str)}
Return only the letter."""
    answer, error = ask_ai(provider, api_key, model, prompt)
    if answer:
        return _fill_name(answer.strip(), case.get("name")), "AI", None
    return template_followup(case), "fixed template (AI off)", error


def explain_plan(rules_df, language, provider, api_key, model):
    prompt = f"""Explain these steps to a small shop owner whose bank account was frozen.
Write in {language}. Use short, simple sentences and a numbered list. Do not add any new legal
claims, laws or phone numbers beyond what is given. End with one line saying this is not legal advice.

Steps:
{rules_as_text(rules_df)}"""
    return ask_ai(provider, api_key, model, prompt)


# ---------------------------------------------------------------------------
# 5. Saving cases (a small SQLite database file)
# ---------------------------------------------------------------------------
def _connect():
    con = sqlite3.connect(DB_FILE)
    con.execute("""CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TEXT, name TEXT, bank TEXT, branch TEXT, last4 TEXT, amount TEXT,
        freeze_date TEXT, police TEXT, case_no TEXT, status TEXT, follow_up TEXT, letter TEXT)""")
    return con


def save_case(d, letter):
    """Save a case. Only the last 4 digits of the account are stored. The SMS is NOT stored."""
    today = date.today()
    with _connect() as con:
        cur = con.execute(
            """INSERT INTO cases (created, name, bank, branch, last4, amount, freeze_date, police,
               case_no, status, follow_up, letter) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (today.isoformat(), d.get("name", ""), d.get("bank", ""), d.get("branch", ""),
             only_last4(d.get("last4", "")), d.get("amount", ""), d.get("freeze_date", ""),
             d.get("police", ""), d.get("case_no", ""), "Letter ready to send",
             (today + timedelta(days=15)).isoformat(), letter))
        return cur.lastrowid


def load_cases():
    with _connect() as con:
        return pd.read_sql_query("SELECT * FROM cases ORDER BY id DESC", con)


def update_status(case_id, status):
    with _connect() as con:
        con.execute("UPDATE cases SET status = ? WHERE id = ?", (status, int(case_id)))


def delete_all_cases():
    with _connect() as con:
        con.execute("DELETE FROM cases")


# ---------------------------------------------------------------------------
# 6. New features: reading a screenshot, sharing, and the impact dashboard
# ---------------------------------------------------------------------------
def extract_from_screenshot(image_bytes, mime_type, provider, api_key, model):
    """Read a screenshot of a bank SMS with the AI.
    Returns (sms_text, details_dict, error). If it fails, sms_text is None."""
    prompt = """This image is a screenshot of a bank SMS or notice.
Return ONLY a JSON object with these keys:
sms_text (the message text, written out exactly), bank, branch, last4, amount, freeze_date, police, case_no.
- last4 = only the last 4 digits of the account number.
- Use "" for anything not in the image. Do not guess."""
    answer, error = ask_ai(provider, api_key, model, prompt, image=(image_bytes, mime_type))
    if not answer:
        return None, None, error
    match = re.search(r"\{.*\}", answer, re.S)
    if not match:
        return None, None, "The AI couldn't read that image. Try a clearer screenshot or paste the text."
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, None, "The AI's answer was not in the expected format."
    sms_text = str(data.get("sms_text", "") or "").strip()
    details = {field: str(data.get(field, "") or "").strip() for field in DETAIL_FIELDS}
    details["last4"] = only_last4(details["last4"])
    backup = extract_without_ai(sms_text)
    for field in DETAIL_FIELDS:
        if not details[field]:
            details[field] = backup[field]
    return sms_text, details, None


def whatsapp_link(text):
    """A link that opens WhatsApp with the text ready to send."""
    return "https://wa.me/?text=" + quote(text)


def email_link(subject, body):
    """A link that opens the email app with the subject and letter filled in."""
    return f"mailto:?subject={quote(subject)}&body={quote(body)}"


def parse_amount(value):
    """Turn text like 'Rs.2,500.00' or '₹150' into a number (2500.0 or 150.0)."""
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", str(value or ""))
    return float(match.group(1).replace(",", "")) if match else 0.0


RESOLVED_STATUSES = ["Freeze limited or removed"]


def case_stats(cases_df):
    """Numbers for the impact dashboard."""
    if cases_df.empty:
        return {"total": 0, "money": 0.0, "due": 0, "resolved": 0, "by_status": {}}
    today = date.today().isoformat()
    open_cases = cases_df[~cases_df["status"].isin(RESOLVED_STATUSES)]
    return {
        "total": len(cases_df),
        "money": float(cases_df["amount"].apply(parse_amount).sum()),
        "due": int((open_cases["follow_up"] <= today).sum()),
        "resolved": int(cases_df["status"].isin(RESOLVED_STATUSES).sum()),
        "by_status": cases_df["status"].value_counts().to_dict(),
    }

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
from urllib.parse import quote
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).parent
RULES_FILE = APP_DIR / "rules.csv"
DB_FILE = APP_DIR / "wapas_cases.db"


EXAMPLE_SMS = (
    "Dear Customer, your A/c XX4417 at ABC Bank, Gandhi Bazaar branch has been marked "
    "DEBIT FREEZE on 22-09-2026 as per instructions of Cyber Crime PS, Patna "
    "(Ack No. 123456789012345) regarding a disputed credit of Rs.150. "
    "Please contact your branch. - ABC Bank"
)

# The details we try to find in every SMS
DETAIL_FIELDS = ["bank", "branch", "last4", "amount", "freeze_date", "police", "case_no"]


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


# ---------------------------------------------------------------------------
# 4. Letters
# ---------------------------------------------------------------------------
def _blank(value, label):
    return value.strip() if value and value.strip() else f"[{label}]"


def template_letter(d, rules_df, for_sale=None, knows_payer=None):
    """Fixed letter. It still uses the rules table.
    The "received from a customer in the normal course of my work" claim is included only when for_sale is True.
    "I did not know the payer." is included only when knows_payer is False. A missing answer (None) leaves a claim out."""
    letter_rules = rules_for(rules_df, "frozen")
    letter_rules = letter_rules[letter_rules["use_in_letter"].str.lower() == "yes"]
    basis = "\n".join(f"- {r['rule']}" for _, r in letter_rules.iterrows())
    case_part = f" (reference {d['case_no']})" if d.get("case_no") else ""
    sale_part = " that I received from a customer in the normal course of my work" if for_sale is True else " credited to my account"
    payer_part = " I did not know the payer." if knows_payer is False else ""
    return f"""To,
The Branch Manager,
{_blank(d.get('bank'), 'bank name')}, {_blank(d.get('branch'), 'branch')} branch

Date: {date.today().strftime('%d %B %Y')}

Subject: Request to limit the debit freeze on my account ending {_blank(d.get('last4'), 'last 4 digits')} to the disputed amount

Dear Sir/Madam,

I, {_blank(d.get('name'), 'your full name')}, hold the account ending {_blank(d.get('last4'), 'last 4 digits')} at your branch. On {_blank(d.get('freeze_date'), 'date of freeze')}, a debit freeze was placed on my account on instructions from {_blank(d.get('police'), 'police station / cyber cell')}{case_part}.

I understand this is linked to a payment of {_blank(d.get('amount'), 'amount')}{sale_part}.{payer_part}

I request you to:
1. Share the details of the freeze instruction: the police station, case or FIR number, date of the request and the legal sections mentioned.
2. Limit the hold to the disputed amount of {_blank(d.get('amount'), 'amount')} only, and allow me to use the rest of my account.

In support of this request:
{basis}

I am ready to cooperate with the police and to provide any documents required.

Yours faithfully,
{_blank(d.get('name'), 'your full name')}
"""


def template_followup(case):
    return f"""To,
The Branch Manager,
{_blank(case.get('bank'), 'bank name')}, {_blank(case.get('branch'), 'branch')} branch

Date: {date.today().strftime('%d %B %Y')}

Subject: Reminder about my request dated {case.get('created')} regarding the debit freeze on account ending {_blank(case.get('last4'), 'last 4 digits')}

Dear Sir/Madam,

On {case.get('created')}, I wrote to request the details of the freeze instruction on my account and that the hold be limited to the disputed amount of {_blank(case.get('amount'), 'amount')}. I have not yet received a reply.

I request an update within 7 days. If I do not hear back, I will use the official grievance redressal mechanism and seek legal advice, including free legal aid if I qualify.

Yours faithfully,
{_blank(case.get('name'), 'your full name')}
"""


def template_grievance_letter(stage, case, reference="", registered="", decided=""):
    """Fixed letter for the next step of the grievance process in the MHA SOP dated 02.01.2026 (Clause 10).
    stage 1: the police officer did not act in time, so the grievance went to the District Grievance Officer.
    stage 2: the police officer rejected it, so the person asks the District Grievance Officer for a review.
    stage 3: the District Grievance Officer rejected the review, so the person appeals to the State Grievance Officer.
    It uses only the bank, last 4 digits, amount and freeze date from the case, and the three typed fields."""
    ref = _blank(reference, "grievance reference number")
    registered_on = _blank(registered, "date the bank registered the grievance")
    decided_on = _blank(decided, "date of the decision")
    officer = "The State Grievance Officer" if stage == 3 else "The District Grievance Officer"
    subject = {
        1: f"Request to decide my grievance, reference {ref}",
        2: f"Request to review the decision on my grievance, reference {ref}",
        3: f"Appeal against the decision on my review, reference {ref}",
    }[stage]
    what_happened = {
        1: "The police officer did not act on it in time, so it went to the District Grievance Officer.",
        2: f"The police officer rejected my grievance on {decided_on}.",
        3: f"The District Grievance Officer rejected my review on {decided_on}.",
    }[stage]
    request = {
        1: "I request you to decide my grievance as the MHA SOP dated 02.01.2026 (Clause 10) provides.",
        2: "I ask you to review the decision as the MHA SOP dated 02.01.2026 (Clause 10) provides.",
        3: "I appeal to you to review the decision as the MHA SOP dated 02.01.2026 (Clause 10) provides.",
    }[stage]
    return f"""To,
{officer}

Date: {date.today().strftime('%d %B %Y')}

Subject: {subject}

Dear Sir/Madam,

A debit freeze was placed on my account ending {_blank(case.get('last4'), 'last 4 digits')} at {_blank(case.get('bank'), 'bank name')} on {_blank(case.get('freeze_date'), 'date of freeze')}. The amount in dispute is {_blank(case.get('amount'), 'amount')}.

The bank registered my grievance on {registered_on}. The reference number is {ref}. {what_happened}

{request}

I am ready to cooperate and provide any documents required.

Yours faithfully,
[your full name]
"""


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


# ---------------------------------------------------------------------------
# 7. Case files: the visitor can download their cases and open them again later
# ---------------------------------------------------------------------------
CASE_STATUSES = ["Letter ready to send", "Sent to bank", "Bank replied",
                 "Freeze limited or removed", "Escalated to legal aid"]
CASE_FILE_FIELDS = ["bank", "branch", "last4", "amount", "freeze_date", "police", "case_no", "name",
                    "status", "created", "letter"]
MAX_CASE_FILE_BYTES = 100 * 1024
MAX_CASES_IN_FILE = 20
MAX_SHORT_TEXT = 60
MAX_LETTER_TEXT = 5000


def cases_to_json(cases):
    """The cases as JSON text, in memory only. Only the fields in CASE_FILE_FIELDS are written."""
    return json.dumps({"version": 1, "cases": [{key: str(case.get(key, "")) for key in CASE_FILE_FIELDS}
                                                for case in cases]}, ensure_ascii=False, indent=2)


def _has_control_characters(text, allow_line_breaks):
    allowed = "\n\r\t" if allow_line_breaks else ""
    return any((ord(ch) < 32 and ch not in allowed) or ord(ch) == 127 for ch in text)


def read_cases_file(raw):
    """Check an uploaded case file strictly. Returns a list of clean cases, or None if anything is wrong.
    The file is only parsed as JSON text: nothing in it is run, evaluated or turned into HTML.
    Rules: at most 100 KB; valid UTF-8 JSON; an object with version 1 and a list "cases" of 1 to 20 objects;
    only the keys in CASE_FILE_FIELDS are kept (every other key is dropped); status and created are required;
    every value is a string no longer than 60 characters (5000 for the letter) with no control characters
    (the letter may have line breaks); last4 is at most 4 digits; status is one of CASE_STATUSES;
    created is a real date written YYYY-MM-DD."""
    try:
        if raw is None or len(raw) > MAX_CASE_FILE_BYTES:
            return None
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
            return None
        items = data.get("cases")
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_CASES_IN_FILE:
            return None
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                return None
            case = {}
            for key in CASE_FILE_FIELDS:
                if key not in item:
                    if key in ("status", "created"):
                        return None
                    case[key] = ""
                    continue
                value = item[key]
                if not isinstance(value, str):
                    return None
                if len(value) > (MAX_LETTER_TEXT if key == "letter" else MAX_SHORT_TEXT):
                    return None
                if _has_control_characters(value, allow_line_breaks=(key == "letter")):
                    return None
                case[key] = value
            if case["status"] not in CASE_STATUSES:
                return None
            if not re.fullmatch(r"[0-9]{0,4}", case["last4"]):
                return None
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", case["created"]):
                return None
            case["follow_up"] = (date.fromisoformat(case["created"]) + timedelta(days=15)).isoformat()
            cleaned.append(case)
        return cleaned
    except (ValueError, UnicodeDecodeError, RecursionError, OverflowError, TypeError):
        return None

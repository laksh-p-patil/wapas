# Wapas

**Helping people get their frozen money back.**

Wapas ("back" in Hindi) is a prototype assistant for people in India whose bank accounts were frozen during cyber-fraud investigations, often because they received a small, genuine payment that turned out to be linked to someone else's scam. It reads the bank's SMS, explains what to do in plain language, and drafts a ready-to-send grievance letter based on real court orders and government procedures.

> Built by a team of first-year students for an open-innovation hackathon (September 2026).

---

## The problem

When a cyber fraud is reported, police trace the stolen money and ask banks to freeze accounts along the trail. Many of those account holders are innocent: shopkeepers, freelancers and students who received money for real goods or services. Their entire account can stay frozen for months.

- A nursery owner in Faridabad had an account holding over ₹1 lakh frozen for months over a ₹150 UPI payment ([The420.in](https://the420.in/cyber-fraud-crackdown-account-freeze-mule-network-cost/)).
- Several High Courts have said only the disputed amount should be held, not the whole account ([MediaNama](https://www.medianama.com/2026/07/223-merchants-bank-accounts-frozen-upi-payments-fraudsters-andhra-hc/)).
- In August 2026, the Supreme Court asked for public awareness of the official grievance and money-restoration mechanisms ([Bar and Bench](https://www.barandbench.com/news/supreme-court-issues-directions-to-curb-digital-arrest-scams-asks-rbi-to-frame-sop-on-mule-accounts)).

The government has built an official grievance system, but the first step, writing a proper grievance to the bank with the right details, is hard for most people. **The official system is the destination. Wapas is the guide that gets people there.**

---

## Features

- **Reads the bank SMS:** paste the message and the AI extracts the bank, account (last 4 digits only), amount, date, police station and reference number.
- **Reads screenshots:** upload a screenshot of the SMS instead of typing it.
- **Three simple questions:** works out the person's situation. Anyone who lent their account to someone else is sent to free legal aid instead of being given an "I'm innocent" letter.
- **Action plan:** clear next steps, each with its source and a "last checked" date.
- **Personalised letter:** a formal grievance letter to the bank, grounded only in the verified rules. Download it, share it on WhatsApp, or open it in an email app.
- **Case tracker and dashboard:** saves cases, shows follow-up reminders (with a "Simulate day 15" demo) and tracks cases, money in dispute and cases resolved.
- **Editable rules table:** when a law or court order changes, update one row. No code changes needed.
- **Explanations in English or Kannada.**
- **Works without AI:** if the AI is unavailable, the app falls back to pattern matching and fixed letter templates, so users are never stuck.

---

## How it works

```
User (browser)
   │  pastes SMS / uploads screenshot, answers questions
   ▼
app.py  ── frontend (Streamlit screens)
   │
   ▼
wapas_logic.py  ── backend
   ├── rules.csv        verified rules (facts come only from here)
   ├── Gemini API       reads the SMS, writes letters (words only)
   ├── templates        backup when the AI is unavailable
   └── wapas_cases.db   saved cases (SQLite)
```

**Design principle:** facts come from the rules table; words come from the AI. The AI is instructed never to invent laws, court cases or phone numbers.

---

## Tech stack

| Part | Technology |
|---|---|
| Frontend | Python, Streamlit |
| Backend | Python |
| AI | Google Gemini API (OpenAI and Anthropic also supported) |
| Database | SQLite |
| Data | CSV rules table with sources |

---

## Run it yourself

**1. Install Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).

**2. Download this repository** (green **Code** button → **Download ZIP**, or clone it) and open a terminal in the project folder.

**3. Create a virtual environment and install the requirements.**

Mac / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

**4. Add your API key.** Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey), then create a file at `.streamlit/secrets.toml` containing:
```toml
PROVIDER = "gemini"
API_KEY = "paste-your-key-here"
MODEL = "gemini-3.5-flash-lite"
```
This file is listed in `.gitignore`, so your key is never uploaded. Model names change over time; if you get a "model not found" error, use a current model name from Google AI Studio.

**5. Start the app.**
```bash
python3 -m streamlit run app.py
```
It opens in your browser at `http://localhost:8501`. Click **Use example SMS** to try it.

No API key? The app still runs using its fixed templates.

---

## Data and safety

- **Real:** the rules come from published court orders and government procedures, each with a source.
- **Sample:** the example SMS and the demo person ("Ravi") are made up. No real victims' data was used.
- **Privacy:** only the last 4 digits of an account number are stored, the SMS itself is not saved, and personal details are masked.
- **Safety:** Wapas never asks for money, OTPs, PINs or passwords, and says so on every screen.

> **This is a student prototype, not legal advice.** Rules and procedures change often; always check the latest official guidance or contact free legal aid.

---

## What's next

- Voice input in Kannada and other Indian languages
- More states and bank-specific procedures
- A pilot with a legal aid cell, using real cases with consent
- Outcome data: "what worked for people in your situation"

---


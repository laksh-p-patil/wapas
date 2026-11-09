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

- **Reads the bank SMS:** paste the message and the app finds the bank, branch, account (last 4 digits only), amount, date, police station and reference number using pattern matching. It can miss details in unusual messages, so the person checks and corrects each field before going on.
- **Three simple questions:** works out the person's situation. Anyone who lent their account to someone else is not given an "I'm innocent" letter. They are told to get legal advice and to ask NALSA (15100) whether they qualify for free legal aid.
- **Action plan:** a short "Do this now" list, with a button to show the full plan. Each step has its source and a "last checked" date.
- **Letter:** a formal grievance letter to the bank, written from a fixed template using the details the person entered and the verified rules. If the person says they know the payer, the letter leaves out the sentence saying they did not know the payer. Download it, share it on WhatsApp, or open it in an email app.
- **Case tracker and dashboard:** keeps saved cases while the browser tab is open, shows follow-up reminders (with a "Simulate day 15" demo that writes the follow-up letter from a fixed template) and shows cases tracked, money in dispute and cases resolved.
- **Editable rules table:** in owner mode, when a law or court order changes, update one row. No code changes needed.
- **No AI and no API key:** the app does not call any AI service, and it needs no API key. Nothing the user types or uploads is sent to one.

---

## How it works

```
User (browser)
   │  pastes the SMS, answers three questions
   ▼
app.py  ── frontend (Streamlit screens)
   │
   ▼
wapas_logic.py  ── backend
   ├── rules.csv        verified rules (facts come only from here)
   └── templates        fixed letter and follow-up text, filled in from the details
```

**Design principle:** facts come from the rules table, and the letters come from fixed templates. The pasted SMS is read with pattern matching in Python. Saved cases are kept in the browser session, not in a database file.

---

## Tech stack

| Part | Technology |
|---|---|
| Frontend | Python, Streamlit |
| Backend | Python (pattern matching and fixed templates) |
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

**4. Start the app.**
```bash
python3 -m streamlit run app.py
```
It opens in your browser at `http://localhost:8501`. Click **Use example SMS** to try it.

No API key or account is needed.

---

## Data and safety

- **Real:** the rules come from published court orders and government procedures, each with a source.
- **Sample:** the example SMS and the demo person ("Ravi") are made up. No real victims' data was used.
- **Privacy:** cases are kept only while the browser tab is open. If you refresh or close the tab, they are gone, so download the letter to keep it. A saved case keeps only the last 4 digits of the account number and does not include the SMS text. Nothing the user types or uploads is sent to an AI service. If the app is hosted online, what you paste is processed on the host's server.
- **Safety:** Wapas never asks for money, OTPs, PINs or passwords, and says so on every screen.

> **This is a student prototype, not legal advice.** Rules and procedures change often; always check the latest official guidance or contact free legal aid.

---

## What's next

- Voice input in Kannada and other Indian languages
- More states and bank-specific procedures
- A pilot with a legal aid cell, using real cases with consent
- Outcome data: "what worked for people in your situation"

---


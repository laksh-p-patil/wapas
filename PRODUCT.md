# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python + Streamlit (`app.py` for screens, `wapas_logic.py` for logic) for the public launch. A custom web front end over the same `wapas_logic.py` is a possible later step, not a current plan. Theme lives in `.streamlit/config.toml`, and custom CSS is injected in `app.py`.

Hosting: free on Streamlit Community Cloud at **wapas.streamlit.app**. Limits to design around:
- The app sleeps after about 12 hours without visitors, and the first visitor after that waits for it to wake up.
- No custom domain; the address stays `wapas.streamlit.app`.
- No API key is needed. The optional `ADMIN_MODE` setting for owner mode goes in Streamlit Cloud's Secrets settings, never in the repo.

## Users

- **Affected account holder (primary):** a person in India whose bank account was frozen during a cyber-fraud investigation, usually because they received a small, genuine payment linked to someone else's scam. Typical examples are shopkeepers, freelancers and students. They are stressed, short of money, and often unsure of their rights. They may have limited English or digital literacy, and real use will probably happen on a phone.
- **Helper (secondary, common path):** a legal aid volunteer, NGO worker or family member who fills in the case with the person or on their behalf.
- **Public-link visitors:** friends, club seniors and recruiters who open the public link on a phone or laptop. They decide within about 30 seconds whether it looks well made.

## Product Purpose

Wapas ("back" in Hindi) is a public website that helps innocent account holders take the first step toward getting frozen money released. That first step is a proper grievance letter to the bank with the right details. Wapas reads the bank's SMS, asks three screening questions, gives a plain-language action plan with sources, and drafts a ready-to-send letter. The official government grievance system is the destination, and Wapas is the guide that gets people there. Success means the person sends a correct, well-grounded grievance and follows up until the freeze is limited or removed.

## Positioning

- **Facts come from a verified rules table, and the letters come from fixed templates.** Every plan step and letter claim traces to a row in `rules.csv` with a source and a "last checked" date. The letters are fixed templates filled in from the person's details and the rules table, so nothing is generated on the fly.
- **Honest routing:** anyone who lent their account or UPI to someone else is told to get legal advice and to ask NALSA (15100) whether they qualify for free legal aid. They are not given an "I'm innocent" letter.
- **No AI and no API key:** the pasted bank message is read with pattern matching, and the letter and the day-15 follow-up come from fixed templates. Nothing the user types or uploads is sent to an AI service.

## Operating Context

- **Flow:** paste the bank SMS → check the extracted details (bank, branch, last 4 digits, amount, freeze date, police station, case number) → answer three yes/no questions → see the plan → get the letter → download it, share it on WhatsApp or email it → save the case.
- **Case tracker:** each saved case has a status ("Letter ready to send" → "Sent to bank" → "Bank replied" → "Freeze limited or removed" / "Escalated to legal aid") and a 15-day follow-up reminder. A "Simulate day 15" button shows the reminder without waiting.
- **Rules tab (admin):** updating a row of the editable rules table changes plans and letters without any code change.

## Capabilities and Constraints

- No AI is used. The pasted bank message is read with pattern matching, and the letter and the day-15 follow-up come from fixed templates, so the app works with no API key. Nothing the user types or uploads is sent to an AI service.
- The app is in English only for now. Explanations in Hindi and Kannada (with checked translations), voice input, more Indian languages and WhatsApp as the main channel are planned but not built.
- Privacy: cases are kept only while the browser tab is open, and are gone when it is refreshed or closed. A saved case keeps only the last 4 digits of the account and does not include the SMS text. The app runs on a server, so pasted text is processed there, but it is not passed to an AI service.
- Public-site privacy: one visitor must never see another visitor's saved cases.
- Public visitors must not be able to edit the rules table that every plan and letter is built from.
- The public site must not ask visitors for an API key. None is needed.
- Files written on Streamlit Community Cloud (rule edits) can be wiped when the app restarts or sleeps, so nothing may rely on them persisting.
- Terminology: "frozen account", "debit freeze", "grievance", "disputed amount", "Grievance Redressal Module", "legal aid".
- Undecided: whether real-user use happens through a pilot partner, which states and banks are covered beyond the generic procedure, and the long-term front end.

## Brand Commitments

- Name: **Wapas**. The tagline in the README is "Helping people get their frozen money back."
- Voice: plain, respectful, calm and direct. Use short sentences and avoid legal jargon unless it is explained.
- Every screen must say that Wapas never asks for money, OTPs, PINs or passwords.
- Every screen must say that this is a prototype and not legal advice.
- The site must say that it is a demo and that people should not enter real bank details.
- Character: modern, bold and memorable, while staying calm and trustworthy. The design can be striking, but the main user is stressed, so calm confidence beats decoration.

## Evidence on Hand

- `rules.csv`: seven rules drawn from court orders, the MHA SOP of 2 January 2026, the Supreme Court order of 4 August 2026, NALSA and the National Cybercrime Portal, each with a source and a last-verified date.
- The README cites real reporting (The420.in, MediaNama, Bar and Bench), including the case of a ₹150 UPI payment that froze more than ₹1 lakh.
- The example SMS and the demo person "Ravi" are made up. No real users, cases, outcomes, testimonials or partners exist yet. Do not fabricate success rates, recovered amounts or partner names.

## Product Principles

1. **Never invent facts.** Every legal claim traces to a sourced, dated rule.
2. **Honesty over a happy path.** Route people to legal aid when the innocence letter would be the wrong tool.
3. **Never leave someone stuck.** Every step needs a way forward that works without an API key and without prior knowledge. If the app can't read the SMS, the person can fill in the details by hand.
4. **Calm clarity for a stressed person.** Use one clear next step, plain words, and no blame or alarm beyond what the situation warrants.
5. **Protect the person.** Collect the minimum data, mask account numbers, and repeat the warnings about scams and OTPs.

## Accessibility & Inclusion

- Users may have limited English or digital literacy, so plain language and multiple Indian languages matter (English only now; Hindi and Kannada with checked translations are planned).
- Visitors arrive on phones and laptops, and the main user is most likely on a phone. Text must stay readable at both sizes.

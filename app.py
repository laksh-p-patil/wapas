"""
app.py  -  the screens of Wapas (the part people see).

HOW TO RUN (Windows): double-click START_WAPAS.bat
   or type in a terminal inside this folder:   python -m streamlit run app.py

This file only draws the screens. All the real work (rules, letters,
database) happens in wapas_logic.py.
"""

import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import wapas_logic as L

st.set_page_config(page_title="Wapas", page_icon="🔓", layout="centered",
                   initial_sidebar_state="collapsed")

# Styling: type sizes, tap sizes, phone layout, and the opening
st.markdown(
    """
    <style>
      /* Type. One family (Streamlit's own Source Sans); sizes and spacing tuned for phone and laptop */
      .stApp p, .stApp li, .stApp label { font-size: 1.05rem; text-wrap: pretty; }
      /* Lines of text stay a comfortable length on a wide screen */
      [data-testid="stMarkdownContainer"] p { max-width: 70ch; line-height: 1.55; }
      /* Captions carry sources and "check every detail", so they get a readable size */
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { font-size: 0.95rem; line-height: 1.5; }
      /* Step headings are a little smaller on a phone, so they wrap less */
      [data-testid="stMain"] h3 { font-size: clamp(1.35rem, 1.1rem + 1.2vw, 1.75rem); line-height: 1.25;
                                  text-wrap: balance; }
      /* The letter reads like a letter */
      [data-testid="stTextArea"] textarea { line-height: 1.5; }
      /* Numbers line up */
      [data-testid="stMetricValue"], [data-testid="stDataFrame"] { font-variant-numeric: tabular-nums; }

      /* Hide Streamlit's own Deploy button and toolbar actions. The menu stays, so visitors can pick a theme */
      [data-testid="stAppDeployButton"],
      [data-testid="stToolbarActions"] { display: none; }

      /* A deep green, so white button text and the active tab pass contrast (6.5:1) */
      [data-testid="stBaseButton-primary"], [data-testid="stBaseLinkButton-primary"] {
        background-color: #1B6B4A; border-color: #1B6B4A; }
      [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseLinkButton-primary"]:hover {
        background-color: #14543A; border-color: #14543A; }
      .stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p { font-weight: 700; }
      /* In dark mode the deep green is too dark on the page, so step lines and primary buttons
         use one lighter green (#3DB27C), with white text on the buttons.
         The step line rule has an extra .stApp so it beats the later, equal-specificity rule below. */
      @media (prefers-color-scheme: dark) {
        .stApp div.wapas-hero ol.wapas-steps li { border-top-color: #3DB27C; }
        [data-testid="stBaseButton-primary"], [data-testid="stBaseLinkButton-primary"] {
          background-color: #3DB27C; border-color: #3DB27C; }
        [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseLinkButton-primary"]:hover {
          background-color: #2F9A69; border-color: #2F9A69; }
        [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] *,
        [data-testid="stBaseLinkButton-primary"], [data-testid="stBaseLinkButton-primary"] * { color: #FFFFFF; }
      }

      /* Easy to tap: buttons, tabs, answer options and expanders are at least 44px tall */
      [data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
      [data-testid="stLinkButton"] a { min-height: 3rem; }
      .stTabs [data-testid="stTab"] { min-height: 3rem; }
      /* 16px inside fields, so iPhones don't zoom the page when you tap one */
      [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { font-size: 1rem; }
      /* The small link icons next to headings are not needed here */
      [data-testid="stHeaderActionElements"] { display: none; }
      [data-testid="stRadio"] label[data-baseweb="radio"] { min-height: 2.75rem; align-items: center; }
      [data-testid="stExpander"] summary { min-height: 3rem; }

      /* Long words (case numbers, links) wrap instead of pushing the page sideways */
      [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] { overflow-wrap: break-word; }

      /* Letter box: shorter on a phone so it fits the screen; it still scrolls inside */
      @media (max-width: 640px) {
        .st-key-letter_box, .st-key-letter_box [data-testid="stTextArea"],
        .st-key-letter_box [data-testid="stTextAreaRootElement"] { height: auto !important; }
        .st-key-letter_box textarea { height: min(55vh, 20rem) !important; }
      }

      /* Saved cases: a table on laptops, one small card per case on phones */
      .st-key-cases_cards { display: none !important; }
      @media (max-width: 640px) {
        .st-key-cases_table { display: none !important; }
        .st-key-cases_cards { display: flex !important; }
      }

      /* On a phone, Streamlit stacks columns; make each button fill the width so it is easy to hit */
      @media (max-width: 640px) {
        div:has(> [data-testid="stButton"]), div:has(> [data-testid="stDownloadButton"]),
        div:has(> [data-testid="stLinkButton"]), [data-testid="stButton"],
        [data-testid="stDownloadButton"], [data-testid="stLinkButton"] { width: 100%; }
        [data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a { width: 100%; }
      }

      /* The opening: name, meaning, promise, three steps */
      div.wapas-hero { margin: 0.5rem 0 1rem 0; }
      div.wapas-hero h1.wapas-name { font-size: 3.25rem; line-height: 1.05; font-weight: 800;
                                     letter-spacing: -0.02em; margin: 0; padding: 0; }
      div.wapas-hero .wapas-meaning { color: inherit; opacity: 0.7; margin: 0.35rem 0 0.9rem 0; }
      div.wapas-hero .wapas-promise { font-size: 1.25rem; line-height: 1.4; max-width: 36rem;
                                      margin: 0 0 1.25rem 0; text-wrap: balance; }
      div.wapas-hero ol.wapas-steps { display: grid; gap: 1rem; list-style: none; margin: 0; padding: 0;
                                      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); }
      div.wapas-hero ol.wapas-steps li { border-top: 3px solid #1B6B4A; padding: 0.5rem 0 0 0; margin: 0; }
      div.wapas-hero ol.wapas-steps b { display: block; font-size: 1.1rem; }
      div.wapas-hero ol.wapas-steps span { color: inherit; opacity: 0.7; font-size: 0.95rem; }

      .wapas-note { background:#E3F3EA; color:#12432E; padding:10px 14px; border-radius:8px;
                    font-size:1rem; line-height: 1.5; margin: 0.25rem 0 0.75rem 0; }
      .st-key-call_nalsa a { min-height: 3.5rem; font-size: 1.3rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


# Tints for the three send buttons. Light fills with dark text read well in light and dark mode.
st.markdown(
    """
    <style>
      .st-key-download_letter button, .st-key-share_whatsapp a, .st-key-send_email a,
      .st-key-reset_letter button { border-width: 1px; }
      .st-key-download_letter button, .st-key-download_letter button * { color: #0B3B38; }
      .st-key-download_letter button { background-color: #D3F0EE; border-color: #8CCFCA; }
      .st-key-download_letter button:hover { background-color: #BCE6E3; border-color: #5FB8B1; }

      .st-key-share_whatsapp a, .st-key-share_whatsapp a * { color: #123B1E; }
      .st-key-share_whatsapp a { background-color: #D9F2DF; border-color: #93CFA4; }
      .st-key-share_whatsapp a:hover { background-color: #C4EACD; border-color: #66B87F; }

      .st-key-send_email a, .st-key-send_email a * { color: #12335A; }
      .st-key-send_email a { background-color: #DCEBFA; border-color: #9BC2EA; }
      .st-key-send_email a:hover { background-color: #C8DFF5; border-color: #6AA3DC; }

      .st-key-reset_letter button, .st-key-reset_letter button * { color: #5C3B00; }
      .st-key-reset_letter button { background-color: #FFF1CC; border-color: #D9A93A; }
      .st-key-reset_letter button:hover { background-color: #FCE5A6; border-color: #B8861A; }

      /* The amber note in the reminder dialog: the same amber as Reset letter, with dark text in both modes */
      .wapas-amber { background-color: #FFF1CC; border: 1px solid #D9A93A; border-radius: 8px; padding: 10px 14px;
                     font-size: 1rem; line-height: 1.5; margin: 0 0 0.75rem 0; }
      .wapas-amber, .wapas-amber * { color: #5C3B00; }
    </style>
    """,
    unsafe_allow_html=True,
)


# Small CSS-only animations. They are switched off for visitors who ask for reduced motion.
# Only things that appear once (the step cards and the two boxes) fade in, so nothing flickers on a click.
st.markdown(
    """
    <style>
      @media (prefers-reduced-motion: no-preference) {
        @keyframes wapas-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        @keyframes wapas-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes wapas-slide { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: none; } }
        @keyframes wapas-pop { 0% { transform: scale(1); } 50% { transform: scale(1.04); } 100% { transform: scale(1); } }
        @keyframes wapas-type { from { clip-path: inset(-0.4em 100% -0.4em -0.1em); }
                                to { clip-path: inset(-0.4em -0.4em -0.4em -0.1em); } }
        @keyframes wapas-cursor-move { from { left: 0; } to { left: 100%; } }
        @keyframes wapas-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes wapas-cursor-hide { to { visibility: hidden; } }
        @keyframes wapas-draw { from { transform: scaleX(0); } to { transform: scaleX(1); } }
        @keyframes wapas-glow { 0%, 100% { box-shadow: 0 0 0 0 rgba(61, 178, 124, 0); }
                                50% { box-shadow: 0 0 14px 4px rgba(61, 178, 124, 0.55); } }
        @keyframes wapas-ring { 0%, 100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
                                50% { box-shadow: 0 0 12px 3px rgba(220, 53, 69, 0.45); } }

        /* The three step cards rise in one after another, 0.4s each */
        div.wapas-hero ol.wapas-steps li { animation: wapas-rise 0.4s ease-out both; }
        div.wapas-hero ol.wapas-steps li:nth-child(2) { animation-delay: 0.4s; }
        div.wapas-hero ol.wapas-steps li:nth-child(3) { animation-delay: 0.8s; }

        /* The line above each step card draws in left to right over 0.6s, staggered like the cards.
           The real border is turned off (its colour is kept) and a line of the same colour is drawn in its place. */
        div.wapas-hero ol.wapas-steps li { position: relative; border-top-style: none; padding-top: calc(0.5rem + 3px); }
        div.wapas-hero ol.wapas-steps li::before { content: ""; position: absolute; top: 0; left: 0; right: 0;
                                                   border-top: 3px solid; border-top-color: inherit;
                                                   transform-origin: left; animation: wapas-draw 0.6s ease-out both; }
        div.wapas-hero ol.wapas-steps li:nth-child(2)::before { animation-delay: 0.4s; }
        div.wapas-hero ol.wapas-steps li:nth-child(3)::before { animation-delay: 0.8s; }

        /* The line under "Wapas" is typed out once in 1.2s (27 characters, so 27 steps). The reveal is a
           clip that moves left to right, so the Hindi letters are never cut and a narrow screen still wraps.
           A thin cursor rides the front edge, blinks, and is hidden when the typing ends. */
        div.wapas-hero .wapas-meaning { position: relative; width: fit-content;
                                        animation: wapas-type 1.2s steps(27, end) both; }
        div.wapas-hero .wapas-meaning::after { content: ""; position: absolute; top: 0.2em; left: 0;
                                               width: 2px; height: 1.1em; margin-left: -2px; background: currentColor;
                                               animation: wapas-cursor-move 1.2s steps(27, end) both,
                                                          wapas-blink 0.6s steps(1) infinite,
                                                          wapas-cursor-hide 0s linear 1.2s forwards; }

        /* Buttons lift 2px with a soft shadow on hover */
        [data-testid="stButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {
          transition: transform 0.15s ease, box-shadow 0.15s ease,
                      background-color 0.15s ease, border-color 0.15s ease; }
        [data-testid="stButton"] button:not(:disabled):hover,
        [data-testid="stDownloadButton"] button:not(:disabled):hover,
        [data-testid="stLinkButton"] a:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.18); }

        /* Buttons shrink slightly while pressed */
        [data-testid="stButton"] button:not(:disabled):active,
        [data-testid="stDownloadButton"] button:not(:disabled):active,
        [data-testid="stLinkButton"] a:active { transform: scale(0.97); transition: transform 0.1s ease; }

        /* The "Do this now" box and the letter box fade in when they appear */
        .st-key-do_now, .st-key-letter_box { animation: wapas-fade 0.3s ease-out; }

        /* Switching tabs: the new tab's content fades in and the underline slides */
        [data-baseweb="tab-panel"] { animation: wapas-fade 0.25s ease-out; }
        .stTabs [data-baseweb="tab-highlight"] { transition: transform 0.25s ease, left 0.25s ease, width 0.25s ease; }

        /* Success, warning and info boxes slide in once when they appear (the "Do this now" box already fades) */
        [data-testid="stAlert"] { animation: wapas-slide 0.3s ease-out; }
        .st-key-do_now [data-testid="stAlert"] { animation: none; }

        /* "Read my message" glows softly 3 times, starting 1s after it appears, then stops */
        .st-key-read_message button { animation: wapas-glow 2.4s ease-in-out 1s 3; }

        /* The red "lent your account" box gets one soft border glow, with no movement (this replaces its slide) */
        [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) { animation: wapas-ring 2.5s ease-in-out 1; }

        /* Yes/No answers: the fill eases to the chosen option, which pops once; the others lift on hover */
        [data-testid="stRadioOption"] { transition: transform 0.15s ease; }
        [data-testid="stRadioOption"] * { transition: background-color 0.2s ease, border-color 0.2s ease; }
        [data-testid="stRadioOption"]:has(input:checked) { animation: wapas-pop 0.2s ease-out; }
        [data-testid="stRadioOption"]:not(:has(input:checked)):hover { transform: translateY(-2px); }

        /* The three questions fade in one after another when they first appear */
        .st-key-q1, .st-key-q2, .st-key-q3 { animation: wapas-fade 0.3s ease-out both; }
        .st-key-q2 { animation-delay: 0.15s; }
        .st-key-q3 { animation-delay: 0.3s; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def secret(name, default=""):
    """Read a value from .streamlit/secrets.toml. Returns default if it isn't there."""
    try:
        value = st.secrets.get(name, default)
        return value if value else default
    except Exception:
        return default


# Owner mode: add ADMIN_MODE = true to your local .streamlit/secrets.toml to edit
# the rules. Leave it out on the public site.
admin = str(secret("ADMIN_MODE")).strip().lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="wapas-hero">
      <h1 class="wapas-name">Wapas</h1>
      <p class="wapas-meaning">वापस means &ldquo;back&rdquo; in Hindi.</p>
      <p class="wapas-promise">If your bank account was frozen because of someone else&rsquo;s scam,
        Wapas gives you a clear plan and a letter to ask your bank to release it.</p>
      <ol class="wapas-steps">
        <li><b>Paste your bank SMS</b><span>Wapas reads the details for you.</span></li>
        <li><b>Answer three questions</b><span>Yes or no, nothing more.</span></li>
        <li><b>Get your letter</b><span>Plus a plan, with sources.</span></li>
      </ol>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="wapas-note">Wapas never asks for money, OTPs, PINs or passwords. '
    "This is a demo, so don't enter real bank details. It is not legal advice.</div>",
    unsafe_allow_html=True,
)

rules_df = L.load_rules()

# Remember things between clicks (Streamlit re-runs this file on every click)
defaults = {"details_ready": False, "show_result": False, "letter_ready": False,
            "extract_method": "", "extract_error": None, "letter_method": "",
            "rules_version": 0, "flash": None, "followups": {},
            "my_cases": [], "case_count": 0, "confirm_rewrite": False, "letter_original": ""}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
for field in ["name"] + L.DETAIL_FIELDS:
    st.session_state.setdefault("f_" + field, "")


def use_example():
    st.session_state.sms_input = L.EXAMPLE_SMS


def start_new_case():
    st.session_state.sms_input = ""
    for field in ["name"] + L.DETAIL_FIELDS:
        st.session_state["f_" + field] = ""
    for q in ["q1", "q2", "q3"]:
        st.session_state.pop(q, None)  # clears the answers
    st.session_state.details_ready = False
    st.session_state.show_result = False
    st.session_state.letter_ready = False
    st.session_state.confirm_rewrite = False


def toast_download():
    st.toast("Download started", icon=":material/check_circle:")


def reminder_ics():
    """A tiny calendar file with one all-day event 15 days from today. It holds nothing from the case."""
    today = date.today()
    due = today + timedelta(days=15)
    title = "Check your bank's reply about your frozen account"
    note = "Open Wapas, check whether the bank replied, and use the follow-up letter if it has not."
    escape = lambda text: text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Wapas//Reminder//EN", "BEGIN:VEVENT",
             f"UID:wapas-day15-{due:%Y%m%d}@wapas", f"DTSTAMP:{today:%Y%m%d}T000000Z",
             f"DTSTART;VALUE=DATE:{due:%Y%m%d}", f"DTEND;VALUE=DATE:{due + timedelta(days=1):%Y%m%d}",
             f"SUMMARY:{escape(title)}", f"DESCRIPTION:{escape(note)}", "END:VEVENT", "END:VCALENDAR"]
    # Calendar files use CRLF line ends and fold long lines after 75 characters
    folded = ["\r\n ".join(line[i:i + 74] for i in range(0, len(line), 74)) for line in lines]
    return "\r\n".join(folded) + "\r\n"


@st.dialog("Add a reminder to your calendar")
def reminder_dialog():
    st.markdown(
        '<div class="wapas-amber">This adds one event to your calendar for day 15. On that day, check whether '
        "your bank replied. If it has not, open Wapas and use the follow-up letter. The file has none of your "
        "details. Day 15 is a check-in date set by Wapas, not a legal deadline. Cases like this can take time, "
        "so keep copies of everything and write down dates. Wapas does not keep your case, so download your "
        "letter too.</div>",
        unsafe_allow_html=True,
    )
    # "ignore" means no rerun and no callback, so the dialog stays open
    st.download_button("Download reminder file", icon=":material/event:", key="download_reminder",
                       data=reminder_ics(), file_name="wapas-day-15-reminder.ics",
                       mime="text/calendar", on_click="ignore")
    st.caption("Your file downloads when you click.")


# Cases are kept only in this visitor's browser tab, never in a shared file,
# so one visitor can never see another visitor's cases.
def save_my_case(d, letter):
    """Save a case for this visitor only. Only the last 4 digits of the account are kept."""
    today = date.today()
    st.session_state.case_count += 1
    case = {"id": st.session_state.case_count, "created": today.isoformat()}
    case.update({k: d.get(k, "") for k in ["name"] + L.DETAIL_FIELDS})
    case["last4"] = L.only_last4(case["last4"])
    case.update({"status": "Letter ready to send",
                 "follow_up": (today + timedelta(days=15)).isoformat(), "letter": letter})
    st.session_state.my_cases.insert(0, case)  # newest first
    return case["id"]


def plain(value):
    """Show a saved value as plain text inside markdown (so typed symbols can't change the layout)."""
    text = str(value).strip()
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$&])", r"\\\1", text) if text else "—"


def update_my_case_status(case_id, status):
    for case in st.session_state.my_cases:
        if case["id"] == case_id:
            case["status"] = status


tab_new, tab_cases, tab_rules = st.tabs(["New case", "My cases", "Rules"])

# ---------------------------------------------------------------------------
# Tab 1: New case
# ---------------------------------------------------------------------------
with tab_new:
    st.subheader("1. Paste the message from your bank")
    st.text_area("Bank SMS or notice", key="sms_input", height=130,
                 placeholder="Paste the SMS your bank sent you")
    st.caption("Demo tip: use the example SMS, or remove your full account number first. "
               "Wapas only needs the last 4 digits.")
    col1, col2 = st.columns(2)
    col1.button("Use example SMS", on_click=use_example)
    read_clicked = col2.button("Read my message", type="primary", key="read_message")

    if read_clicked:
        sms = st.session_state.get("sms_input", "").strip()
        if not sms:
            st.warning("Paste a message first, or click Use example SMS.")
        else:
            with st.spinner("Reading your message..."):
                details = L.extract_without_ai(sms)
            for field in L.DETAIL_FIELDS:
                st.session_state["f_" + field] = details[field]
            st.session_state.extract_method = "pattern matching on this device"
            st.session_state.extract_error = None
            st.session_state.details_ready = True

    if st.session_state.details_ready:
        st.subheader("2. Check your details")
        st.caption("Correct any of the details that you may feel is incorrect.")

        with st.expander("What do these words mean?"):
            st.markdown("- **FIR** (First Information Report): the police's written record of a complaint. "
                        "Your bank's message may show its number, or another reference number.\n"
                        "- **Debit freeze**: the bank stops money from going out of your account.")

        # Each column is filled top to bottom, so on a phone (one column) the order reads
        # name, bank, branch, last 4, amount, date, police, case number.
        c1, c2 = st.columns(2)
        c1.text_input("Your full name", key="f_name")
        c1.text_input("Bank", key="f_bank")
        c1.text_input("Branch", key="f_branch")
        c1.text_input("Account: last 4 digits only", key="f_last4", max_chars=4)
        c2.text_input("Amount in dispute", key="f_amount")
        c2.text_input("Date of freeze", key="f_freeze_date")
        c2.text_input("Police station or cyber cell", key="f_police")
        c2.text_input("Case, FIR or reference number", key="f_case_no")

        st.subheader("3. Answer three questions")
        q1 = st.radio("Did you receive this money for something you sold or a service you gave?",
                      ["Yes", "No"], index=None, horizontal=True, key="q1")
        q2 = st.radio("Do you personally know the person who paid you?",
                      ["Yes", "No"], index=None, horizontal=True, key="q2")
        q3 = st.radio("Did you ever let someone else use your bank account or UPI?",
                      ["Yes", "No"], index=None, horizontal=True, key="q3")

        if None not in (q1, q2, q3):
            details = {f: st.session_state["f_" + f] for f in ["name"] + L.DETAIL_FIELDS}
            details["last4"] = L.only_last4(details["last4"])

            if q3 == "Yes":
                # Honest route: no innocence letter for people who lent their account
                st.error("Because you let someone else use your account, this is serious. "
                         "Please don't send a letter saying you're innocent. Get legal advice first. "
                         "You may qualify for free legal aid.")
                st.link_button("Ask NALSA (15100) if you qualify for free legal aid", "tel:15100",
                               type="primary", width="stretch", key="call_nalsa")
                for _, r in L.rules_for(rules_df, "lent").iterrows():
                    st.markdown(f"- {r['rule']}")
                    st.caption(f"Source: {r['source']}. Last checked: {r['last_verified']}.")
            else:
                if q1 == "No":
                    st.info("Wapas works best when the money was received for a genuine sale or service. "
                            "If that's not your situation, get legal advice before sending anything. "
                            "Ask NALSA (15100) if you qualify for free legal aid.")

                st.subheader("4. Your plan")
                plan_rules = L.rules_for(rules_df, "frozen")
                with st.container(key="do_now"):  # the key lets the CSS fade this box in
                    st.info("**Do this now**\n\n"
                            "1. Ask your bank for the freeze details: police station, case or FIR number, date, legal sections.\n"
                            "2. Ask that only the disputed amount is held, not the whole account.\n"
                            "3. Use the official grievance redressal mechanism first.")
                plan_open = st.session_state.get("plan_details_open", False)
                if st.button("Hide full details" if plan_open else "Show full details"):
                    st.session_state.plan_details_open = not plan_open
                    st.rerun()
                if st.session_state.get("plan_details_open"):
                    for number, (_, r) in enumerate(plan_rules.iterrows(), start=1):
                        st.markdown(f"**{number}.** {r['rule']}")
                        st.caption(f"Source: {r['source']}. Last checked: {r['last_verified']}.")

                st.subheader("5. Your letter")
                inputs = (tuple(details.values()), q2 == "Yes")  # what the letter is built from
                if st.session_state.letter_ready and "letter_box" not in st.session_state:
                    # the box was not on screen for a run (for example question 3 was Yes), so Streamlit
                    # dropped its text; put back the last text the visitor had
                    st.session_state.letter_box = st.session_state.get("letter_saved", "")
                if st.session_state.letter_ready and inputs != st.session_state.get("letter_inputs"):
                    if st.session_state.letter_box == st.session_state.letter_original:
                        st.session_state.letter_ready = False  # not edited, so write it again
                    else:
                        st.session_state.confirm_rewrite = True  # edited, so keep it and offer Reset
                        st.session_state.letter_inputs = inputs
                if not st.session_state.letter_ready:
                    with st.spinner("Writing your letter..."):
                        letter, method = (L.template_letter(details, rules_df, knows_payer=(q2 == "Yes")),
                                          "Letter written from a standard template. Not sent to any AI.")
                    st.session_state.letter_box = letter
                    st.session_state.letter_original = letter  # to tell later if the user edited it
                    st.session_state.letter_method = method
                    st.session_state.letter_inputs = inputs
                    st.session_state.letter_ready = True

                st.caption("Letter written from a standard template. Not sent to any AI. Check every detail before sending.")
                st.text_area("You can edit the letter here", key="letter_box", height=460)
                st.session_state.letter_saved = st.session_state.letter_box

                # Group 1: send the letter
                st.caption("Send your letter")
                subject = f"Request to limit the debit freeze on account ending {details['last4']}"
                b1, b2, b3 = st.columns(3)
                b1.download_button("Download letter", icon=":material/download:", key="download_letter",
                                   data=st.session_state.letter_box,
                                   file_name=f"wapas_letter_{details['last4'] or 'case'}.txt",
                                   on_click=toast_download)
                b2.link_button("Share on WhatsApp", L.whatsapp_link(st.session_state.letter_box),
                               icon=":material/chat:", key="share_whatsapp")
                b3.link_button("Send by email", L.email_link(subject, st.session_state.letter_box),
                               icon=":material/mail:", key="send_email")
                st.caption("Share it with a family member or lawyer to check, or open your email app "
                           "with the letter ready to send to the bank.")

                st.space("small")

                # Group 2: change the letter or keep the case
                st.caption("Change or keep your case")
                k1, k2, _ = st.columns(3)  # the two buttons line up under the first two above
                if k1.button("Reset letter", icon=":material/edit:", key="reset_letter"):
                    if st.session_state.letter_box != st.session_state.letter_original:
                        st.session_state.confirm_rewrite = True  # they edited it, so ask first
                    else:
                        st.session_state.letter_ready = False
                        st.rerun()
                if k2.button("Save this case", icon=":material/save:", type="primary"):
                    case_id = save_my_case(details, st.session_state.letter_box)
                    st.success(f"Saved as case #{case_id}. Open My cases to track it.")
                    st.toast("Case saved", icon=":material/check_circle:")
                st.caption("Your case is kept only while this tab is open. Refresh or close it and it's gone. "
                           "Download your letter to keep it.")

                if st.session_state.confirm_rewrite:
                    st.warning("You edited this letter. Resetting replaces your edits with a new letter.")
                    r1, r2 = st.columns(2)
                    if r1.button("Reset and replace my edits"):
                        st.session_state.confirm_rewrite = False
                        st.session_state.letter_ready = False
                        st.rerun()
                    if r2.button("Keep my edits"):
                        st.session_state.confirm_rewrite = False
                        st.rerun()

                if st.button("Add day-15 reminder", icon=":material/event:", key="open_reminder"):
                    reminder_dialog()
                st.caption("Adds a calendar event on day 15 to check if your bank replied. "
                           "The file has none of your details.")

                st.info("**What to do next**\n\n"
                        "1. Fill in anything still in [square brackets] and check every detail.\n"
                        "2. Send the letter to your bank branch manager. Keep a copy.\n"
                        "3. Note the date you sent it, and set the case status to \"Sent to bank\" in My cases.\n"
                        "4. If the bank has not replied in 15 days, send the follow-up letter from My cases.\n\n"
                        "This can take time. Keep copies of every letter and reply, and write down dates. "
                        "Wapas cannot speed up your bank.")

        st.button("Start a new case", on_click=start_new_case)

# ---------------------------------------------------------------------------
# Tab 2: My cases (kept only in this visitor's browser tab)
# ---------------------------------------------------------------------------
with tab_cases:
    st.subheader("Case tracker")
    st.caption("Your cases are saved in this browser tab only. Refreshing or closing the page "
               "clears them, so download your letter to keep it.")
    cases = pd.DataFrame(st.session_state.my_cases)
    if cases.empty:
        st.info("No saved cases yet. Save one from the New case tab.")
    else:
        stats = L.case_stats(cases)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cases tracked", stats["total"])
        m2.metric("Money in dispute", f"₹{stats['money']:,.0f}")
        m3.metric("Follow-ups due", stats["due"])
        m4.metric("Resolved", stats["resolved"])
        st.caption("Cases by status")
        st.bar_chart(pd.Series(stats["by_status"], name="Cases"))

        with st.container(key="cases_table"):  # shown on laptops
            st.dataframe(cases[["id", "created", "name", "bank", "last4", "status", "follow_up"]],
                         hide_index=True)
        with st.container(key="cases_cards"):  # shown on phones, no sideways scrolling
            for _, c in cases.iterrows():
                with st.container(border=True):
                    st.markdown(f"**Case #{c['id']}** · {plain(c['name'])}")
                    st.markdown(f"{plain(c['bank'])}, account ending {plain(c['last4'])}")
                    st.markdown(f"Status: **{plain(c['status'])}**")
                    st.caption(f"Next follow-up: {c['follow_up']} · Saved: {c['created']}")
        chosen = st.selectbox("Open a case", cases["id"].tolist(), format_func=lambda i: f"Case #{i}")
        case = cases[cases["id"] == chosen].iloc[0].to_dict()

        statuses = ["Letter ready to send", "Sent to bank", "Bank replied",
                    "Freeze limited or removed", "Escalated to legal aid"]
        current = statuses.index(case["status"]) if case["status"] in statuses else 0
        new_status = st.selectbox("Status", statuses, index=current, key=f"status_{chosen}")
        if st.button("Update status"):
            update_my_case_status(chosen, new_status)
            st.rerun()

        st.write(f"Next follow-up: **{case['follow_up']}**")
        if st.button("Simulate day 15"):
            with st.spinner("Writing a follow-up letter..."):
                text, method, error = (L.template_followup(case),
                                       "Letter written from a standard template. Not sent to any AI.", None)
            st.session_state.followups[chosen] = (text, method)

        if chosen in st.session_state.followups:
            text, method = st.session_state.followups[chosen]
            st.warning(f"Day 15 reminder: no reply yet on case #{chosen}? Send this follow-up today.")
            st.caption("Letter written from a standard template. Not sent to any AI. Check every detail before sending.")
            st.text_area("Follow-up letter", value=text, height=300, key=f"followup_box_{chosen}")
            st.download_button("Download follow-up", data=text, file_name=f"wapas_followup_{chosen}.txt")

        with st.expander("See the first letter saved with this case"):
            st.text(case["letter"])

        with st.expander("Delete my saved cases"):
            confirm = st.checkbox("Yes, delete all the cases I saved in this tab")
            if st.button("Delete my saved cases", disabled=not confirm):
                st.session_state.my_cases = []
                st.session_state.followups = {}
                st.rerun()

# ---------------------------------------------------------------------------
# Tab 3: Rules (read-only for visitors, editable in owner mode)
# ---------------------------------------------------------------------------
with tab_rules:
    st.subheader("Rules Wapas uses")
    if not admin:
        # Visitors can read the rules but never change them
        st.write("Every plan and letter is built from this table. Each rule lists its source "
                 "and the date it was last checked.")
        st.dataframe(
            rules_df,
            hide_index=True,
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "rule": st.column_config.TextColumn("Rule", width="large"),
                "source": st.column_config.TextColumn("Source", width="medium"),
                "applies_to": st.column_config.TextColumn("Applies to"),
                "use_in_letter": st.column_config.TextColumn("Use in letter"),
                "last_verified": st.column_config.TextColumn("Last checked"),
            },
        )
    else:
        st.write("Every plan and letter is built from this table. When a law or court order changes, "
                 "update the row here. No code changes needed.")
        if st.session_state.flash:
            st.success(st.session_state.flash)
            st.session_state.flash = None

        edited = st.data_editor(
            rules_df,
            num_rows="dynamic",
            hide_index=True,
            key=f"rules_editor_{st.session_state.rules_version}",
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "rule": st.column_config.TextColumn("Rule", width="large"),
                "source": st.column_config.TextColumn("Source", width="medium"),
                "applies_to": st.column_config.SelectboxColumn(
                    "Applies to", options=["frozen", "scammed", "lent", "all"]),
                "use_in_letter": st.column_config.SelectboxColumn("Use in letter", options=["yes", "no"]),
                "last_verified": st.column_config.TextColumn("Last checked"),
            },
        )
        if st.button("Save rules", type="primary"):
            edited = edited.copy()
            edited["last_verified"] = edited["last_verified"].replace("", date.today().isoformat())
            L.save_rules(edited)
            st.session_state.rules_version += 1   # gives the table a fresh start
            st.session_state.letter_ready = False  # next letter uses the new rules
            st.session_state.flash = "Rules saved. New plans and letters will use them."
            st.rerun()

# ---------------------------------------------------------------------------
# Footer: shown under every tab. The date is the oldest "last checked" date in the rules table.
# ---------------------------------------------------------------------------
try:
    oldest = pd.to_datetime(rules_df["last_verified"], errors="coerce").min()
    footer = (f"Rules last checked on {oldest.day} {oldest:%B %Y}. Not legal advice."
              if pd.notna(oldest) else "Rules last checked: date unavailable")
except Exception:
    footer = "Rules last checked: date unavailable"
st.caption(footer)

"""
app.py  -  the screens of Wapas (the part people see).

HOW TO RUN (Windows): double-click START_WAPAS.bat
   or type in a terminal inside this folder:   python -m streamlit run app.py

This file only draws the screens. All the real work (AI, rules, letters,
database) happens in wapas_logic.py.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import wapas_logic as L

st.set_page_config(page_title="Wapas", page_icon="🔓", layout="centered")

# A little styling so it reads well on a projector
st.markdown(
    """
    <style>
      .stApp p, .stApp li, .stApp label { font-size: 1.05rem; }
      .wapas-note { background:#FDE9DC; color:#7A2E07; padding:10px 14px; border-radius:8px;
                    font-size:0.95rem; margin: 0.25rem 0 0.75rem 0; }
      .st-key-call_nalsa a { min-height: 3.5rem; font-size: 1.3rem; font-weight: 700; }
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


# Owner mode: add ADMIN_MODE = true to your local .streamlit/secrets.toml to see the
# AI settings and edit the rules. Leave it out on the public site.
admin = str(secret("ADMIN_MODE")).strip().lower() in ("true", "1", "yes")

# On the public site the AI settings come only from Streamlit's Secrets settings
providers = ["gemini", "openai", "anthropic"]
saved_provider = secret("PROVIDER", "gemini")
provider = saved_provider if saved_provider in providers else "gemini"
api_key = secret("API_KEY")
model = secret("MODEL") or L.DEFAULT_MODELS[provider]

# ---------------------------------------------------------------------------
# Sidebar: settings (AI settings only in owner mode)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    if admin:
        provider = st.selectbox(
            "AI provider", providers,
            index=providers.index(saved_provider) if saved_provider in providers else 0,
        )
        typed_key = st.text_input("API key", type="password",
                                  help="Leave this empty if you saved your key in .streamlit/secrets.toml")
        api_key = typed_key.strip() or secret("API_KEY")

        default_model = secret("MODEL") if provider == saved_provider and secret("MODEL") else L.DEFAULT_MODELS[provider]
        model = st.text_input("Model name", value=default_model,
                              help="If you get a 'model not found' error, copy a current model name from your provider's website.")
    language = st.radio("Explain my plan in", ["English", "Kannada"], horizontal=True)

    if admin:
        if st.button("Test AI connection"):
            with st.spinner("Checking..."):
                answer, error = L.ask_ai(provider, api_key, model, "Reply with the single word: connected")
            if answer:
                st.success(f"AI is working ({model}).")
            else:
                st.error(error)
        st.caption("If the AI is off or fails, Wapas uses fixed templates, so the app keeps working.")

ai_on = bool(api_key)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Wapas")
st.write("Help for people whose bank account was frozen because of someone else's scam.")
st.markdown(
    '<div class="wapas-note">Wapas never asks for money, OTPs, PINs or passwords. '
    "This is a demo, so don't enter real bank details. It is not legal advice.</div>",
    unsafe_allow_html=True,
)
if ai_on:
    st.caption(f"AI is on ({provider}, {model}).")
elif admin:
    st.caption("AI is off, so Wapas is using fixed templates. Add an API key in the sidebar to turn it on.")
else:
    st.caption("Wapas is using its built-in letter templates right now.")

rules_df = L.load_rules()

# Remember things between clicks (Streamlit re-runs this file on every click)
defaults = {"details_ready": False, "show_result": False, "letter_ready": False,
            "extract_method": "", "extract_error": None, "letter_method": "",
            "rules_version": 0, "flash": None, "followups": {}, "plan_explained": None,
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
    st.session_state.plan_explained = None
    st.session_state.confirm_rewrite = False


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
    with st.expander("Have a screenshot of the SMS? Upload it instead"):
        photo = st.file_uploader("Screenshot of the bank SMS", type=["png", "jpg", "jpeg", "webp"])
        if st.button("Read my screenshot", disabled=photo is None):
            if not ai_on:
                st.warning("Reading screenshots needs the AI. Add an API key, or paste the SMS text below."
                           if admin else
                           "Reading screenshots isn't available right now. Please paste the SMS text below.")
            else:
                with st.spinner("Reading your screenshot..."):
                    text, found, error = L.extract_from_screenshot(
                        photo.getvalue(), photo.type or "image/png", provider, api_key, model)
                if text is None:
                    st.warning(f"Couldn't read the screenshot. {error}")
                else:
                    st.session_state.sms_input = text
                    for field in L.DETAIL_FIELDS:
                        st.session_state["f_" + field] = found[field]
                    st.session_state.extract_method = "AI (from screenshot)"
                    st.session_state.extract_error = None
                    st.session_state.details_ready = True
                    st.session_state.show_result = False
                    st.session_state.letter_ready = False
                    st.success("Screenshot read. Check the details below.")

    st.text_area("Bank SMS or notice", key="sms_input", height=130,
                 placeholder="Paste the SMS your bank sent you")
    st.caption("Demo tip: use the example SMS, or remove your full account number first. "
               "Wapas only needs the last 4 digits.")
    col1, col2 = st.columns(2)
    col1.button("Use example SMS", on_click=use_example)
    read_clicked = col2.button("Read my message", type="primary")

    if read_clicked:
        sms = st.session_state.get("sms_input", "").strip()
        if not sms:
            st.warning("Paste a message first, or click Use example SMS.")
        else:
            with st.spinner("Reading your message..."):
                details, method, error = L.extract_details(sms, provider, api_key, model)
            for field in L.DETAIL_FIELDS:
                st.session_state["f_" + field] = details[field]
            st.session_state.extract_method = method
            st.session_state.extract_error = error if ai_on else None
            st.session_state.details_ready = True
            st.session_state.show_result = False
            st.session_state.letter_ready = False

    if st.session_state.details_ready:
        st.subheader("2. Check your details")
        st.caption(f"Found using: {st.session_state.extract_method}. Correct anything that's wrong.")
        if st.session_state.extract_error:
            st.caption(f"AI problem: {st.session_state.extract_error}")

        with st.expander("What do these words mean?"):
            st.markdown("- **FIR** (First Information Report): the police's written record of a complaint. "
                        "Your bank's message may show its number, or another reference number.\n"
                        "- **Debit freeze**: the bank stops money from going out of your account.")

        c1, c2 = st.columns(2)
        c1.text_input("Your full name", key="f_name")
        c2.text_input("Bank", key="f_bank")
        c1.text_input("Branch", key="f_branch")
        c2.text_input("Account: last 4 digits only", key="f_last4", max_chars=4)
        c1.text_input("Amount in dispute", key="f_amount")
        c2.text_input("Date of freeze", key="f_freeze_date")
        c1.text_input("Police station or cyber cell", key="f_police")
        c2.text_input("Case, FIR or reference number", key="f_case_no")

        st.subheader("3. Answer three questions")
        q1 = st.radio("Did you receive this money for something you sold or a service you gave?",
                      ["Yes", "No"], index=None, horizontal=True, key="q1")
        q2 = st.radio("Do you personally know the person who paid you?",
                      ["Yes", "No"], index=None, horizontal=True, key="q2")
        q3 = st.radio("Did you ever let someone else use your bank account or UPI?",
                      ["Yes", "No"], index=None, horizontal=True, key="q3")

        if st.button("Show my plan and letter", type="primary"):
            if None in (q1, q2, q3):
                st.warning("Please answer all three questions.")
            else:
                st.session_state.show_result = True
                st.session_state.letter_ready = False
                st.session_state.plan_explained = None
                st.session_state.confirm_rewrite = False

        if st.session_state.show_result and None not in (q1, q2, q3):
            details = {f: st.session_state["f_" + f] for f in ["name"] + L.DETAIL_FIELDS}
            details["last4"] = L.only_last4(details["last4"])

            if q3 == "Yes":
                # Honest route: no innocence letter for people who lent their account
                st.error("Because you let someone else use your account, this is serious. "
                         "Please don't send a letter saying you're innocent. Get free legal help first.")
                st.link_button("Call NALSA free legal aid: 15100", "tel:15100",
                               type="primary", width="stretch", key="call_nalsa")
                for _, r in L.rules_for(rules_df, "lent").iterrows():
                    st.markdown(f"- {r['rule']}")
                    st.caption(f"Source: {r['source']}. Last checked: {r['last_verified']}.")
            else:
                if q1 == "No":
                    st.info("Wapas works best when the money was received for a genuine sale or service. "
                            "If that's not your situation, talk to free legal aid before sending anything.")

                st.subheader("4. Your plan")
                plan_rules = L.rules_for(rules_df, "frozen")
                for number, (_, r) in enumerate(plan_rules.iterrows(), start=1):
                    st.markdown(f"**{number}.** {r['rule']}")
                    st.caption(f"Source: {r['source']}. Last checked: {r['last_verified']}.")

                if st.button(f"Explain this plan in simple {language}"):
                    with st.spinner("Explaining..."):
                        text, error = L.explain_plan(plan_rules, language, provider, api_key, model)
                    st.session_state.plan_explained = text or (
                        f"The AI couldn't explain this right now. {error}" if admin else
                        "The AI couldn't explain this right now. The steps above are the full plan.")
                if st.session_state.plan_explained:
                    st.info(st.session_state.plan_explained)

                st.subheader("5. Your letter")
                if not st.session_state.letter_ready:
                    with st.spinner("Writing your letter..."):
                        if ai_on:
                            letter, method, error = L.ai_letter(details, rules_df, provider, api_key, model)
                        else:
                            letter, method, error = L.template_letter(details, rules_df), "fixed template (AI off)", None
                    st.session_state.letter_box = letter
                    st.session_state.letter_original = letter  # to tell later if the user edited it
                    st.session_state.letter_method = method
                    st.session_state.letter_error = error
                    st.session_state.letter_ready = True

                st.caption(f"Written using: {st.session_state.letter_method}. Check every detail before sending.")
                if st.session_state.get("letter_error"):
                    st.caption(f"AI problem: {st.session_state.letter_error}")
                st.text_area("You can edit the letter here", key="letter_box", height=460)

                b1, b2, b3 = st.columns(3)
                b1.download_button("Download letter", data=st.session_state.letter_box,
                                   file_name=f"wapas_letter_{details['last4'] or 'case'}.txt")
                if b2.button("Rewrite letter"):
                    if st.session_state.letter_box != st.session_state.letter_original:
                        st.session_state.confirm_rewrite = True  # they edited it, so ask first
                    else:
                        st.session_state.letter_ready = False
                        st.rerun()
                if b3.button("Save this case", type="primary"):
                    case_id = save_my_case(details, st.session_state.letter_box)
                    st.success(f"Saved as case #{case_id}. Open My cases to track it.")

                if st.session_state.confirm_rewrite:
                    st.warning("You edited this letter. Rewriting replaces your edits with a new letter.")
                    r1, r2 = st.columns(2)
                    if r1.button("Replace my edits with a new letter"):
                        st.session_state.confirm_rewrite = False
                        st.session_state.letter_ready = False
                        st.rerun()
                    if r2.button("Keep my edits"):
                        st.session_state.confirm_rewrite = False
                        st.rerun()

                subject = f"Request to limit the debit freeze on account ending {details['last4']}"
                s1, s2 = st.columns(2)
                s1.link_button("Share on WhatsApp", L.whatsapp_link(st.session_state.letter_box))
                s2.link_button("Send by email", L.email_link(subject, st.session_state.letter_box))
                st.caption("Share it with a family member or lawyer to check, or open your email app "
                           "with the letter ready to send to the bank.")

                st.info("**What to do next**\n\n"
                        "1. Fill in anything still in [square brackets] and check every detail.\n"
                        "2. Send the letter to your bank branch manager. Keep a copy.\n"
                        "3. Note the date you sent it, and set the case status to \"Sent to bank\" in My cases.\n"
                        "4. If the bank has not replied in 15 days, send the follow-up letter from My cases.")

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

        st.dataframe(cases[["id", "created", "name", "bank", "last4", "status", "follow_up"]],
                     hide_index=True)
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
                if ai_on:
                    text, method, error = L.ai_followup(case, provider, api_key, model)
                else:
                    text, method, error = L.template_followup(case), "fixed template (AI off)", None
            st.session_state.followups[chosen] = (text, method)

        if chosen in st.session_state.followups:
            text, method = st.session_state.followups[chosen]
            st.warning(f"Day 15 reminder: no reply yet on case #{chosen}? Send this follow-up today.")
            st.caption(f"Written using: {method}.")
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

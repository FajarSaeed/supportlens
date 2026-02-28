"""
LLM module — works WITHOUT an OpenAI API key.

If OPENAI_API_KEY is set in the environment (or a .env file), real GPT-4o-mini
calls are made.  Otherwise the module falls back to fast, deterministic
keyword-based stubs so the whole app runs locally for free.
"""

import os
import random
import time

# ── optional dotenv loading ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # python-dotenv not installed — that's fine

# ── check whether we have a real key ─────────────────────────────────────────
_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_USE_REAL_LLM = bool(_OPENAI_KEY and not _OPENAI_KEY.startswith("sk-your"))

# ── keyword-based mock classifier ────────────────────────────────────────────
_BILLING_KW    = {"invoice", "charge", "charged", "payment", "pricing", "fee", "subscription", "bill", "cost", "price"}
_REFUND_KW     = {"refund", "money back", "return", "dispute", "credit", "reimburse"}
_ACCESS_KW     = {"login", "log in", "password", "locked", "mfa", "2fa", "access", "sign in", "account locked"}
_CANCEL_KW     = {"cancel", "cancellation", "downgrade", "close account", "unsubscribe", "terminate"}

_MOCK_RESPONSES: dict[str, list[str]] = {
    "Billing": [
        "I can help with billing questions. Could you share the invoice ID or the charge date so I can look into it?",
        "Happy to assist with your billing concern. What's the invoice number or the amount in question?",
        "Let me pull up your billing details — can you provide the invoice ID or the email on the account?",
    ],
    "Refund": [
        "I can process a refund request for you. Please share the invoice ID and the reason for the refund.",
        "Refunds are usually processed within 5–7 business days. What's the invoice number and reason?",
        "I'll look into that refund. Could you provide the charge date and the amount?",
    ],
    "Account Access": [
        "I can help you regain access. Did you try the 'Forgot Password' link? If MFA is the issue, I can reset it.",
        "Account lockouts are usually resolved quickly. Have you tried resetting your password via email?",
        "Let me help unlock your account. Can you confirm the email address associated with it?",
    ],
    "Cancellation": [
        "I can process your cancellation. Would you like it effective immediately or at the end of the billing period?",
        "Before I cancel, is there anything we can do to improve your experience? If not, I'll proceed right away.",
        "Understood — I'll cancel your subscription. Do you want a confirmation email sent to your address?",
    ],
    "General Inquiry": [
        "Great question! Could you give me a bit more detail so I can point you to the right resource?",
        "Happy to help. Can you elaborate a little so I can give you the most accurate answer?",
        "Thanks for reaching out. Let me look into that for you — could you share more context?",
    ],
}


def _mock_classify(user_message: str, bot_response: str = "") -> str:
    text = (user_message + " " + bot_response).lower()
    if any(k in text for k in _CANCEL_KW):
        return "Cancellation"
    if any(k in text for k in _REFUND_KW):
        return "Refund"
    if any(k in text for k in _ACCESS_KW):
        return "Account Access"
    if any(k in text for k in _BILLING_KW):
        return "Billing"
    return "General Inquiry"


def _mock_chat(user_message: str) -> str:
    category = _mock_classify(user_message)
    return random.choice(_MOCK_RESPONSES[category])


# ── real OpenAI helpers (only used when key is present) ──────────────────────
CHATBOT_SYSTEM_PROMPT = (
    "You are a helpful customer support agent for a SaaS billing platform. "
    "Be concise, friendly, and practical. If you need account-specific data, "
    "ask for the minimum info required."
)

CLASSIFIER_SYSTEM_PROMPT = """You are a strict classifier for customer support chatbot traces.

Return EXACTLY one category from this list (and nothing else):
Billing
Refund
Account Access
Cancellation
General Inquiry

Definitions:
- Billing: invoices, charges, pricing, payment methods, subscription fees
- Refund: money back, returns, charge disputes, credits
- Account Access: login, password reset, locked accounts, MFA problems
- Cancellation: cancel subscription, downgrade plan, close account
- General Inquiry: anything else

Tie-break rules (when multiple intents appear):
1) If user asks for cancellation/downgrade/close account -> Cancellation.
2) Else if user asks for refund/charge dispute/credit -> Refund.
3) Else if user cannot log in / reset password / MFA -> Account Access.
4) Else if money/pricing/invoice/charges/payment method -> Billing.
5) Else -> General Inquiry.

Only output the single category string.
"""


def _real_chat(user_message: str, model: str = "gpt-4o-mini") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=_OPENAI_KEY)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )
    content = resp.choices[0].message.content
    return content.strip() if content is not None else ""


def _real_classify(user_message: str, bot_response: str, model: str = "gpt-4o-mini") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=_OPENAI_KEY)
    content = f"Trace:\nUSER: {user_message}\nBOT: {bot_response}\n"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content
    category = raw.strip() if raw is not None else ""
    allowed = {"Billing", "Refund", "Account Access", "Cancellation", "General Inquiry"}
    return category if category in allowed else "General Inquiry"


# ── public API ────────────────────────────────────────────────────────────────

def llm_classify(user_message: str, bot_response: str, model: str = "gpt-4o-mini") -> str:
    if _USE_REAL_LLM:
        return _real_classify(user_message, bot_response, model)
    return _mock_classify(user_message, bot_response)


def llm_chat(user_message: str, model: str = "gpt-4o-mini") -> str:
    if _USE_REAL_LLM:
        return _real_chat(user_message, model)
    return _mock_chat(user_message)


def chat_with_timing(user_message: str, model: str = "gpt-4o-mini") -> tuple[str, int]:
    start = time.perf_counter()
    bot = llm_chat(user_message, model=model)
    ms = int((time.perf_counter() - start) * 1000)
    return bot, ms

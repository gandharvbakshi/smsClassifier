"""Phishing policy helpers shared by the backend and unit tests.

This module is intentionally importable without loading any models.
It contains the phishing-specific policy gates used by the Android backend:

- strong danger overrides for credential, KYC/account-block, APK/install,
  payment-action, and short-link abuse
- conservative low-risk contexts for legitimate receipts, service updates,
  telecom notices, and delivery/service OTP sharing
- first-party sender/domain alignment as supporting evidence only
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

URL_PATTERN = re.compile(r"https?://[^\s<>)\]]+|www\.[^\s<>)\]]+", re.IGNORECASE)
REDACTED_URL_PATTERN = re.compile(r"<URL:[^>]+>", re.IGNORECASE)
SHORT_URL_HOSTS = {
    "bit.ly",
    "bitly.com",
    "cutt.ly",
    "goo.gl",
    "is.gd",
    "lnkd.in",
    "tinyurl.com",
    "t.co",
}
BRAND_TOKEN_PATTERN = re.compile(
    r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY|"
    r"SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART|NETFLIX|SPOTIFY|"
    r"INSTAGRAM|FACEBOOK|TWITTER|GODADDY|BSE|VI|JIO|AIRTEL|MGMOTOR|MG|"
    r"URBANCOMPANY|MCDONALDS|YESBANK|FLYAIX|AIRINDIAEXPRESS)\b",
    re.IGNORECASE,
)
BRAND_DOMAIN_SUFFIXES = {
    "AMAZON": ("amazon.in", "amazon.com"),
    "DELHIVERY": ("delhivery.com",),
    "SWIGGY": ("swiggy.com",),
    "VI": ("myvi.in", "viapp.onelink.me", "vodafoneidea.com"),
    "JIO": ("jio.com",),
    "AIRTEL": ("airtel.in",),
    "MG": ("mgmotor.co.in", "mg-url.in"),
    "MGMOTOR": ("mgmotor.co.in", "mg-url.in"),
    "URBANCOMPANY": ("urbancompany.com",),
    "MCDONALDS": ("mcdonalds.co.in", "mcdelivery.co.in"),
    "YESBANK": ("yesbank.in",),
    "FLYAIX": ("airindiaexpress.com",),
    "AIRINDIAEXPRESS": ("airindiaexpress.com",),
}
SENDER_BRAND_SIGNATURES = [
    (
        re.compile(r"MGINET", re.IGNORECASE),
        re.compile(r"\b(?:JSW\s+)?MG(?:\s+MOTOR|\s+FAMILY|_[A-Z0-9_]+)", re.IGNORECASE),
    ),
    (
        re.compile(r"FLYAIX", re.IGNORECASE),
        re.compile(r"\bAIR\s+INDIA\s+EXPRESS\b", re.IGNORECASE),
    ),
    (
        re.compile(r"VICARE", re.IGNORECASE),
        re.compile(r"\bVI\s+(?:APP|BILL|PLAN|ACCOUNT)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"URBNCP", re.IGNORECASE),
        re.compile(r"\bURBAN\s+COMPANY\b", re.IGNORECASE),
    ),
    (
        re.compile(r"MCDNLD", re.IGNORECASE),
        re.compile(r"\bMCDONALD(?:'S|S)?\b", re.IGNORECASE),
    ),
]

LEGIT_CONTEXT_PATTERNS = [
    (
        "bank transaction / standing-instruction notice",
        0.15,
        0.08,
        False,
        re.compile(
            r"\b("
            r"debit(?:ed)?|credit(?:ed)?|transaction|txn|standing instruction|"
            r"auto[- ]debit|auto[- ]?pay|mandate|ecs|nach|account statement|statement|"
            r"emi|scheduled payment|payment received|processed|refund(?:ed)?"
            r"|payment (?:of )?(?:rs\.?\s*)?\d+(?:[.,]\d+)? (?:was )?successful|receipt"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delivery / order confirmation",
        0.15,
        0.08,
        False,
        re.compile(
            r"\b("
            r"order (?:has )?(?:confirmed|placed|shipped|dispatched)|"
            r"received your .* order|shipment|tracking|"
            r"delivery(?: update| status)?|out for delivery|courier|package|delivered"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bill / data alert",
        0.18,
        0.10,
        False,
        re.compile(
            r"\b("
            r"bill due|due date|invoice|recharge|data balance|data pack|plan validity|"
            r"validity|usage alert|postpaid|prepaid|mobile data|broadband|"
            r"electricity bill|gas bill|internet bill"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "brand unsubscribe / preference link",
        0.25,
        0.15,
        False,
        re.compile(r"\b(unsubscribe|opt[- ]?out|sms preferences?|email preferences?)\b", re.IGNORECASE),
    ),
    (
        "security education / investor awareness",
        0.20,
        0.12,
        False,
        re.compile(
            r"\b(beware|unsolicited tips|take informed decision|attention investors?|security education)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "completed / confirmed order",
        0.15,
        0.08,
        True,
        re.compile(
            r"\b("
            r"order\s+(?:#?\d+\s+)?(?:confirmed|completed|placed|delivered)|"
            r"booking\s+(?:confirmed|completed)|"
            r"congratulations\s+on\s+(?:your\s+)?booking|"
            r"booking\s+id\s+is|"
            r"purchase\s+(?:confirmed|completed)|"
            r"thank you for your purchase|"
            r"order receipt|purchase receipt|"
            r"order details"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "receipt / e-bill",
        0.12,
        0.06,
        True,
        re.compile(
            r"\b("
            r"receipt(?:\s+(?:generated|issued|for|of))?|"
            r"tax invoice|e[- ]?bill|invoice|"
            r"payment\s+(?:receipt|successful|completed)|"
            r"bill\s+(?:generated|issued|receipt)|"
            r"bill\s+copy|download\s+your\s+.{0,24}\s*bill|"
            r"statement"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "booked / completed service appointment",
        0.12,
        0.06,
        True,
        re.compile(
            r"\b("
            r"appointment(?:\s+(?:is|was|has been))?\s+(?:booked|confirmed|completed|scheduled)|"
            r"service\s+appointment(?:\s+(?:is|was|has been))?\s+(?:booked|confirmed|completed|scheduled)|"
            r"service\s+(?:booked|confirmed|completed|scheduled)|"
            r"visit\s+(?:confirmed|scheduled)|"
            r"technician\s+(?:assigned|scheduled)|"
            r"installation\s+(?:scheduled|completed)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "review / rating link",
        0.18,
        0.10,
        True,
        re.compile(
            r"\b("
            r"rate\s+(?:your|us|this|the)\s+(?:experience|service)?|"
            r"leave a review|write a review|review link|rating link|"
            r"feedback link|how was your experience|share your feedback"
            r"|tell us about (?:your )?.{0,40}experience"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "sales enquiry / detailed quote follow-up",
        0.15,
        0.08,
        True,
        re.compile(
            r"\b(further to your interest|detailed quote|vehicle quote|sales enquiry)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "flight web check-in / trip management",
        0.15,
        0.08,
        True,
        re.compile(
            r"\b(web check[- ]?in|complete your check[- ]?in|choose your .{0,20}seat)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "telecom plan / data / account notice",
        0.15,
        0.08,
        True,
        re.compile(
            r"\b("
            r"plan\s+(?:renewed|activated|active|expiry|expires)|"
            r"data\s+(?:usage|alert|balance|pack|limit)|"
            r"recharge\s+(?:successful|completed)|"
            r"account\s+(?:notice|update|summary)|"
            r"prepaid\s+plan|postpaid\s+bill|mobile\s+account|"
            r"validity\s+(?:ends|expires|extended)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delivery / service OTP sharing",
        0.10,
        0.05,
        False,
        re.compile(
            r"\b("
            r"share this (?:delivery|service) (?:otp|code)|"
            r"share (?:the )?(?:delivery|service) (?:otp|code)|"
            r"please share this code after checking|"
            r"delivery otp|service otp"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]

LEGIT_OTP_PATTERNS = [
    re.compile(
        r"\b(otp|verification code|verify code|login code|sign in code|"
        r"one[- ]time password|authentication code|auth code|passcode|code\s*[:#]\s*\d{4,8})\b",
        re.IGNORECASE,
    )
]

DANGER_PATTERNS = [
    (
        "credential / password collection",
        re.compile(
            r"\b("
            r"cvv|card details|bank details|account details|login details|"
            r"share otp|send otp|enter otp|confirm credentials|verify credentials|"
            r"reset password|change password|re[- ]?enter (?:your )?(?:details|credentials|password)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "KYC / account-blocked urgency",
        re.compile(
            r"\b("
            r"kyc|account blocked|blocked account|account will be blocked|"
            r"account suspended|suspended|freeze|deactivate|limited access|"
            r"verify immediately|verify now|urgent action|expires soon|"
            r"within \d+\s*(hours?|days?)|parcel is on hold|shipment is on hold|"
            r"redelivery fee|release (?:it|shipment|parcel|package)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "APK / install lure",
        re.compile(
            r"\b(apk|install app|download app|sideload|unknown sources|update app)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "UPI / payment trap",
        re.compile(
            r"\b("
            r"pay request|collect request|scan qr|request money|"
            r"send money|transfer money|payment link|refund link"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]

PAYMENT_TRAP_PATTERN = re.compile(
    r"\b(upi|pay request|pay now|transfer money|send money|request money|"
    r"collect request|scan qr|qr code|payment link|refund link)\b",
    re.IGNORECASE,
)
PAYMENT_ACTION_LURE_PATTERN = re.compile(
    r"\b("
    r"pay request|pay now|transfer money|send money|request money|collect request|"
    r"scan qr|qr code|payment link|refund link|claim (?:your )?refund|"
    r"approve (?:the )?(?:request|payment|collect)|accept (?:the )?collect|"
    r"authorize (?:payment|upi|mandate)|verify (?:upi|payment)"
    r")\b",
    re.IGNORECASE,
)
SHORT_URL_DANGER_PATTERN = re.compile(
    r"\b(login|verify|update|password|pin|cvv|kyc|install|apk|upi|payment|transfer|"
    r"send money|request money|collect request|urgent)\b",
    re.IGNORECASE,
)


def _extract_url_hosts(text: str) -> List[str]:
    hosts: List[str] = []
    for match in URL_PATTERN.finditer(text or ""):
        raw_url = match.group(0).rstrip(").,;:!?]")
        if raw_url.startswith("www."):
            raw_url = f"http://{raw_url}"
        parsed = urlparse(raw_url)
        host = (parsed.netloc or parsed.path).lower().strip(".")
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.append(host)
    return hosts


def _extract_brand_tokens(text: str, sender: Optional[str]) -> List[str]:
    haystack = f"{sender or ''} {text or ''}"
    return sorted({match.group(1).upper() for match in BRAND_TOKEN_PATTERN.finditer(haystack)})


def _has_sender_brand_signature_alignment(text: str, sender: Optional[str]) -> bool:
    normalized_sender = sender or ""
    normalized_text = text or ""
    return any(
        sender_pattern.search(normalized_sender) and text_pattern.search(normalized_text)
        for sender_pattern, text_pattern in SENDER_BRAND_SIGNATURES
    )


def _has_link_reference(text: str) -> bool:
    return bool(URL_PATTERN.search(text or "") or REDACTED_URL_PATTERN.search(text or ""))


def _host_matches_brand_token(host: str, token: str) -> bool:
    normalized_host = host.lower().strip(".")
    for suffix in BRAND_DOMAIN_SUFFIXES.get(token.upper(), ()):
        if normalized_host == suffix or normalized_host.endswith(f".{suffix}"):
            return True
    labels = re.split(r"[.-]", normalized_host)
    return token.lower() in labels


def _has_first_party_alignment(text: str, sender: Optional[str]) -> bool:
    hosts = _extract_url_hosts(text)
    if not hosts:
        return False
    brand_tokens = _extract_brand_tokens(text, sender)
    if not brand_tokens:
        return False
    for host in hosts:
        if host in SHORT_URL_HOSTS:
            continue
        if any(_host_matches_brand_token(host, token) for token in brand_tokens):
            return True
    return False


def _looks_like_low_risk_payment_notice(text: str, sender: Optional[str]) -> bool:
    normalized = f"{sender or ''} {text or ''}"
    bank_notice_pattern = next(
        pattern
        for label, _cap, _aligned_cap, _requires_alignment, pattern in LEGIT_CONTEXT_PATTERNS
        if label == "bank transaction / standing-instruction notice"
    )
    if not bank_notice_pattern.search(normalized):
        return False
    if PAYMENT_ACTION_LURE_PATTERN.search(normalized):
        return False
    if re.search(
        r"\b(click|open|login|verify now|kyc|blocked|suspended|freeze|deactivate|"
        r"urgent action|expires soon|install|apk)\b",
        normalized,
        re.IGNORECASE,
    ):
        return False
    return bool(
        re.search(
            r"\b(upi|card|acct|account|debit(?:ed)?|credit(?:ed)?|txn|transaction|"
            r"ref|available|avl|balance|bal)\b",
            normalized,
            re.IGNORECASE,
        )
    )


def _looks_like_legitimate_delivery_share(
    text: str,
    is_otp: bool,
    otp_intent: str,
) -> bool:
    if not is_otp or otp_intent != "DELIVERY_OR_SERVICE_OTP":
        return False
    normalized = text or ""
    if not re.search(r"\b(delivery|deliver|courier|package|parcel|service|technician|agent)\b", normalized, re.IGNORECASE):
        return False
    if not re.search(r"\bshare\b.{0,32}\b(otp|code)\b|\b(otp|code)\b.{0,32}\bshare\b", normalized, re.IGNORECASE):
        return False
    return not bool(
        re.search(
            r"\b(cvv|card details|bank details|login details|send otp|enter otp|"
            r"credentials?|password|pay now|payment link|refund link|kyc|account blocked)\b",
            normalized,
            re.IGNORECASE,
        )
    )


def _has_strong_phishing_danger_signal(
    text: str,
    sender: Optional[str],
    is_otp: bool = False,
    otp_intent: str = "NOT_OTP",
) -> List[str]:
    normalized = f"{sender or ''} {text or ''}"
    lowered = normalized.lower()
    has_link_reference = _has_link_reference(text) or bool(re.search(r"\b(link|url)\b", lowered))
    signals: List[str] = []

    for label, pattern in DANGER_PATTERNS:
        if pattern.search(normalized):
            if label == "credential / password collection" and _looks_like_legitimate_delivery_share(
                text,
                is_otp,
                otp_intent,
            ):
                continue
            signals.append(label)

    hosts = _extract_url_hosts(text)
    brand_tokens = _extract_brand_tokens(text, sender)
    if hosts and brand_tokens:
        for host in hosts:
            if host in SHORT_URL_HOSTS:
                if SHORT_URL_DANGER_PATTERN.search(normalized):
                    signals.append("suspicious shortened link in dangerous context")
                continue
            if any(_host_matches_brand_token(host, token) for token in brand_tokens):
                continue
            if SHORT_URL_DANGER_PATTERN.search(normalized) or "login" in lowered or "verify" in lowered:
                signals.append(f"brand-domain mismatch ({host})")
                break

    if (
        PAYMENT_TRAP_PATTERN.search(normalized)
        and has_link_reference
        and (
            PAYMENT_ACTION_LURE_PATTERN.search(normalized)
            or not _looks_like_low_risk_payment_notice(text, sender)
        )
    ):
        signals.append("payment trap with link")

    return list(dict.fromkeys(signals))


def _should_promote_ml_negative(
    text: str,
    sender: Optional[str],
    raw_phish_prob: float,
) -> bool:
    """Promote only the corpus-validated numeric-sender KYC login lure."""
    normalized_sender = (sender or "").strip()
    if raw_phish_prob < 0.30 or not re.fullmatch(r"\+?\d{6,14}", normalized_sender):
        return False
    return bool(
        re.search(r"\bkyc\b", text or "", re.IGNORECASE)
        and re.search(r"\b(log\s*in|login|sign\s*in)\b", text or "", re.IGNORECASE)
    )


def _detect_legit_low_risk_context(
    text: str,
    sender: Optional[str],
    is_otp: bool,
    otp_intent: str,
) -> Optional[Dict[str, Any]]:
    normalized = text or ""
    reasons: List[str] = []
    first_party_alignment = _has_first_party_alignment(normalized, sender)
    sender_brand_alignment = _has_sender_brand_signature_alignment(normalized, sender)
    supporting_alignment = first_party_alignment or sender_brand_alignment
    has_link = _has_link_reference(normalized)

    if is_otp and otp_intent in {"APP_LOGIN_OTP", "APP_ACCOUNT_CHANGE_OTP", "GENERIC_APP_ACTION_OTP", "DELIVERY_OR_SERVICE_OTP"}:
        if LEGIT_OTP_PATTERNS[0].search(normalized):
            reasons.append("app OTP verification")
            return {"label": "app OTP verification", "cap": 0.08, "reasons": reasons}

    for label, cap, aligned_cap, requires_alignment, pattern in LEGIT_CONTEXT_PATTERNS:
        if pattern.search(normalized):
            if requires_alignment and has_link and not supporting_alignment:
                continue
            reasons.append(label)
            if supporting_alignment:
                reasons.append(
                    "first-party sender/domain alignment"
                    if first_party_alignment
                    else "registered sender/brand signature alignment"
                )
                return {"label": label, "cap": aligned_cap, "reasons": reasons}
            return {"label": label, "cap": cap, "reasons": reasons}

    return None


def _apply_phishing_policy(
    text: str,
    sender: Optional[str],
    is_otp: bool,
    otp_intent: str,
    raw_phish_prob: float,
    is_phishing_ml: bool,
    phish_threshold: float,
) -> tuple[bool, float, List[str]]:
    danger_signals = _has_strong_phishing_danger_signal(text, sender, is_otp, otp_intent)
    if danger_signals:
        if is_phishing_ml:
            return True, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"] + [
                f"phishing calibration skipped: {', '.join(danger_signals)}"
            ]
        if _should_promote_ml_negative(text, sender, raw_phish_prob):
            return True, max(raw_phish_prob, phish_threshold), [
                f"raw phishScore={raw_phish_prob:.3f}",
                "phishing promoted by numeric-sender KYC login lure",
            ]
        return False, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"] + [
            f"high-risk signals observed below ML threshold: {', '.join(danger_signals)}"
        ]

    if not is_phishing_ml:
        return False, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"]

    low_risk_context = _detect_legit_low_risk_context(text, sender, is_otp, otp_intent)
    if not low_risk_context:
        return True, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"]

    calibrated_phish_prob = min(raw_phish_prob, float(low_risk_context["cap"]))
    if calibrated_phish_prob >= phish_threshold:
        return True, raw_phish_prob, [
            f"raw phishScore={raw_phish_prob:.3f}",
            f"legit context matched ({low_risk_context['label']}) but calibrated score stayed above threshold",
        ]

    return False, calibrated_phish_prob, [
        f"raw phishScore={raw_phish_prob:.3f}",
        (
            f"phishing downgraded by context calibration ({low_risk_context['label']}); "
            f"calibrated phishScore={calibrated_phish_prob:.3f}"
        ),
    ]

"""
Shared heuristic OTP classifier module for backend and testing.

This module contains the heuristic classifier used by:
- Backend server (android_backend_server.py)
- Test scripts
- Other classification pipelines

Design philosophy
-----------------
The classifier prioritises HIGH PRECISION: when we say is_otp=True, it really
should be one. We accept slightly lower recall (some real OTPs may fall through
to the ML model) in exchange for far fewer false positives.

The previous version over-fired on credit card transaction notifications,
delivery confirmations, marketing messages and balance alerts that just happened
to contain a 4-8 digit number from a "known sender".

The 2026-05 rewrite introduces three changes:

  1. **Hard-negative gate**: if the message contains transaction-context
     words (spent / debited / refund / out for delivery / discount / etc.)
     AND no strong OTP signal, we return is_otp=False immediately.

  2. **Sender hint requires corroboration**: matching a known OTP sender
     pattern (ICICI/HDFC/SWIGGY/...) is no longer enough on its own. The
     body must ALSO contain at least one weak OTP signal.

  3. **Removed the over-generous fallbacks**:
       - "short message with numeric code" (lines 209-218 of v1)
       - "validity period alone" (lines 178-183 of v1)
       - "security warning alone" (lines 185-190 of v1)
     These all over-fired on bank alerts.

Delivery-OTP coverage was strengthened by adding "delivery code", "guest code",
"pickup code" etc. to the OTP_KEYWORDS list, since those are legitimate OTPs
that don't use the literal word "OTP".
"""

import re
from typing import Dict, List, Optional


class HeuristicOtpClassifier:
    """High-precision heuristic OTP classifier."""

    # ------------------------------------------------------------------ #
    # POSITIVE SIGNALS (presence increases OTP confidence)
    # ------------------------------------------------------------------ #

    OTP_KEYWORDS = [
        "otp", "verification code", "authentication code", "your code",
        "one time password", "one-time password", "verification pin",
        "access code", "security code", "password code", "login code",
        "verification", "authenticate",
        # OTPs that say "activation code" / "one-time activation" instead of OTP
        "activation code", "one-time activation", "one time activation",
        "one-time code", "one time code",
        # Delivery / service / building OTPs that don't literally say "OTP":
        "delivery code", "pickup code", "courier code",
        "guest code", "visitor code", "check-in code", "check-out code",
    ]

    OTP_PHRASES = [
        "is your", "code is", "verify with", "use code", "enter code",
        "use otp", "your otp", "otp is", "code to", "verification code is",
        "your verification", "verification code", "login code is",
        # Delivery OTPs ("PLEASE SHARE THIS CODE AFTER CHECKING ALL THE
        # ITEMS IN THE DELIVERED ORDER : 8174")
        "share this code", "share the code", "share code", "please share",
    ]

    OTP_SENDER_PATTERNS = [
        "BANK", "PAYTM", "PHONEPE", "GPAY", "SWIGGY", "ZOMATO",
        "AMAZON", "FLIPKART", "ICICI", "HDFC", "SBI", "AXIS",
        "OTP", "VERIFY", "CODE", "AUTH",
    ]

    SECURITY_WARNINGS = [
        "do not share", "don't share", "keep secret",
        "confidential", "never share", "do not disclose", "keep it safe",
        "don't reveal", "never reveal",
    ]

    VALIDITY_WORDS = [
        "valid", "validity", "expires", "expiry", "minutes", "min",
        "seconds", "sec", "valid for", "expires in",
    ]

    VERIFICATION_WORDS = [
        "verify", "verification", "authenticate", "authentication",
        "login", "sign in", "access", "confirm",
    ]

    CODE_PATTERN = re.compile(r"\b\d{4,8}\b")

    STRONG_OTP_PATTERNS = [
        re.compile(r"\b(otp|one.?time.?password)\b.*?\b\d{4,8}\b", re.IGNORECASE),
        re.compile(r"\b\d{4,8}\b.*?(otp|code|verification)", re.IGNORECASE),
        re.compile(r"(your|use|enter).*?(otp|code).*?\b\d{4,8}\b", re.IGNORECASE),
        re.compile(r"\b\d{4,8}\b.*?(is|as).*?(your|the).*?(otp|code|password)", re.IGNORECASE),
        # "X code: 1234567" / "code:1234" / "code# 1234" — common compact OTPs
        re.compile(r"\bcode\s*[:#]\s*\d{4,8}\b", re.IGNORECASE),
    ]

    # Strip URLs before pattern matching to avoid spurious matches on URL
    # query strings like "?CODE=000942700000604" inside marketing/order-receipt
    # SMS that contain a real (non-OTP) digit elsewhere in the body.
    URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

    # Code at start with explicit OTP context
    START_CODE_PATTERN = re.compile(
        r"^\b\d{4,8}\b\s*(?:is|for|your|use|enter|verification|code|otp|password)",
        re.IGNORECASE,
    )

    # Verification words with code
    VERIFICATION_CODE_PATTERN = re.compile(
        r"(?:verify|verification|authenticate|login|sign.?in).*?\b\d{4,8}\b",
        re.IGNORECASE,
    )

    # Security warning with code in same message
    SECURITY_CODE_PATTERN = re.compile(
        r"(?:do\s+not\s+share|don'?t\s+share|keep\s+secret|confidential|never\s+share).*?\b\d{4,8}\b",
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------ #
    # NEGATIVE INDICATORS (presence + no strong OTP signal => NOT an OTP)
    #
    # These patterns are deliberately specific to transaction / delivery /
    # marketing / status notifications. They almost never appear in real OTP
    # messages, except as incidental words like "INR 500" inside a real OTP
    # message — and in those cases the strong OTP signal (the literal word
    # "OTP" or "One-Time Password") will still be present and override this
    # gate.
    # ------------------------------------------------------------------ #

    NEGATIVE_INDICATORS = [
        # Money in/out (transaction notifications)
        re.compile(r"\b(spent|debited|credited|withdrawn|deposited)\b", re.IGNORECASE),
        re.compile(r"\b(received|sent|transferred)\s+(rs\.?|inr|usd|eur|gbp|₹)\b", re.IGNORECASE),
        # Bank balance / available limit
        re.compile(r"\b(avl|available|closing|opening)\s+(bal|balance|limit)\b", re.IGNORECASE),
        re.compile(r"\b(your\s+)?(account|wallet|card)\s+balance\b", re.IGNORECASE),
        # Bills / EMI / due
        re.compile(r"\b(bill|emi|overdue|payment\s+due|outstanding|due\s+on|due\s+by|due\s+date)\b", re.IGNORECASE),
        # Refund / payment processed (recurring payments, refund notifications)
        re.compile(r"\brefund\s+(of|for|has\s+been|reference)\b", re.IGNORECASE),
        re.compile(r"\b(payment\s+(?:has\s+been\s+)?(?:successfully\s+)?(?:processed|received|completed))\b", re.IGNORECASE),
        re.compile(r"\bstanding\s+instruction\b", re.IGNORECASE),
        # Shipping / delivery status (without OTP context — distinct from "delivery code")
        re.compile(r"\b(out\s+for\s+delivery|delivered|shipped|dispatched|in\s+transit)\b", re.IGNORECASE),
        re.compile(r"\b(track\s+(?:your\s+)?order|tracking\s+(?:id|number|link))\b", re.IGNORECASE),
        re.compile(r"\border\s+#?\d+\s+(?:has\s+been|is\s+)?(?:placed|confirmed|cancelled|shipped|delivered)", re.IGNORECASE),
        re.compile(r"\b(arrived|reached|on[\s-]?its[\s-]?way|on[\s-]?the[\s-]?way)\b", re.IGNORECASE),
        re.compile(r"\b(scheduled\s+for\s+delivery|will\s+be\s+delivered|order\s+is\s+scheduled)\b", re.IGNORECASE),
        # Promotional / offers / marketing
        re.compile(r"\b(offer|sale|discount|coupon|cashback|reward|win|congratulations|free)\b", re.IGNORECASE),
        re.compile(r"\b(get\s+rs\.?\s*\d|flat\s+\d+%|extra\s+\d+%|upto\s+\d+%)\b", re.IGNORECASE),
        # Recharge / data
        re.compile(r"\b(recharge|data\s+pack|talktime|validity\s+upto)\b", re.IGNORECASE),
        # Pickup executive / driver / appointment confirmations
        re.compile(r"\b(pickup\s+executive|driver|booking\s+(?:confirmed|scheduled)|reservation\s+confirmed)\b", re.IGNORECASE),
        # Account statements / surveys / feedback
        re.compile(r"\b(account\s+statement|monthly\s+statement|survey|feedback|rate\s+(?:your|us|the))\b", re.IGNORECASE),
        # Calls / contact (often appear in marketing / scam SMS, not OTPs)
        re.compile(r"\b(call|wp|whatsapp)[\s/]+\d{10,}\b", re.IGNORECASE),
    ]

    # ------------------------------------------------------------------ #

    @classmethod
    def classify(cls, text: str, sender: Optional[str] = None) -> Dict:
        """
        Classify message using heuristics.

        Returns:
            {
              "isOtp": bool,
              "confidence": float in [0.0, 1.0],
              "suggestedIntent": Optional[str],
              "reasons": List[str],
            }
        """
        text = text or ""
        # Pattern matching uses a URL-stripped copy of the body. URLs commonly
        # contain noise like "?CODE=000942700000604" or path segments that
        # collide with our OTP patterns; the recipient never reads the URL
        # query string as an OTP, so we exclude it from signal detection.
        text_no_url = cls.URL_PATTERN.sub(" ", text)
        text_lower = text_no_url.lower()
        sender_upper = (sender or "").upper()
        reasons: List[str] = []

        # ---------------------------------------------------------- #
        # 1. A 4-8 digit code is required (in the non-URL portion).
        # ---------------------------------------------------------- #
        has_code = bool(cls.CODE_PATTERN.search(text_no_url))
        if not has_code:
            return {
                "isOtp": False,
                "confidence": 0.0,
                "suggestedIntent": None,
                "reasons": ["No numeric code found (4-8 digits required)"],
            }
        reasons.append("Numeric code found (4-8 digits)")

        # ---------------------------------------------------------- #
        # 2. Detect positive signals (on URL-stripped text).
        # ---------------------------------------------------------- #
        strong_match = any(p.search(text_no_url) for p in cls.STRONG_OTP_PATTERNS)
        start_code_match = bool(cls.START_CODE_PATTERN.search(text_no_url))
        verification_match = bool(cls.VERIFICATION_CODE_PATTERN.search(text_no_url))
        security_match = bool(cls.SECURITY_CODE_PATTERN.search(text_no_url))

        has_otp_keyword = False
        for keyword in cls.OTP_KEYWORDS:
            if len(keyword.split()) == 1:
                if re.search(rf"\b{re.escape(keyword)}\b", text_no_url, re.IGNORECASE):
                    has_otp_keyword = True
                    break
            elif keyword in text_lower:
                has_otp_keyword = True
                break

        has_otp_phrase = any(phrase in text_lower for phrase in cls.OTP_PHRASES)

        # Any of the above counts as a "real" OTP signal in the body.
        has_body_otp_signal = (
            strong_match or start_code_match or verification_match
            or security_match or has_otp_keyword or has_otp_phrase
        )

        # ---------------------------------------------------------- #
        # 3. NEGATIVE GATE: transaction / marketing / delivery context
        #    blocks OTP classification UNLESS a strong OTP signal is
        #    present in the body.
        # ---------------------------------------------------------- #
        negative_matches = sum(1 for p in cls.NEGATIVE_INDICATORS if p.search(text_no_url))
        if negative_matches > 0 and not has_body_otp_signal:
            return {
                "isOtp": False,
                "confidence": 0.0,
                "suggestedIntent": None,
                "reasons": reasons + [
                    f"Heuristic OTP veto: transaction/marketing/delivery/status context detected "
                    f"({negative_matches} negative indicators) with no strong OTP signal"
                ],
            }

        # ---------------------------------------------------------- #
        # 4. Score positive signals (cumulative max).
        # ---------------------------------------------------------- #
        confidence = 0.0
        is_otp = False

        if strong_match:
            is_otp = True
            confidence = 0.95
            reasons.append("Strong OTP pattern detected")

        if start_code_match:
            is_otp = True
            confidence = max(confidence, 0.90)
            reasons.append("Code at start with OTP context")

        if has_otp_keyword:
            is_otp = True
            confidence = max(confidence, 0.85)
            reasons.append("OTP keyword found")

        if has_otp_phrase:
            is_otp = True
            confidence = max(confidence, 0.80)
            reasons.append("OTP phrase found")

        if verification_match:
            is_otp = True
            confidence = max(confidence, 0.80)
            reasons.append("Verification word with code detected")

        if security_match:
            is_otp = True
            confidence = max(confidence, 0.75)
            reasons.append("Security warning with code detected")

        # ---------------------------------------------------------- #
        # 5. Sender hint REQUIRES at least one body OTP signal.
        #    Bare "ICICI/HDFC/SWIGGY in sender + a 4-8 digit number"
        #    is NOT enough — that's how transaction-alert false positives
        #    used to slip through.
        # ---------------------------------------------------------- #
        sender_matches = any(s in sender_upper for s in cls.OTP_SENDER_PATTERNS)
        if sender_matches and has_body_otp_signal:
            confidence = max(confidence, 0.75)
            reasons.append("Known OTP sender + corroborating body signal")

        # ---------------------------------------------------------- #
        # 6. Multiple-indicator bonus.
        # ---------------------------------------------------------- #
        indicator_count = sum([
            strong_match, start_code_match, has_otp_keyword, has_otp_phrase,
            sender_matches, verification_match, security_match,
        ])
        if is_otp and indicator_count >= 2:
            confidence = min(confidence + 0.05, 0.98)
            reasons.append(f"Multiple OTP indicators ({indicator_count})")

        # ---------------------------------------------------------- #
        # 7. (REMOVED in 2026-05 rewrite) — these caused most of the
        #    false positives in the original classifier:
        #
        #      - "Short message with numeric code" fallback
        #      - "Validity period mentioned" alone fallback
        #      - "Security warning present" alone fallback
        #
        #    If a message lacks any explicit OTP signal AND lacks any
        #    negative indicator, we now defer to the ML model rather
        #    than over-firing.
        # ---------------------------------------------------------- #

        if not is_otp:
            reasons.append("No explicit OTP signal in body")
            return {
                "isOtp": False,
                "confidence": 0.0,
                "suggestedIntent": None,
                "reasons": reasons,
            }

        # ---------------------------------------------------------- #
        # 8. Intent classification (only if is_otp).
        # ---------------------------------------------------------- #
        suggested_intent = cls._detect_intent(text, sender_upper, reasons)

        return {
            "isOtp": is_otp,
            "confidence": confidence,
            "suggestedIntent": suggested_intent,
            "reasons": reasons,
        }

    # ---------------------------------------------------------------- #
    # Intent detection — unchanged from previous version.
    # ---------------------------------------------------------------- #

    @staticmethod
    def _detect_intent(text: str, sender_upper: str, reasons: List[str]) -> Optional[str]:
        """Detect OTP intent from message content."""
        if (re.search(r"\b(delivery|deliver|courier|package|order|shipment|tracking|logistics)\b",
                      text, re.IGNORECASE)
                or any(s in sender_upper for s in ["SWIGGY", "ZOMATO", "DELHIVERY", "BLUEDART",
                                                    "XPBEES", "XPRESSBEES", "ECOM", "DUNZO"])):
            reasons.append("Intent: DELIVERY_OR_SERVICE_OTP")
            return "DELIVERY_OR_SERVICE_OTP"

        if (re.search(r"\b(bank|card|transaction|payment|transfer|debit|credit)\b",
                      text, re.IGNORECASE)
                or any(s in sender_upper for s in ["BANK", "ICICI", "HDFC", "SBI", "AXIS"])):
            reasons.append("Intent: BANK_OR_CARD_TXN_OTP")
            return "BANK_OR_CARD_TXN_OTP"

        if (re.search(r"\b(upi|unified payments|pin|device.*link|link.*device)\b",
                      text, re.IGNORECASE)
                or any(s in sender_upper for s in ["UPI", "PHONEPE", "GPAY", "PAYTM", "BHIM"])):
            reasons.append("Intent: UPI_TXN_OR_PIN_OTP")
            return "UPI_TXN_OR_PIN_OTP"

        if re.search(r"\b(password.*reset|change.*password|update.*profile|change.*phone|"
                     r"change.*email|account.*change|new\s+phone\s+number|"
                     r"phone\s+number\s+(?:change|verify|verification)|change\s+number)\b",
                     text, re.IGNORECASE):
            reasons.append("Intent: APP_ACCOUNT_CHANGE_OTP")
            return "APP_ACCOUNT_CHANGE_OTP"

        if re.search(r"\b(login|sign.?in|access|verify.?account|authenticate)\b",
                     text, re.IGNORECASE):
            reasons.append("Intent: APP_LOGIN_OTP")
            return "APP_LOGIN_OTP"

        if re.search(r"\b(kyc|know.*customer|e.?sign|esign|document.*sign)\b",
                     text, re.IGNORECASE):
            reasons.append("Intent: KYC_OR_ESIGN_OTP")
            return "KYC_OR_ESIGN_OTP"

        reasons.append("Intent: GENERIC_APP_ACTION_OTP (default)")
        return "GENERIC_APP_ACTION_OTP"

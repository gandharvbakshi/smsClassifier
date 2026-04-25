package com.smsclassifier.app.classification

import java.util.regex.Pattern

/**
 * Heuristic-based OTP classifier. The goal is HIGH PRECISION: when we say it's an
 * OTP, it really should be one. We accept slightly lower recall (some real OTPs may
 * fall through to the ML model) in exchange for far fewer false positives, since
 * the previous version was over-firing on marketing / transaction / order
 * notifications that just happened to contain a 4-8 digit number.
 */
object HeuristicOtpClassifier {

    // -- Required: a 4-8 digit numeric code somewhere in the body.
    private val CODE_PATTERN = Pattern.compile("(?<![\\d])\\d{4,8}(?![\\d])")

    // -- Strong OTP keywords. These almost guarantee OTP intent.
    //    NOTE: kept as word-boundary regexes so "voted" doesn't match "vot".
    private val OTP_STRONG_KEYWORDS = listOf(
        "\\botp\\b",
        "\\bo\\.t\\.p\\b",
        "\\bone[\\s-]?time[\\s-]?(password|passcode|pin|code)\\b",
        "\\bverification\\s+(code|pin|number)\\b",
        "\\bauthenti(cation|cator)\\s+code\\b",
        "\\bsecurity\\s+code\\b",
        "\\baccess\\s+code\\b",
        "\\blogin\\s+code\\b",
        "\\bsign[\\s-]?in\\s+code\\b",
        "\\bconfirmation\\s+code\\b",
        "\\bverify\\s+(?:your\\s+)?(?:account|identity|number|email|phone|mobile)\\b"
    ).map { Pattern.compile(it, Pattern.CASE_INSENSITIVE) }

    // -- Weaker indicators that count only when paired with a code AND nothing
    //    obviously *non*-OTP (transaction, marketing) appears.
    private val OTP_WEAK_KEYWORDS = listOf(
        "\\b(?:your\\s+)?code\\s+is\\b",
        "\\buse\\s+code\\b",
        "\\benter\\s+code\\b",
        "\\bvalid\\s+for\\s+\\d+\\s+(?:min|minute|sec|second|hour)s?\\b",
        "\\bdo\\s+not\\s+share\\b",
        "\\bdon'?t\\s+share\\b",
        "\\bnever\\s+share\\b",
        "\\bkeep\\s+(?:it|this)\\s+(?:secret|confidential|private)\\b"
    ).map { Pattern.compile(it, Pattern.CASE_INSENSITIVE) }

    // -- Hard NEGATIVE indicators. If any of these match, it is almost certainly
    //    NOT an OTP — these are transaction, marketing, order, bill messages that
    //    used to confuse us.
    private val NEGATIVE_INDICATORS = listOf(
        // Money in/out
        "\\b(debited|credited|debit|credit|withdrawn|deposited|received\\s+rs|sent\\s+rs)\\b",
        "\\b(?:rs\\.?|inr|usd|eur|gbp|\\$|₹)\\s*\\d",
        "\\b\\d+\\s*(?:rs\\.?|inr|usd|eur|gbp|₹)\\b",
        // Bank balance
        "\\b(avl|available|closing|opening)\\s+(bal|balance)\\b",
        // Bills / EMI / due
        "\\b(bill|emi|due|overdue|payment\\s+due|outstanding)\\b",
        // Shipping / delivery / order tracking (without OTP context)
        "\\b(out\\s+for\\s+delivery|delivered|shipped|dispatched|track\\s+(?:your\\s+)?order|tracking\\s+(?:id|number))\\b",
        "\\border\\s+#?\\d+\\s+(?:has\\s+been|is\\s+)?(?:placed|confirmed|cancelled|shipped|delivered)",
        // Promotional / offers
        "\\b(offer|sale|discount|coupon|cashback|reward|win|congratulations|free)\\b",
        // Recharge / data
        "\\b(recharge|data\\s+pack|talktime|validity\\s+upto)\\b",
        // Appointments / reminders not security
        "\\b(appointment|booking|reservation)\\s+(?:confirmed|scheduled)\\b"
    ).map { Pattern.compile(it, Pattern.CASE_INSENSITIVE) }

    // -- Phishing red flags that should reduce OTP confidence (legit OTP messages
    //    rarely contain links).
    private val PHISH_LINK_PATTERN = Pattern.compile(
        "https?://|www\\.|\\bbit\\.ly\\b|\\btinyurl\\b",
        Pattern.CASE_INSENSITIVE
    )

    // -- Sender hints. DLT-registered IDs in India look like XX-SENDER, AX-SENDER,
    //    JD-VKAUTH, etc. (6-char headers). Numeric senders alone are not enough.
    private val OTP_SENDER_HINTS = listOf(
        "OTP", "AUTH", "VERIFY", "ALRT", "BANK", "ICICI", "HDFC", "SBI", "AXIS",
        "KOTAK", "YESBNK", "IDFCBK", "INDUSB", "CITI", "AMEX", "AMZN", "AMAZON",
        "FLIPKART", "PAYTM", "PHONEPE", "GPAY", "GOOGLE", "GOOG", "MICROSOFT",
        "MSFT", "META", "FBOOK", "WHATSAPP", "WA", "TELEGRAM", "TG", "INSTA",
        "TWITTER", "LNKD", "LINKD", "SWIGGY", "ZOMATO", "UBER", "OLA", "MMT",
        "MAKEMYT", "GOIBIBO", "OYO"
    )

    data class HeuristicResult(
        val isOtp: Boolean,
        val confidence: Float,
        val suggestedIntent: String?,
        val reasons: List<String>
    )

    fun classify(text: String, sender: String? = null): HeuristicResult {
        val reasons = mutableListOf<String>()
        val senderUpper = sender?.uppercase().orEmpty()

        // Code is required.
        val codeMatch = CODE_PATTERN.matcher(text)
        if (!codeMatch.find()) {
            return HeuristicResult(
                isOtp = false,
                confidence = 0f,
                suggestedIntent = null,
                reasons = listOf("No 4-8 digit numeric code found")
            )
        }
        reasons.add("Numeric code detected")

        // Hard negatives: if we see clearly non-OTP context (transaction, bill,
        // delivery confirmation, marketing), treat it as NOT an OTP unless the
        // text ALSO contains a strong OTP keyword. Many transaction notifications
        // are formatted as "Rs. 1234 credited to your A/C XXX1234" — the "1234"
        // would have been a false positive previously.
        val negativeMatches = NEGATIVE_INDICATORS.count { it.matcher(text).find() }
        val strongMatches = OTP_STRONG_KEYWORDS.count { it.matcher(text).find() }
        val weakMatches = OTP_WEAK_KEYWORDS.count { it.matcher(text).find() }

        if (negativeMatches > 0 && strongMatches == 0) {
            return HeuristicResult(
                isOtp = false,
                confidence = 0f,
                suggestedIntent = null,
                reasons = reasons + "Transaction/marketing context detected (no strong OTP keyword)"
            )
        }

        var confidence = 0f
        var isOtp = false

        if (strongMatches > 0) {
            isOtp = true
            confidence = 0.95f
            reasons.add("Strong OTP keyword(s): $strongMatches")
        } else if (weakMatches >= 2) {
            // E.g. "code is" + "do not share" + 4-digit code, but no explicit "OTP".
            isOtp = true
            confidence = 0.80f
            reasons.add("Multiple OTP-style cues: $weakMatches")
        } else if (weakMatches == 1 && senderHints(senderUpper)) {
            isOtp = true
            confidence = 0.75f
            reasons.add("OTP-style cue + recognised sender")
        } else if (strongMatches == 0 && weakMatches == 0 && senderHints(senderUpper) && text.length < 80) {
            // Very short message from known OTP sender — keep but lower confidence.
            isOtp = true
            confidence = 0.55f
            reasons.add("Short message from known OTP sender")
        }

        if (!isOtp) {
            reasons.add("Insufficient OTP context")
            return HeuristicResult(false, 0f, null, reasons)
        }

        // Penalise if the message contains a link (real banks/apps rarely send
        // OTPs with links; if there is one this is more likely phishing or a
        // marketing message dressed up like OTP).
        if (PHISH_LINK_PATTERN.matcher(text).find()) {
            confidence *= 0.6f
            reasons.add("Contains link — reduced confidence")
        }

        val intent = detectIntent(text, senderUpper, reasons)

        return HeuristicResult(
            isOtp = true,
            confidence = confidence.coerceIn(0f, 1f),
            suggestedIntent = intent,
            reasons = reasons
        )
    }

    private fun senderHints(senderUpper: String): Boolean {
        if (senderUpper.isEmpty()) return false
        return OTP_SENDER_HINTS.any { senderUpper.contains(it) }
    }

    private fun detectIntent(text: String, senderUpper: String, reasons: MutableList<String>): String {
        val t = text.lowercase()

        fun mark(intent: String): String {
            reasons.add("Intent: $intent")
            return intent
        }

        if (Regex("\\b(upi|vpa|bhim|unified payments|upi pin|set\\s+upi)\\b").containsMatchIn(t) ||
            senderUpper.contains("UPI") || senderUpper.contains("BHIM")
        ) return mark("UPI_TXN_OR_PIN_OTP")

        if (Regex("\\b(bank|debit\\s+card|credit\\s+card|net\\s+banking|transaction|transfer|imps|neft|rtgs)\\b")
                .containsMatchIn(t) ||
            listOf("ICICI", "HDFC", "SBI", "AXIS", "KOTAK", "YESBNK", "IDFCBK", "INDUSB", "CITI", "AMEX")
                .any { senderUpper.contains(it) }
        ) return mark("BANK_OR_CARD_TXN_OTP")

        if (Regex("\\b(login|sign[\\s-]?in)\\b").containsMatchIn(t) &&
            Regex("\\b(net\\s*banking|account|wallet|portal)\\b").containsMatchIn(t)
        ) return mark("FINANCIAL_LOGIN_OTP")

        if (Regex("\\b(delivery|courier|package|parcel|shipment|otp\\s+for\\s+delivery|delivery\\s+otp|delivery\\s+person)\\b")
                .containsMatchIn(t) ||
            listOf("SWIGGY", "ZOMATO", "DELHIVERY", "BLUEDART", "ECOM", "XPRESSBEES", "DUNZO")
                .any { senderUpper.contains(it) }
        ) return mark("DELIVERY_OR_SERVICE_OTP")

        if (Regex("\\b(reset|change|update)\\s+(?:your\\s+)?(?:password|email|phone|number|profile)\\b")
                .containsMatchIn(t)
        ) return mark("APP_ACCOUNT_CHANGE_OTP")

        if (Regex("\\bkyc|e[\\s-]?sign|esign|aadhaar|aadhar\\b").containsMatchIn(t))
            return mark("KYC_OR_ESIGN_OTP")

        if (Regex("\\blog[\\s-]?in|sign[\\s-]?in|verify\\b").containsMatchIn(t))
            return mark("APP_LOGIN_OTP")

        return mark("GENERIC_APP_ACTION_OTP")
    }
}

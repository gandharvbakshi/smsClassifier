package com.smsclassifier.app.classification

import com.smsclassifier.app.util.AppLog
import java.util.regex.Pattern

/**
 * Heuristic-based OTP classifier that uses pattern matching to quickly identify OTP messages.
 * This runs before ML models for faster classification of common OTP patterns.
 */
object HeuristicOtpClassifier {
    
    // OTP keywords - case insensitive
    private val OTP_KEYWORDS = listOf(
        "otp",
        "verification code",
        "authentication code",
        "your code",
        "one time password",
        "verification pin",
        "access code",
        "security code",
        "password code",
        "login code",
        "verification",
        "authenticate"
    )
    
    // Common OTP phrases
    private val OTP_PHRASES = listOf(
        "is your",
        "code is",
        "verify with",
        "use code",
        "enter code",
        "use otp",
        "your otp",
        "otp is",
        "code to",
        "verification code is",
        "your verification",
        "verification code",
        "login code is"
    )
    
    // Security warning indicators
    private val SECURITY_WARNINGS = listOf(
        "do not share", "don't share", "keep secret",
        "confidential", "never share", "do not disclose", "keep it safe",
        "don't reveal", "never reveal"
    )
    
    // Validity period indicators
    private val VALIDITY_WORDS = listOf(
        "valid", "validity", "expires", "expiry", "minutes", "min",
        "seconds", "sec", "valid for", "expires in"
    )
    
    // Known OTP sender patterns (short codes, common services)
    private val OTP_SENDER_PATTERNS = listOf(
        "BANK", "PAYTM", "PHONEPE", "GPAY", "SWIGGY", "ZOMATO",
        "AMAZON", "FLIPKART", "ICICI", "HDFC", "SBI", "AXIS",
        "OTP", "VERIFY", "CODE", "AUTH"
    )
    
    // Numeric code pattern: 4-8 digits
    private val CODE_PATTERN = Pattern.compile("\\b\\d{4,8}\\b")
    
    // Strong OTP indicators (high confidence)
    private val STRONG_OTP_PATTERNS = listOf(
        Pattern.compile("\\b(otp|one.?time.?password)\\b.*?\\b\\d{4,8}\\b", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\b\\d{4,8}\\b.*?(otp|code|verification)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(your|use|enter).*?(otp|code).*?\\b\\d{4,8}\\b", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\b\\d{4,8}\\b.*?(is|as).*?(your|the).*?(otp|code|password)", Pattern.CASE_INSENSITIVE)
    )
    
    // Code at start pattern
    private val START_CODE_PATTERN = Pattern.compile(
        "^\\b\\d{4,8}\\b\\s*(?:is|for|your|use|enter|verification|code|otp|password)",
        Pattern.CASE_INSENSITIVE
    )
    
    // Verification words with code pattern
    private val VERIFICATION_CODE_PATTERN = Pattern.compile(
        "(?:verify|verification|authenticate|login|sign.?in).*?\\b\\d{4,8}\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    // Security warning with code pattern
    private val SECURITY_CODE_PATTERN = Pattern.compile(
        "(?:do\\s+not\\s+share|don'?t\\s+share|keep\\s+secret|confidential|never\\s+share).*?\\b\\d{4,8}\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    // Intent detection patterns
    private val DELIVERY_INTENT_PATTERN = Pattern.compile(
        "\\b(delivery|deliver|courier|package|order|shipment|tracking|logistics)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    private val BANK_TXN_INTENT_PATTERN = Pattern.compile(
        "\\b(bank|card|transaction|payment|transfer|upi|debit|credit)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    private val LOGIN_INTENT_PATTERN = Pattern.compile(
        "\\b(login|sign.?in|access|verify.?account|authenticate)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    private val APP_ACCOUNT_CHANGE_PATTERN = Pattern.compile(
        "\\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|account.*change)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    private val UPI_PATTERN = Pattern.compile(
        "\\b(upi|unified payments|pin|device.*link|link.*device)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    private val KYC_PATTERN = Pattern.compile(
        "\\b(kyc|know.*customer|e.?sign|esign|document.*sign)\\b",
        Pattern.CASE_INSENSITIVE
    )
    
    data class HeuristicResult(
        val isOtp: Boolean,
        val confidence: Float, // 0.0 to 1.0
        val suggestedIntent: String?,
        val reasons: List<String>
    )
    
    /**
     * Classify message using heuristics first.
     * Returns result with confidence score.
     */
    fun classify(text: String, sender: String? = null): HeuristicResult {
        val textLower = text.lowercase()
        val senderUpper = sender?.uppercase() ?: ""
        val reasons = mutableListOf<String>()
        var confidence = 0.0f
        var isOtp = false
        var suggestedIntent: String? = null
        
        // Check for numeric code (required for OTP)
        val hasCode = CODE_PATTERN.matcher(text).find()
        if (!hasCode) {
            return HeuristicResult(
                isOtp = false,
                confidence = 0.0f,
                suggestedIntent = null,
                reasons = listOf("No numeric code found (4-8 digits required)")
            )
        }
        reasons.add("Numeric code found (4-8 digits)")
        
        // Check for strong OTP patterns (high confidence)
        val strongMatch = STRONG_OTP_PATTERNS.any { pattern ->
            pattern.matcher(text).find()
        }
        if (strongMatch) {
            isOtp = true
            confidence = 0.95f
            reasons.add("Strong OTP pattern detected")
        }
        
        // Check for code at start pattern
        val startCodeMatch = START_CODE_PATTERN.matcher(text).find()
        if (startCodeMatch) {
            isOtp = true
            confidence = maxOf(confidence, 0.90f)
            reasons.add("Code at start with OTP context")
        }
        
        // Check for OTP keywords (improved: use word boundaries)
        val hasOtpKeyword = OTP_KEYWORDS.any { keyword ->
            if (keyword.split(" ").size == 1) {
                // Single word - use word boundary
                Pattern.compile("\\b${Pattern.quote(keyword)}\\b", Pattern.CASE_INSENSITIVE)
                    .matcher(text).find()
            } else {
                // Phrase - use substring
                textLower.contains(keyword)
            }
        }
        if (hasOtpKeyword) {
            isOtp = true
            confidence = maxOf(confidence, 0.85f)
            reasons.add("OTP keyword found")
        }
        
        // Check for OTP phrases
        val hasOtpPhrase = OTP_PHRASES.any { phrase ->
            textLower.contains(phrase)
        }
        if (hasOtpPhrase && hasCode) {
            isOtp = true
            confidence = maxOf(confidence, 0.80f)
            reasons.add("OTP phrase found")
        }
        
        // Check for verification words with code
        val verificationMatch = VERIFICATION_CODE_PATTERN.matcher(text).find()
        if (verificationMatch) {
            isOtp = true
            confidence = maxOf(confidence, 0.80f)
            reasons.add("Verification word with code detected")
        }
        
        // Check for security warnings with code
        val securityMatch = SECURITY_CODE_PATTERN.matcher(text).find()
        if (securityMatch) {
            isOtp = true
            confidence = maxOf(confidence, 0.75f)
            reasons.add("Security warning with code detected")
        }
        
        // Check sender patterns
        val senderMatches = OTP_SENDER_PATTERNS.any { pattern ->
            senderUpper.contains(pattern)
        }
        if (senderMatches && hasCode) {
            isOtp = true
            confidence = maxOf(confidence, 0.75f)
            reasons.add("Known OTP sender pattern")
        }
        
        // Check for validity period indicators
        val hasValidity = VALIDITY_WORDS.any { word ->
            textLower.contains(word)
        }
        if (hasValidity && hasCode && !isOtp) {
            isOtp = true
            confidence = maxOf(confidence, 0.70f)
            reasons.add("Validity period mentioned")
        }
        
        // Check for security warnings as additional indicator
        val hasSecurityWarning = SECURITY_WARNINGS.any { warning ->
            textLower.contains(warning)
        }
        if (hasSecurityWarning && hasCode && !isOtp) {
            isOtp = true
            confidence = maxOf(confidence, 0.75f)
            reasons.add("Security warning present")
        }
        
        // Additional confidence boost if multiple indicators present
        val indicatorCount = listOf(
            strongMatch,
            startCodeMatch,
            hasOtpKeyword,
            hasOtpPhrase,
            senderMatches,
            verificationMatch,
            securityMatch,
            hasValidity,
            hasSecurityWarning
        ).count { it }
        
        if (indicatorCount >= 2) {
            confidence = minOf(confidence + 0.05f, 0.98f)
            reasons.add("Multiple OTP indicators ($indicatorCount)")
        }
        
        // If we have code but low confidence indicators, still classify as OTP but with lower confidence
        if (hasCode && !isOtp) {
            // Check if message is short (typical for OTPs) - lowered threshold
            if (text.length < 100) {
                isOtp = true
                confidence = 0.60f
                reasons.add("Short message with numeric code (possible OTP)")
            } else if (text.length < 150) {
                isOtp = true
                confidence = 0.55f
                reasons.add("Medium-length message with numeric code (possible OTP)")
            }
        }
        
        // Determine intent if it's an OTP
        if (isOtp) {
            suggestedIntent = detectIntent(text, senderUpper, reasons)
        }
        
        // Reduce confidence if phishing indicators present
        if (containsPhishingIndicators(text)) {
            confidence *= 0.7f
            reasons.add("Phishing indicators present (reduced confidence)")
        }
        
        return HeuristicResult(
            isOtp = isOtp,
            confidence = confidence,
            suggestedIntent = suggestedIntent,
            reasons = reasons
        )
    }
    
    private fun detectIntent(text: String, senderUpper: String, reasons: MutableList<String>): String {
        // Check for delivery/service intent
        if (DELIVERY_INTENT_PATTERN.matcher(text).find() || 
            senderUpper.contains("SWIGGY") || senderUpper.contains("ZOMATO") ||
            senderUpper.contains("DELHIVERY") || senderUpper.contains("BLUEDART")) {
            reasons.add("Intent: DELIVERY_OR_SERVICE_OTP")
            return "DELIVERY_OR_SERVICE_OTP"
        }
        
        // Check for bank/card transaction intent
        if (BANK_TXN_INTENT_PATTERN.matcher(text).find() ||
            senderUpper.contains("BANK") || senderUpper.contains("ICICI") ||
            senderUpper.contains("HDFC") || senderUpper.contains("SBI") ||
            senderUpper.contains("AXIS")) {
            reasons.add("Intent: BANK_OR_CARD_TXN_OTP")
            return "BANK_OR_CARD_TXN_OTP"
        }
        
        // Check for UPI intent
        if (UPI_PATTERN.matcher(text).find() ||
            senderUpper.contains("UPI") || senderUpper.contains("PHONEPE") ||
            senderUpper.contains("GPAY") || senderUpper.contains("PAYTM")) {
            reasons.add("Intent: UPI_TXN_OR_PIN_OTP")
            return "UPI_TXN_OR_PIN_OTP"
        }
        
        // Check for app account change intent
        if (APP_ACCOUNT_CHANGE_PATTERN.matcher(text).find()) {
            reasons.add("Intent: APP_ACCOUNT_CHANGE_OTP")
            return "APP_ACCOUNT_CHANGE_OTP"
        }
        
        // Check for login intent
        if (LOGIN_INTENT_PATTERN.matcher(text).find()) {
            reasons.add("Intent: APP_LOGIN_OTP")
            return "APP_LOGIN_OTP"
        }
        
        // Check for KYC intent
        if (KYC_PATTERN.matcher(text).find()) {
            reasons.add("Intent: KYC_OR_ESIGN_OTP")
            return "KYC_OR_ESIGN_OTP"
        }
        
        // Default to generic app action
        reasons.add("Intent: GENERIC_APP_ACTION_OTP (default)")
        return "GENERIC_APP_ACTION_OTP"
    }
    
    private fun containsPhishingIndicators(text: String): Boolean {
        val phishingPatterns = listOf(
            Pattern.compile("http://|https://|www\\."), // URLs
            Pattern.compile("click.*here|verify.*link"), // Click here phrases
            Pattern.compile("urgent|immediately|act.*now"), // Urgency
            Pattern.compile("reward|win|cashback|lottery") // Too good to be true
        )
        return phishingPatterns.any { it.matcher(text.lowercase()).find() }
    }
}


package com.smsclassifier.app.classification

import android.content.Context
import com.smsclassifier.app.util.AppLog
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.util.regex.Pattern

@Serializable
data class FeatureVocab(
    val vocab: Map<String, Int>,
    val heuristicFeatureCount: Int = 23
)

class FeatureExtractor(private val context: Context) {
    private var vocab: Map<String, Int>? = null
    private val vocabSize: Int
        get() = vocab?.size ?: 0

    init {
        loadVocab()
    }

    private fun loadVocab() {
        try {
            val json = context.assets.open("feature_map.json").bufferedReader().use { it.readText() }
            val featureVocab = Json.decodeFromString<FeatureVocab>(json)
            vocab = featureVocab.vocab
            AppLog.d("FeatureExtractor", "Loaded vocab with ${vocab?.size} terms")
        } catch (e: Exception) {
            AppLog.e("FeatureExtractor", "Failed to load vocab", e)
        }
    }

    fun extractHeuristicFeatures(text: String, sender: String? = null): FloatArray {
        val senderUpper = sender?.uppercase() ?: ""

        val features = mutableListOf<Float>()

        // Pattern-based features (matching training script)
        features.add(if (Pattern.compile("\\d").matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\bOTP\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("do not share|never share", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("https?://|www\\.").matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\blogin\\b|\\bverify\\b|\\bupdate\\b|\\bclick\\b|\\bcall\\b|\\bshare\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("bank never asks|otp is secret|do not disclose", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("sms block 7007", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("reward|win|cashback|lottery|prize|gift", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(social|entertainment|streaming|gaming|shopping|app login|account login)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(delivery|deliver|courier|package|order|shipment|tracking|OTP.*delivery|share.*code.*delivery)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(UPI|unified payments|PIN|device.*link|link.*device|bind.*device)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(KYC|know your customer|e-sign|esign|document.*sign|verification.*document)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|update.*contact)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(one time password|OTP|verification code|authentication code|this is your.*code|your.*code is|give.*code|share.*code|delivery code)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(INR|Rs\\.?|₹)\\s*\\d+[.,]?\\d*\\b").matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(XX\\d+|xxxx\\d+|card.*XX|account.*XX)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(urgent|immediately|act now|expires.*soon|limited time|verify now)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(bit\\.ly|tinyurl|short\\.link|click.*here|verify.*link)\\b", Pattern.CASE_INSENSITIVE).matcher(text).find()) 1f else 0f)

        // Sender-based features
        features.add(if (Pattern.compile("\\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\\b").matcher(senderUpper).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\\b").matcher(senderUpper).find()) 1f else 0f)
        features.add(if (Pattern.compile("\\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\\b").matcher(senderUpper).find()) 1f else 0f)
        features.add(if (Pattern.compile("^\\d{10,12}$").matcher(senderUpper).find()) 1f else 0f)

        return features.toFloatArray()
    }

    fun extractTfIdfVector(text: String): FloatArray {
        val vocab = this.vocab ?: return FloatArray(0)
        val textLower = text.lowercase()
        val words = textLower.split(Regex("\\s+"))
        
        // Simple TF-IDF: just use term frequency for now
        // In production, you'd want to load the actual IDF values
        val vector = FloatArray(vocabSize) { 0f }
        
        words.forEach { word ->
            vocab[word]?.let { index ->
                vector[index] += 1f
            }
        }
        
        // Normalize
        val sum = vector.sum()
        if (sum > 0) {
            for (i in vector.indices) {
                vector[i] /= sum
            }
        }
        
        return vector
    }

    fun extractFeatures(text: String, sender: String? = null): MessageFeatures {
        // Handle edge cases
        val sanitizedText = sanitizeText(text)
        
        val tfidfVector = extractTfIdfVector(sanitizedText)
        val heuristicFeatures = extractHeuristicFeatures(sanitizedText, sender)
        
        return MessageFeatures(
            text = sanitizedText,
            sender = sender,
            tfidfVector = tfidfVector,
            heuristicFeatures = heuristicFeatures
        )
    }
    
    /**
     * Sanitize text to handle edge cases:
     * - Empty messages
     * - Very long messages (truncate)
     * - Emoji-only messages
     * - Whitespace-only messages
     */
    private fun sanitizeText(text: String): String {
        if (text.isBlank()) {
            return ""
        }
        
        // Trim whitespace
        var sanitized = text.trim()
        
        // Handle very long messages (SMS max is ~160 chars, but concatenated SMS can be longer)
        // Limit to reasonable length for feature extraction (1000 chars)
        if (sanitized.length > 1000) {
            AppLog.w("FeatureExtractor", "Message too long (${sanitized.length} chars), truncating to 1000 chars")
            sanitized = sanitized.take(1000)
        }
        
        // Check if message is emoji-only (after removing whitespace)
        val textWithoutWhitespace = sanitized.replace(Regex("\\s"), "")
        if (textWithoutWhitespace.isNotEmpty() && textWithoutWhitespace.all { 
            it.isEmoji() || Character.getType(it) == Character.SURROGATE.toInt() 
        }) {
            // Emoji-only message - keep as is, features will be minimal
            AppLog.d("FeatureExtractor", "Detected emoji-only message")
        }
        
        return sanitized
    }
    
    /**
     * Check if a character is an emoji.
     * Simple check - Unicode ranges for common emoji blocks.
     */
    private fun Char.isEmoji(): Boolean {
        val codePoint = this.code
        return (codePoint in 0x1F300..0x1F9FF) ||  // Misc Symbols and Pictographs
               (codePoint in 0x1F600..0x1F64F) ||  // Emoticons
               (codePoint in 0x1F680..0x1F6FF) ||  // Transport and Map
               (codePoint in 0x2600..0x26FF) ||    // Misc symbols
               (codePoint in 0x2700..0x27BF)       // Dingbats
    }
}


package com.smsclassifier.app.util

/**
 * Resolves Indian transactional/promotional SMS sender IDs to friendly brand names.
 *
 * Input examples → output:
 *   "VD-HSBCIN-S"  → "HSBC"
 *   "VM-ICICIT-S"  → "ICICI Bank"
 *   "AX-ICICIT-S"  → "ICICI Bank"
 *   "JD-AMAZON-S"  → "Amazon"
 *   "VM-ICICIT-S1" → "ICICI Bank"
 *   "+919876543210" → "+91 98765 43210"
 *   "John"         → "John"  (already friendly)
 */
object SenderNameResolver {

    // Known brand mappings. Keys are uppercase, after route prefix/suffix stripped.
    private val brandMap: Map<String, String> = mapOf(
        "HSBCIN" to "HSBC",
        "HSBC" to "HSBC",
        "ICICIT" to "ICICI Bank",
        "ICICIB" to "ICICI Bank",
        "ICICI" to "ICICI Bank",
        "SBIINB" to "SBI",
        "SBIPSG" to "SBI",
        "SBI" to "SBI",
        "HDFCBK" to "HDFC Bank",
        "HDFC" to "HDFC Bank",
        "AXISBK" to "Axis Bank",
        "AXIS" to "Axis Bank",
        "KOTAKB" to "Kotak Bank",
        "KOTAK" to "Kotak Bank",
        "PAYTM" to "Paytm",
        "PHONPE" to "PhonePe",
        "GPAY" to "Google Pay",
        "AMAZON" to "Amazon",
        "FLPKRT" to "Flipkart",
        "MYNTRA" to "Myntra",
        "SWIGGY" to "Swiggy",
        "ZOMATO" to "Zomato",
        "UBER" to "Uber",
        "OLA" to "Ola",
        "JIO" to "Jio",
        "AIRTEL" to "Airtel",
        "VI" to "Vi",
        "BSNL" to "BSNL"
    )

    // Common Indian DLT route prefixes (2 letters, then dash)
    private val routePrefixes = setOf(
        "VD", "VM", "VK", "AX", "AD", "JD", "JM", "JK",
        "BP", "BT", "BX", "BV", "TX", "DM", "MD", "PM", "PD"
    )

    fun resolve(rawSender: String): String {
        if (rawSender.isBlank()) return rawSender

        // Phone numbers: format with spaces for readability
        if (rawSender.startsWith("+") || rawSender.all { it.isDigit() || it == '+' || it == ' ' }) {
            return formatPhoneNumber(rawSender)
        }

        // Already a human name (contains lowercase letters or spaces)
        if (rawSender.any { it.isLowerCase() } || rawSender.contains(' ')) {
            return rawSender
        }

        // Strip Indian DLT format: <2-char-route>-<brand>-<entity>
        var core = rawSender.uppercase()

        // Strip leading route prefix like "VD-" / "AX-"
        val firstDash = core.indexOf('-')
        if (firstDash == 2 && core.substring(0, 2) in routePrefixes) {
            core = core.substring(firstDash + 1)
        }

        // Strip trailing entity suffix like "-S" / "-P" / "-T" / "-G" and numeric variants.
        core = core.replace(Regex("-(?:[A-Z]{1,4}\\d*|\\d+)$"), "")

        // Strip any trailing numeric entity/route suffix such as "S1" / "1234"
        core = core.replace(Regex("\\d+$"), "")

        // Look up known brand; otherwise return cleaned-up core
        return brandMap[core] ?: core
    }

    private fun formatPhoneNumber(number: String): String {
        val digits = number.filter { it.isDigit() }
        return when {
            number.startsWith("+91") && digits.length == 12 ->
                "+91 ${digits.substring(2, 7)} ${digits.substring(7)}"
            digits.length == 10 ->
                "${digits.substring(0, 5)} ${digits.substring(5)}"
            else -> number
        }
    }
}

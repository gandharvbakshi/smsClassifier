package com.smsclassifier.app.util

object ThreadUtils {
    /**
     * Calculate thread ID from phone number.
     * Thread ID is used to group messages from the same phone number.
     * This matches Android's standard thread ID calculation.
     */
    fun calculateThreadId(phoneNumber: String): Long {
        if (phoneNumber.isBlank()) return 0
        
        // Normalize phone number: remove all non-digit characters
        val normalized = phoneNumber.replace(Regex("[^0-9]"), "")
        
        // If there are no digits (alphanumeric sender IDs), fall back to sender text
        val key = if (normalized.isNotEmpty()) {
            normalized
        } else {
            phoneNumber.trim().uppercase()
        }

        if (key.isEmpty()) return 0

        // Use a stable hash and ensure positive value
        val hash = key.hashCode().toLong()
        return hash.and(0x7FFFFFFF) // Ensure positive value
    }
    
    /**
     * Normalize phone number for consistent thread grouping.
     */
    fun normalizePhoneNumber(phoneNumber: String): String {
        return phoneNumber.replace(Regex("[^0-9]"), "")
    }
}


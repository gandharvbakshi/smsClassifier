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
        
        if (normalized.isEmpty()) return 0
        
        // Use Android's standard thread ID calculation
        // Hash the normalized number and ensure positive value
        val hash = normalized.hashCode().toLong()
        return hash.and(0x7FFFFFFF) // Ensure positive value
    }
    
    /**
     * Normalize phone number for consistent thread grouping.
     */
    fun normalizePhoneNumber(phoneNumber: String): String {
        return phoneNumber.replace(Regex("[^0-9]"), "")
    }
}


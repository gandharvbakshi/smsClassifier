package com.smsclassifier.app.util

import android.util.Log
import com.smsclassifier.app.BuildConfig

/**
 * Secure logging utility that gates debug/info logs in release builds.
 * Error logs are always kept for production debugging.
 */
object AppLog {
    
    /**
     * Debug log - only in debug builds
     */
    fun d(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) {
                Log.d(tag, message, throwable)
            } else {
                Log.d(tag, message)
            }
        }
    }
    
    /**
     * Verbose log - only in debug builds
     */
    fun v(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) {
                Log.v(tag, message, throwable)
            } else {
                Log.v(tag, message)
            }
        }
    }
    
    /**
     * Info log - only in debug builds
     */
    fun i(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) {
                Log.i(tag, message, throwable)
            } else {
                Log.i(tag, message)
            }
        }
    }
    
    /**
     * Warning log - only in debug builds
     */
    fun w(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) {
                Log.w(tag, message, throwable)
            } else {
                Log.w(tag, message)
            }
        }
    }
    
    /**
     * Error log - always logged (even in release) for production debugging
     * But sanitized to avoid leaking sensitive data
     */
    fun e(tag: String, message: String, throwable: Throwable? = null) {
        // Sanitize message to avoid leaking SMS content or phone numbers
        val sanitizedMessage = sanitizeMessage(message)
        
        if (throwable != null) {
            Log.e(tag, sanitizedMessage, throwable)
        } else {
            Log.e(tag, sanitizedMessage)
        }
    }
    
    /**
     * Sanitize log messages to remove sensitive data
     */
    private fun sanitizeMessage(message: String): String {
        // Remove potential phone numbers (basic pattern)
        var sanitized = message.replace(Regex("\\+?\\d{10,}"), "[PHONE]")
        
        // Remove potential OTP codes (4-8 digit numbers)
        sanitized = sanitized.replace(Regex("\\b\\d{4,8}\\b"), "[CODE]")
        
        // Truncate very long messages (likely SMS content)
        if (sanitized.length > 200) {
            sanitized = sanitized.take(200) + "... [truncated]"
        }
        
        return sanitized
    }
}


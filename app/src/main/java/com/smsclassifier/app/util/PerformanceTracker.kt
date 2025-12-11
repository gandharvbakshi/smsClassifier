package com.smsclassifier.app.util

import android.content.Context
import android.content.SharedPreferences
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * Tracks backend API performance metrics including latency.
 */
object PerformanceTracker {
    private const val PREFS_NAME = "performance_tracker"
    private const val KEY_TOTAL_REQUESTS = "total_requests"
    private const val KEY_TOTAL_LATENCY = "total_latency_ms"
    private const val KEY_MIN_LATENCY = "min_latency_ms"
    private const val KEY_MAX_LATENCY = "max_latency_ms"
    private const val KEY_LAST_LATENCY = "last_latency_ms"
    private const val KEY_LAST_UPDATE = "last_update"
    
    // In-memory queue for recent latencies (last 100)
    private val recentLatencies = ConcurrentLinkedQueue<Long>()
    private const val MAX_RECENT_LATENCIES = 100
    
    /**
     * Record a classification latency measurement.
     */
    fun recordLatency(context: Context, latencyMs: Long) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        
        // Update recent latencies queue
        recentLatencies.offer(latencyMs)
        if (recentLatencies.size > MAX_RECENT_LATENCIES) {
            recentLatencies.poll()
        }
        
        // Update persistent stats
        val totalRequests = prefs.getLong(KEY_TOTAL_REQUESTS, 0) + 1
        val totalLatency = prefs.getLong(KEY_TOTAL_LATENCY, 0) + latencyMs
        val currentMin = prefs.getLong(KEY_MIN_LATENCY, Long.MAX_VALUE)
        val currentMax = prefs.getLong(KEY_MAX_LATENCY, 0)
        
        prefs.edit().apply {
            putLong(KEY_TOTAL_REQUESTS, totalRequests)
            putLong(KEY_TOTAL_LATENCY, totalLatency)
            putLong(KEY_MIN_LATENCY, minOf(currentMin, latencyMs))
            putLong(KEY_MAX_LATENCY, maxOf(currentMax, latencyMs))
            putLong(KEY_LAST_LATENCY, latencyMs)
            putLong(KEY_LAST_UPDATE, System.currentTimeMillis())
            apply()
        }
        
        AppLog.d("PerformanceTracker", "Recorded latency: ${latencyMs}ms (avg: ${getAverageLatency(context)}ms)")
    }
    
    /**
     * Get average latency across all recorded requests.
     */
    fun getAverageLatency(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val totalRequests = prefs.getLong(KEY_TOTAL_REQUESTS, 0)
        if (totalRequests == 0L) return 0
        
        val totalLatency = prefs.getLong(KEY_TOTAL_LATENCY, 0)
        return totalLatency / totalRequests
    }
    
    /**
     * Get average latency from recent requests only (last 100).
     */
    fun getRecentAverageLatency(): Long {
        if (recentLatencies.isEmpty()) return 0
        
        val sum = recentLatencies.sum()
        return sum / recentLatencies.size
    }
    
    /**
     * Get minimum recorded latency.
     */
    fun getMinLatency(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val min = prefs.getLong(KEY_MIN_LATENCY, Long.MAX_VALUE)
        return if (min == Long.MAX_VALUE) 0 else min
    }
    
    /**
     * Get maximum recorded latency.
     */
    fun getMaxLatency(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getLong(KEY_MAX_LATENCY, 0)
    }
    
    /**
     * Get last recorded latency.
     */
    fun getLastLatency(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getLong(KEY_LAST_LATENCY, 0)
    }
    
    /**
     * Get total number of requests tracked.
     */
    fun getTotalRequests(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getLong(KEY_TOTAL_REQUESTS, 0)
    }
    
    /**
     * Get performance stats summary.
     */
    data class PerformanceStats(
        val totalRequests: Long,
        val averageLatency: Long,
        val recentAverageLatency: Long,
        val minLatency: Long,
        val maxLatency: Long,
        val lastLatency: Long
    )
    
    fun getStats(context: Context): PerformanceStats {
        return PerformanceStats(
            totalRequests = getTotalRequests(context),
            averageLatency = getAverageLatency(context),
            recentAverageLatency = getRecentAverageLatency(),
            minLatency = getMinLatency(context),
            maxLatency = getMaxLatency(context),
            lastLatency = getLastLatency(context)
        )
    }
    
    /**
     * Clear all performance stats.
     */
    fun clearStats(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
        recentLatencies.clear()
        AppLog.d("PerformanceTracker", "Cleared all performance stats")
    }
}


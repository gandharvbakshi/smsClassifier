package com.smsclassifier.app.entitlement

import android.content.Context
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.analytics.Telemetry
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.util.AppLog

enum class EntitlementState {
    FREE,
    TRIAL_ACTIVE,
    TRIAL_EXPIRED,
    PRO
}

class EntitlementManager(private val context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val settingsRepository = SettingsRepository(context)
    private val syncClient = EntitlementSyncClient()

    fun isPro(now: Long = System.currentTimeMillis()): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return true
        val started = prefs.getLong(KEY_TRIAL_START, -1L)
        if (started <= 0L) return false
        return now - started < TRIAL_MS
    }

    fun currentState(now: Long = System.currentTimeMillis()): EntitlementState {
        if (prefs.getBoolean(KEY_PRO, false)) return EntitlementState.PRO
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        if (trialStart <= 0L) return EntitlementState.FREE
        return if (now - trialStart < TRIAL_MS) EntitlementState.TRIAL_ACTIVE
        else EntitlementState.TRIAL_EXPIRED
    }

    fun hasTrialStarted(): Boolean = prefs.getLong(KEY_TRIAL_START, -1L) > 0L

    fun hasTrialEverStarted(): Boolean = hasTrialStarted()

    fun startTrialIfAvailable(): Boolean = startTrial()

    fun startTrial(now: Long = System.currentTimeMillis()): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return false
        if (hasTrialStarted()) return false

        prefs.edit().putLong(KEY_TRIAL_START, now).apply()
        Telemetry.instance?.logTrialStarted("local")
        refreshCrashlyticsMode()
        return true
    }

    suspend fun refreshFromServer(): Boolean {
        val result = syncClient.fetch(settingsRepository.installId, firebaseUid())
        val state = result.getOrElse { return false }
        if (!state.ok) return false
        applyServerState(state)
        return true
    }

    suspend fun startTrialIfAvailableRemote(): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return false
        if (hasTrialStarted()) return false

        val result = syncClient.startTrial(settingsRepository.installId, firebaseUid())
        val state = result.getOrNull()
        if (state?.ok == true) {
            applyServerState(state)
            if (state.trialActive && state.trialStartedAt != null) {
                Telemetry.instance?.logTrialStarted("server")
                return true
            }
            return false
        }

        AppLog.w(TAG, "Trial start server sync failed: ${result.exceptionOrNull()?.message}")
        return if (BuildConfig.DEBUG) startTrial() else false
    }

    suspend fun verifyPlayPurchase(
        purchaseToken: String,
        sku: String,
        packageName: String = BuildConfig.APPLICATION_ID
    ): Boolean {
        val result = syncClient.verifyPurchase(
            installId = settingsRepository.installId,
            firebaseUid = firebaseUid(),
            packageName = packageName,
            productId = sku,
            purchaseToken = purchaseToken
        )
        val state = result.getOrNull()
        if (state?.ok == true && state.proActive) {
            applyServerPurchaseState(state, purchaseToken, sku)
            return true
        }
        if (state?.validationStatus == "invalid") {
            AppLog.w(TAG, "Play purchase rejected by backend for sku=$sku")
            return false
        }

        val fallbackReason = when {
            state?.validationStatus == "unavailable" -> "backend-unavailable"
            result.exceptionOrNull() != null -> "network-error"
            else -> null
        }
        if (fallbackReason != null) {
            AppLog.w(TAG, "Play purchase verification unavailable ($fallbackReason): ${result.exceptionOrNull()?.message}")
            markPurchasedFromPlay(purchaseToken, sku)
            return true
        }

        AppLog.w(TAG, "Play purchase verification failed for sku=$sku")
        return false
    }

    /** Calendar days left in trial, or 0 if not in trial. */
    fun trialDaysRemaining(now: Long = System.currentTimeMillis()): Int {
        if (prefs.getBoolean(KEY_PRO, false)) return 0
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        if (trialStart <= 0L) return 0
        val end = trialStart + TRIAL_MS
        if (now >= end) return 0
        val msLeft = end - now
        return ((msLeft + 86_400_000L - 1) / 86_400_000L).toInt().coerceAtLeast(0)
    }

    fun onWorkerDetectedOtp() {
        if (!prefs.getBoolean(KEY_FIRST_OTP_EVENT, false)) {
            prefs.edit().putBoolean(KEY_FIRST_OTP_EVENT, true).apply()
            val launchPrefs = context.getSharedPreferences("telemetry_launch", Context.MODE_PRIVATE)
            val firstOpen = launchPrefs.getLong("first_open_at_ms", System.currentTimeMillis())
            val seconds = (System.currentTimeMillis() - firstOpen) / 1000L
            Telemetry.instance?.logEvent(
                "first_otp_detected",
                mapOf("seconds_since_first_open" to seconds)
            )
        }
        refreshCrashlyticsMode()
    }

    fun setProPurchased(purchased: Boolean) {
        prefs.edit().putBoolean(KEY_PRO, purchased).apply()
        refreshCrashlyticsMode()
    }

    fun markPurchasedFromPlay(purchaseToken: String, sku: String) {
        prefs.edit()
            .putBoolean(KEY_PRO, true)
            .putString(KEY_PURCHASE_TOKEN, purchaseToken)
            .putString(KEY_PURCHASE_SKU, sku)
            .apply()
        refreshCrashlyticsMode()
    }

    /** Clears trial/banner state but keeps Play purchase + SKU + token. */
    fun clearTrialAndBannerStatePreservingPurchase() {
        prefs.edit()
            .remove(KEY_TRIAL_START)
            .remove(KEY_FIRST_OTP_EVENT)
            .remove(KEY_TRIAL_ACK)
            .remove(KEY_TRIAL_END_DISMISS_UNTIL)
            .apply()
        refreshCrashlyticsMode()
    }

    /** True only for lifetime Play purchase (not trial). */
    fun isPaidPro(): Boolean = prefs.getBoolean(KEY_PRO, false)

    @Suppress("UNUSED_PARAMETER")
    fun shouldUseServerForMessage(heuristicSaysOtp: Boolean): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return true
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        val now = System.currentTimeMillis()
        if (trialStart > 0L) {
            val inTrial = now - trialStart < TRIAL_MS
            return inTrial
        }
        return false
    }

    /** One-shot welcome after trial starts (first OTP). */
    fun shouldShowTrialStartedBanner(): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return false
        if (prefs.getLong(KEY_TRIAL_START, -1L) <= 0L) return false
        return !prefs.getBoolean(KEY_TRIAL_ACK, false)
    }

    fun acknowledgeTrialStartedBanner() {
        prefs.edit().putBoolean(KEY_TRIAL_ACK, true).apply()
    }

    fun shouldShowTrialEndingBanner(now: Long = System.currentTimeMillis()): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return false
        if (currentState(now) != EntitlementState.TRIAL_ACTIVE) return false
        val days = trialDaysRemaining(now)
        if (days > 2 || days == 0) return false
        if (now < prefs.getLong(KEY_TRIAL_END_DISMISS_UNTIL, 0L)) return false
        return true
    }

    fun dismissTrialEndingBanner24h() {
        prefs.edit().putLong(KEY_TRIAL_END_DISMISS_UNTIL, System.currentTimeMillis() + 86_400_000L).apply()
    }

    fun showInboxUnlockProCta(): Boolean {
        if (prefs.getBoolean(KEY_PRO, false)) return false
        return currentState() == EntitlementState.TRIAL_EXPIRED
    }

    fun shouldShowDetailUnlockPlaceholder(msg: MessageEntity): Boolean {
        if (isPro()) return false
        val st = currentState()
        if (st != EntitlementState.TRIAL_EXPIRED && st != EntitlementState.FREE) return false
        return msg.phishScore == null && msg.isPhishing == null
    }

    fun telemetryEntitlementLabel(): String = when {
        prefs.getBoolean(KEY_PRO, false) -> "pro"
        isPro() -> "trial"
        prefs.getLong(KEY_TRIAL_START, -1L) > 0L -> "trial_expired"
        else -> "free"
    }

    fun crashlyticsInferenceLabel(): String {
        val mode = when {
            prefs.getBoolean(KEY_PRO, false) -> "pro"
            isPro() -> "trial"
            else -> "free"
        }
        return mode
    }

    private fun refreshCrashlyticsMode() {
        FirebaseCrashlytics.getInstance()
            .setCustomKey("inference_mode", crashlyticsInferenceLabel())
    }

    private fun firebaseUid(): String? =
        FirebaseAuth.getInstance().currentUser?.uid

    private fun applyServerState(state: EntitlementSyncResponse) {
        val editor = prefs.edit()
        if (state.proActive) {
            editor.putBoolean(KEY_PRO, true)
        }
        state.trialStartedAt?.let { editor.putLong(KEY_TRIAL_START, it) }
        editor.apply()
        refreshCrashlyticsMode()
    }

    private fun applyServerPurchaseState(
        state: PurchaseVerifyResponse,
        purchaseToken: String,
        sku: String
    ) {
        val editor = prefs.edit()
            .putBoolean(KEY_PRO, state.proActive)
            .putString(KEY_PURCHASE_TOKEN, purchaseToken)
            .putString(KEY_PURCHASE_SKU, sku)
        state.trialStartedAt?.let { editor.putLong(KEY_TRIAL_START, it) }
        editor.apply()
        refreshCrashlyticsMode()
    }

    init {
        refreshCrashlyticsMode()
    }

    companion object {
        private const val PREFS_NAME = "entitlement_prefs"
        private const val KEY_PRO = "pro_purchased"
        private const val KEY_TRIAL_START = "trial_started_at_ms"
        private const val KEY_FIRST_OTP_EVENT = "first_otp_event_sent"
        private const val KEY_TRIAL_ACK = "trial_started_banner_ack"
        private const val KEY_TRIAL_END_DISMISS_UNTIL = "trial_end_banner_dismiss_until_ms"
        private const val KEY_PURCHASE_TOKEN = "pro_purchase_token"
        private const val KEY_PURCHASE_SKU = "pro_sku"
        private val TRIAL_MS = 7L * 24 * 60 * 60 * 1000
        private const val TAG = "EntitlementManager"
    }
}

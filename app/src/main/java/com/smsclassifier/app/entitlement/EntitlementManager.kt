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
        if (isPaidProAt(now)) return true
        val started = prefs.getLong(KEY_TRIAL_START, -1L)
        if (started <= 0L) return false
        val expiresAt = trialExpiresAtFromPrefs()
        return expiresAt > 0L && now < expiresAt
    }

    fun currentState(now: Long = System.currentTimeMillis()): EntitlementState {
        if (isPaidProAt(now)) return EntitlementState.PRO
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        if (trialStart <= 0L) return EntitlementState.FREE
        val expiresAt = trialExpiresAtFromPrefs()
        return if (expiresAt > 0L && now < expiresAt) EntitlementState.TRIAL_ACTIVE
        else EntitlementState.TRIAL_EXPIRED
    }

    fun hasTrialStarted(): Boolean = prefs.getLong(KEY_TRIAL_START, -1L) > 0L

    fun hasTrialEverStarted(): Boolean = hasTrialStarted()

    fun startTrialIfAvailable(): Boolean = startTrial()

    fun startTrial(now: Long = System.currentTimeMillis()): Boolean {
        if (isPaidProAt(now)) return false
        if (hasTrialStarted()) return false

        prefs.edit()
            .putLong(KEY_TRIAL_START, now)
            .putLong(KEY_TRIAL_EXPIRES_AT, now + DEFAULT_TRIAL_MS)
            .putInt(KEY_TRIAL_DURATION_DAYS, DEFAULT_TRIAL_DAYS)
            .putString(KEY_TRIAL_POLICY_VERSION, DEFAULT_TRIAL_POLICY_VERSION)
            .apply()
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
        if (isPaidProAt()) return false
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
        packageName: String = BuildConfig.APPLICATION_ID,
        productType: String? = null
    ): Boolean {
        val result = syncClient.verifyPurchase(
            installId = settingsRepository.installId,
            firebaseUid = firebaseUid(),
            packageName = packageName,
            productId = sku,
            purchaseToken = purchaseToken,
            productType = productType
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
            val provisionalExpiry = if (productType == PRODUCT_TYPE_SUBS) {
                System.currentTimeMillis() + PROVISIONAL_SUBSCRIPTION_MS
            } else {
                null
            }
            markPurchasedFromPlay(purchaseToken, sku, provisionalExpiry)
            return true
        }

        AppLog.w(TAG, "Play purchase verification failed for sku=$sku")
        return false
    }

    /** Calendar days left in trial, or 0 if not in trial. */
    fun trialDaysRemaining(now: Long = System.currentTimeMillis()): Int {
        if (isPaidProAt(now)) return 0
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        if (trialStart <= 0L) return 0
        val end = trialExpiresAtFromPrefs()
        if (end <= 0L) return 0
        if (now >= end) return 0
        val msLeft = end - now
        return ((msLeft + 86_400_000L - 1) / 86_400_000L).toInt().coerceAtLeast(0)
    }

    fun trialDurationDays(): Int = trialDurationDaysFromPrefs()

    fun trialDurationLabel(): String {
        val days = trialDurationDays()
        return if (days == 1) "1 day" else "$days days"
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
        val editor = prefs.edit().putBoolean(KEY_PRO, purchased)
        if (purchased) {
            editor.remove(KEY_PRO_EXPIRES_AT)
        }
        editor.apply()
        refreshCrashlyticsMode()
    }

    fun markPurchasedFromPlay(purchaseToken: String, sku: String) {
        markPurchasedFromPlay(purchaseToken, sku, proExpiresAt = null)
    }

    private fun markPurchasedFromPlay(purchaseToken: String, sku: String, proExpiresAt: Long?) {
        val editor = prefs.edit()
            .putBoolean(KEY_PRO, true)
            .putString(KEY_PURCHASE_TOKEN, purchaseToken)
            .putString(KEY_PURCHASE_SKU, sku)
            .putString(KEY_PURCHASE_POLICY_VERSION, DEFAULT_PURCHASE_POLICY_VERSION)
        if (proExpiresAt != null) {
            editor.putLong(KEY_PRO_EXPIRES_AT, proExpiresAt)
        } else {
            editor.remove(KEY_PRO_EXPIRES_AT)
        }
        editor.apply()
        refreshCrashlyticsMode()
    }

    /** Clears trial/banner state but keeps Play purchase + SKU + token. */
    fun clearTrialAndBannerStatePreservingPurchase() {
        prefs.edit()
            .remove(KEY_TRIAL_START)
            .remove(KEY_TRIAL_EXPIRES_AT)
            .remove(KEY_TRIAL_DURATION_DAYS)
            .remove(KEY_TRIAL_POLICY_VERSION)
            .remove(KEY_FIRST_OTP_EVENT)
            .remove(KEY_TRIAL_ACK)
            .remove(KEY_TRIAL_END_DISMISS_UNTIL)
            .apply()
        refreshCrashlyticsMode()
    }

    /** True only for active paid Play access (not trial). */
    fun isPaidPro(): Boolean = isPaidProAt()

    @Suppress("UNUSED_PARAMETER")
    fun shouldUseServerForMessage(heuristicSaysOtp: Boolean): Boolean {
        if (isPaidProAt()) return true
        val trialStart = prefs.getLong(KEY_TRIAL_START, -1L)
        val now = System.currentTimeMillis()
        if (trialStart > 0L) {
            val expiresAt = trialExpiresAtFromPrefs()
            val inTrial = expiresAt > 0L && now < expiresAt
            return inTrial
        }
        return false
    }

    /** One-shot welcome after trial starts (first OTP). */
    fun shouldShowTrialStartedBanner(): Boolean {
        if (isPaidProAt()) return false
        if (prefs.getLong(KEY_TRIAL_START, -1L) <= 0L) return false
        return !prefs.getBoolean(KEY_TRIAL_ACK, false)
    }

    fun acknowledgeTrialStartedBanner() {
        prefs.edit().putBoolean(KEY_TRIAL_ACK, true).apply()
    }

    fun shouldShowTrialEndingBanner(now: Long = System.currentTimeMillis()): Boolean {
        if (isPaidProAt(now)) return false
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
        if (isPaidProAt()) return false
        return currentState() == EntitlementState.TRIAL_EXPIRED
    }

    fun shouldShowDetailUnlockPlaceholder(msg: MessageEntity): Boolean {
        if (isPro()) return false
        val st = currentState()
        if (st != EntitlementState.TRIAL_EXPIRED && st != EntitlementState.FREE) return false
        return msg.phishScore == null && msg.isPhishing == null
    }

    fun telemetryEntitlementLabel(): String = when {
        isPaidProAt() -> "pro"
        isPro() -> "trial"
        prefs.getLong(KEY_TRIAL_START, -1L) > 0L -> "trial_expired"
        else -> "free"
    }

    fun crashlyticsInferenceLabel(): String {
        val mode = when {
            isPaidProAt() -> "pro"
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
            if (state.proExpiresAt != null) {
                editor.putLong(KEY_PRO_EXPIRES_AT, state.proExpiresAt)
            } else {
                editor.remove(KEY_PRO_EXPIRES_AT)
            }
        } else {
            editor.remove(KEY_PRO)
            editor.remove(KEY_PRO_EXPIRES_AT)
        }
        applyTrialSnapshot(
            editor = editor,
            trialStartedAt = state.trialStartedAt,
            trialExpiresAt = state.trialExpiresAt,
            trialDurationDays = state.trialDurationDays,
            trialPolicyVersion = state.trialPolicyVersion
        )
        applyPurchasePolicySnapshot(editor, state.purchasePolicyVersion)
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
        if (state.proExpiresAt != null) {
            editor.putLong(KEY_PRO_EXPIRES_AT, state.proExpiresAt)
        } else {
            editor.remove(KEY_PRO_EXPIRES_AT)
        }
        applyTrialSnapshot(
            editor = editor,
            trialStartedAt = state.trialStartedAt,
            trialExpiresAt = state.trialExpiresAt,
            trialDurationDays = state.trialDurationDays,
            trialPolicyVersion = state.trialPolicyVersion
        )
        applyPurchasePolicySnapshot(editor, state.purchasePolicyVersion)
        editor.apply()
        refreshCrashlyticsMode()
    }

    private fun applyTrialSnapshot(
        editor: android.content.SharedPreferences.Editor,
        trialStartedAt: Long?,
        trialExpiresAt: Long?,
        trialDurationDays: Int?,
        trialPolicyVersion: String?
    ) {
        val durationDays = trialDurationDays?.takeIf { it > 0 }
        durationDays?.let { editor.putInt(KEY_TRIAL_DURATION_DAYS, it) }
        trialPolicyVersion?.takeIf { it.isNotBlank() }?.let {
            editor.putString(KEY_TRIAL_POLICY_VERSION, it)
        }
        trialStartedAt?.let { startedAt ->
            editor.putLong(KEY_TRIAL_START, startedAt)
            val expiresAt = trialExpiresAt
                ?: startedAt + (durationDays ?: DEFAULT_TRIAL_DAYS) * 86_400_000L
            editor.putLong(KEY_TRIAL_EXPIRES_AT, expiresAt)
        }
    }

    private fun applyPurchasePolicySnapshot(
        editor: android.content.SharedPreferences.Editor,
        purchasePolicyVersion: String?
    ) {
        purchasePolicyVersion?.takeIf { it.isNotBlank() }?.let {
            editor.putString(KEY_PURCHASE_POLICY_VERSION, it)
        }
    }

    private fun isPaidProAt(now: Long = System.currentTimeMillis()): Boolean {
        if (!prefs.getBoolean(KEY_PRO, false)) return false
        val expiresAt = prefs.getLong(KEY_PRO_EXPIRES_AT, -1L)
        return expiresAt <= 0L || now < expiresAt
    }

    private fun trialExpiresAtFromPrefs(): Long {
        val explicit = prefs.getLong(KEY_TRIAL_EXPIRES_AT, -1L)
        if (explicit > 0L) return explicit
        val started = prefs.getLong(KEY_TRIAL_START, -1L)
        return if (started > 0L) started + LEGACY_TRIAL_MS else -1L
    }

    private fun trialDurationDaysFromPrefs(): Int {
        val stored = prefs.getInt(KEY_TRIAL_DURATION_DAYS, -1)
        if (stored > 0) return stored
        val started = prefs.getLong(KEY_TRIAL_START, -1L)
        val expiresAt = prefs.getLong(KEY_TRIAL_EXPIRES_AT, -1L)
        if (started > 0L && expiresAt > started) {
            val ms = expiresAt - started
            return ((ms + 86_400_000L - 1) / 86_400_000L).toInt().coerceAtLeast(1)
        }
        if (started > 0L) return LEGACY_TRIAL_DAYS
        return DEFAULT_TRIAL_DAYS
    }

    init {
        refreshCrashlyticsMode()
    }

    companion object {
        private const val PREFS_NAME = "entitlement_prefs"
        private const val KEY_PRO = "pro_purchased"
        private const val KEY_TRIAL_START = "trial_started_at_ms"
        private const val KEY_TRIAL_EXPIRES_AT = "trial_expires_at_ms"
        private const val KEY_TRIAL_DURATION_DAYS = "trial_duration_days"
        private const val KEY_TRIAL_POLICY_VERSION = "trial_policy_version"
        private const val KEY_FIRST_OTP_EVENT = "first_otp_event_sent"
        private const val KEY_TRIAL_ACK = "trial_started_banner_ack"
        private const val KEY_TRIAL_END_DISMISS_UNTIL = "trial_end_banner_dismiss_until_ms"
        private const val KEY_PURCHASE_TOKEN = "pro_purchase_token"
        private const val KEY_PURCHASE_SKU = "pro_sku"
        private const val KEY_PURCHASE_POLICY_VERSION = "purchase_policy_version"
        private const val KEY_PRO_EXPIRES_AT = "pro_expires_at_ms"
        private const val PRODUCT_TYPE_SUBS = "subs"
        private const val DEFAULT_TRIAL_DAYS = 14
        private const val DEFAULT_TRIAL_POLICY_VERSION = "trial_14d_v1"
        private const val DEFAULT_PURCHASE_POLICY_VERSION = "play_pro_yearly_annual_v1"
        private val DEFAULT_TRIAL_MS = DEFAULT_TRIAL_DAYS * 24L * 60 * 60 * 1000
        private const val LEGACY_TRIAL_DAYS = 7
        private val LEGACY_TRIAL_MS = LEGACY_TRIAL_DAYS * 24L * 60 * 60 * 1000
        private val PROVISIONAL_SUBSCRIPTION_MS = 3L * 24 * 60 * 60 * 1000
        private const val TAG = "EntitlementManager"
    }
}

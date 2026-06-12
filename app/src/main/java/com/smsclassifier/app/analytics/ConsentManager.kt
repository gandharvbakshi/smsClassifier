package com.smsclassifier.app.analytics

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.core.handlers.ReplaceFileCorruptionHandler
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.preferencesDataStore
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import java.io.IOException

private val Context.consentDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "consent_prefs",
    corruptionHandler = ReplaceFileCorruptionHandler { emptyPreferences() }
)

class ConsentManager(context: Context) {
    private val appContext = context.applicationContext
    private val dataStore = appContext.consentDataStore

    @Volatile
    private var cacheAnalytics: Boolean = false

    @Volatile
    private var cacheCrash: Boolean = false

    @Volatile
    private var cacheMeta: Boolean = false

    @Volatile
    private var cacheOnboardingSeen: Boolean = false

    private val safeData: Flow<Preferences> = dataStore.data.catch { throwable ->
        if (throwable is IOException) {
            emit(emptyPreferences())
        } else {
            throw throwable
        }
    }

    init {
        runBlocking {
            val prefs = withTimeoutOrNull(DATASTORE_READ_TIMEOUT_MS) {
                safeData.first()
            } ?: emptyPreferences()
            cacheAnalytics = prefs[KEY_ANALYTICS] ?: false
            cacheCrash = prefs[KEY_CRASH] ?: false
            cacheMeta = prefs[KEY_META] ?: false
            cacheOnboardingSeen = prefs[KEY_ONBOARDING] ?: false
        }
        FirebaseAnalytics.getInstance(appContext).setAnalyticsCollectionEnabled(cacheAnalytics)
        FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(cacheCrash)
    }

    val analyticsConsent: Flow<Boolean> = safeData.map { it[KEY_ANALYTICS] ?: false }
    val crashlyticsConsent: Flow<Boolean> = safeData.map { it[KEY_CRASH] ?: false }
    val metaAdsConsent: Flow<Boolean> = safeData.map { it[KEY_META] ?: false }
    val onboardingConsentSeen: Flow<Boolean> = safeData.map { it[KEY_ONBOARDING] ?: false }

    fun analyticsEnabledNow(): Boolean = cacheAnalytics
    fun crashlyticsEnabledNow(): Boolean = cacheCrash
    fun metaAdsEnabledNow(): Boolean = cacheMeta
    fun onboardingSeenNow(): Boolean = cacheOnboardingSeen

    suspend fun setAnalyticsConsent(value: Boolean) {
        dataStore.edit { it[KEY_ANALYTICS] = value }
        cacheAnalytics = value
        FirebaseAnalytics.getInstance(appContext).setAnalyticsCollectionEnabled(value)
    }

    suspend fun setCrashlyticsConsent(value: Boolean) {
        dataStore.edit { it[KEY_CRASH] = value }
        cacheCrash = value
        FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(value)
    }

    suspend fun setMetaAdsConsent(value: Boolean) {
        dataStore.edit { it[KEY_META] = value }
        cacheMeta = value
    }

    suspend fun markOnboardingConsentSeen() {
        dataStore.edit { it[KEY_ONBOARDING] = true }
        cacheOnboardingSeen = true
    }

    /**
     * Removes all DataStore preferences except analytics / crash / meta / onboarding flags.
     */
    suspend fun clearAllDataStoreExceptConsent() {
        val snap = safeData.first()
        val analytics = snap[KEY_ANALYTICS]
        val crash = snap[KEY_CRASH]
        val meta = snap[KEY_META]
        val onboarding = snap[KEY_ONBOARDING]
        dataStore.edit { prefs ->
            prefs.clear()
            if (analytics != null) prefs[KEY_ANALYTICS] = analytics
            if (crash != null) prefs[KEY_CRASH] = crash
            if (meta != null) prefs[KEY_META] = meta
            if (onboarding != null) prefs[KEY_ONBOARDING] = onboarding
        }
    }

    companion object {
        private const val DATASTORE_READ_TIMEOUT_MS = 1_500L
        private val KEY_ANALYTICS = booleanPreferencesKey("analytics_consent")
        private val KEY_CRASH = booleanPreferencesKey("crashlytics_consent")
        private val KEY_META = booleanPreferencesKey("meta_ads_consent")
        private val KEY_ONBOARDING = booleanPreferencesKey("onboarding_consent_seen")
    }
}

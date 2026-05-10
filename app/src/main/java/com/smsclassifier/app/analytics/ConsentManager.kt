package com.smsclassifier.app.analytics

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking

private val Context.consentDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "consent_prefs"
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

    init {
        runBlocking {
            cacheAnalytics = dataStore.data.first()[KEY_ANALYTICS] ?: false
            cacheCrash = dataStore.data.first()[KEY_CRASH] ?: false
            cacheMeta = dataStore.data.first()[KEY_META] ?: false
            cacheOnboardingSeen = dataStore.data.first()[KEY_ONBOARDING] ?: false
        }
        FirebaseAnalytics.getInstance(appContext).setAnalyticsCollectionEnabled(cacheAnalytics)
        FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(cacheCrash)
    }

    val analyticsConsent: Flow<Boolean> = dataStore.data.map { it[KEY_ANALYTICS] ?: false }
    val crashlyticsConsent: Flow<Boolean> = dataStore.data.map { it[KEY_CRASH] ?: false }
    val metaAdsConsent: Flow<Boolean> = dataStore.data.map { it[KEY_META] ?: false }
    val onboardingConsentSeen: Flow<Boolean> = dataStore.data.map { it[KEY_ONBOARDING] ?: false }

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

    companion object {
        private val KEY_ANALYTICS = booleanPreferencesKey("analytics_consent")
        private val KEY_CRASH = booleanPreferencesKey("crashlytics_consent")
        private val KEY_META = booleanPreferencesKey("meta_ads_consent")
        private val KEY_ONBOARDING = booleanPreferencesKey("onboarding_consent_seen")
    }
}

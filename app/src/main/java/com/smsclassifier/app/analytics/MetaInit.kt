package com.smsclassifier.app.analytics

import android.content.Context
import com.facebook.FacebookSdk
import com.smsclassifier.app.BuildConfig

object MetaInit {
    fun init(
        @Suppress("UNUSED_PARAMETER") context: Context,
        @Suppress("UNUSED_PARAMETER") consentManager: ConsentManager
    ) {
        if (BuildConfig.META_APP_ID.isBlank()) return
        try {
            FacebookSdk.setApplicationId(BuildConfig.META_APP_ID)
            FacebookSdk.setClientToken(BuildConfig.META_CLIENT_TOKEN)
            FacebookSdk.setAutoInitEnabled(false)
            FacebookSdk.fullyInitialize()
            // Advertiser ID collection: configure via manifest when META_APP_ID is set;
            // runtime toggles vary by SDK minor version — avoid incompatible APIs here.
        } catch (_: Throwable) {
            // Avoid crashing if Play Services / FB deps unavailable on odd builds.
        }
    }
}

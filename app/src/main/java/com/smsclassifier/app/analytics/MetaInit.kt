package com.smsclassifier.app.analytics

import android.content.Context

/**
 * Meta SDK is wired in Phase 11. Stub keeps [SMSClassifierApplication] compiling before then.
 */
object MetaInit {
    fun init(context: Context, consentManager: ConsentManager) {
        // Phase 11: FacebookSdk + AppEventsLogger behind consent
    }
}

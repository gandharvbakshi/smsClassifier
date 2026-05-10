package com.smsclassifier.app

import android.app.Application
import com.smsclassifier.app.analytics.ConsentManager
import com.smsclassifier.app.analytics.MetaInit
import com.smsclassifier.app.analytics.Telemetry
import com.smsclassifier.app.entitlement.EntitlementManager

/**
 * Process-wide singletons. Initialized from [SMSClassifierApplication.onCreate].
 */
object AppContainer {
    lateinit var consentManager: ConsentManager
        private set

    lateinit var entitlementManager: EntitlementManager
        private set

    lateinit var telemetry: Telemetry
        private set

    fun init(application: Application) {
        consentManager = ConsentManager(application.applicationContext)
        entitlementManager = EntitlementManager(application.applicationContext)
        telemetry = Telemetry(application.applicationContext, consentManager)
        Telemetry.instance = telemetry
        telemetry.init()
        MetaInit.init(application.applicationContext, consentManager)
    }
}

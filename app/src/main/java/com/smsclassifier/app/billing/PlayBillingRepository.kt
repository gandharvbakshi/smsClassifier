package com.smsclassifier.app.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingClient.BillingResponseCode
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import com.android.billingclient.api.PurchasesUpdatedListener
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.util.AppLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Play Billing 9 for the annual Pro subscription.
 *
 * New purchases use [SKU_PRO_YEARLY]. The legacy lifetime SKU is still queried
 * during restore so earlier buyers keep access.
 */
class PlayBillingRepository(private val context: Context) {

    companion object {
        const val SKU_PRO_YEARLY = "pro_yearly"
        const val SKU_PRO_LIFETIME = "pro_lifetime"
        private const val BASE_PLAN_ANNUAL = "annual"
        private const val TAG = "PlayBilling"

        fun formattedAnnualPrice(productDetails: ProductDetails?): String? =
            recurringPricingPhase(productDetails)?.formattedPrice

        private fun annualPriceAmountMicros(productDetails: ProductDetails?): Long =
            recurringPricingPhase(productDetails)?.priceAmountMicros ?: 0L

        private fun annualPriceCurrency(productDetails: ProductDetails?): String =
            recurringPricingPhase(productDetails)?.priceCurrencyCode.orEmpty()

        private fun selectedAnnualOffer(
            productDetails: ProductDetails
        ): ProductDetails.SubscriptionOfferDetails? =
            productDetails.subscriptionOfferDetails
                ?.firstOrNull { offer ->
                    offer.basePlanId == BASE_PLAN_ANNUAL && offer.offerId.isNullOrBlank()
                }
                ?: productDetails.subscriptionOfferDetails
                    ?.firstOrNull { offer -> offer.basePlanId == BASE_PLAN_ANNUAL }
                ?: productDetails.subscriptionOfferDetails?.firstOrNull()

        private fun recurringPricingPhase(
            productDetails: ProductDetails?
        ): ProductDetails.PricingPhase? =
            productDetails
                ?.let(::selectedAnnualOffer)
                ?.pricingPhases
                ?.pricingPhaseList
                ?.lastOrNull()
    }

    private val appContext = context.applicationContext
    private var billingClient: BillingClient? = null
    private val billingScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val _productDetails = MutableStateFlow<ProductDetails?>(null)
    val productDetails: StateFlow<ProductDetails?> = _productDetails.asStateFlow()

    private val _connected = MutableStateFlow(false)
    val connected: StateFlow<Boolean> = _connected.asStateFlow()

    private val _purchaseSuccess = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val purchaseSuccess: SharedFlow<Unit> = _purchaseSuccess.asSharedFlow()

    private val _purchaseError = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val purchaseError: SharedFlow<String> = _purchaseError.asSharedFlow()

    private val _isLaunchingFlow = MutableStateFlow(false)
    val isLaunchingFlow: StateFlow<Boolean> = _isLaunchingFlow.asStateFlow()

    private val listener = PurchasesUpdatedListener { billingResult, purchases ->
        _isLaunchingFlow.value = false
        when (billingResult.responseCode) {
            BillingResponseCode.OK ->
                purchases?.forEach { handlePurchase(it, fromUserFlow = true) }
            BillingResponseCode.USER_CANCELED ->
                AppLog.d(TAG, "User canceled purchase flow")
            else -> {
                AppLog.w(TAG, "Purchase update ${billingResult.responseCode} ${billingResult.debugMessage}")
                emitPurchaseFailure(billingResult)
            }
        }
    }

    fun startConnection() {
        if (billingClient?.isReady == true) {
            querySkuDetails()
            restorePurchases()
            return
        }
        val existing = billingClient
        if (existing != null && !existing.isReady) {
            existing.endConnection()
            billingClient = null
            _connected.value = false
        }
        if (billingClient != null) return

        billingClient = BillingClient.newBuilder(appContext)
            .setListener(listener)
            .enablePendingPurchases(
                PendingPurchasesParams.newBuilder()
                    .enableOneTimeProducts()
                    .build()
            )
            .enableAutoServiceReconnection()
            .build()
        billingClient!!.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                if (billingResult.responseCode == BillingResponseCode.OK) {
                    _connected.value = true
                    querySkuDetails()
                    restorePurchases()
                } else {
                    AppLog.w(TAG, "Billing setup failed: ${billingResult.debugMessage}")
                    _connected.value = false
                    billingClient?.endConnection()
                    billingClient = null
                }
            }

            override fun onBillingServiceDisconnected() {
                _connected.value = false
                billingClient?.endConnection()
                billingClient = null
            }
        })
    }

    fun querySkuDetails() {
        val client = billingClient ?: return
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(SKU_PRO_YEARLY)
                        .setProductType(BillingClient.ProductType.SUBS)
                        .build()
                )
            ).build()
        client.queryProductDetailsAsync(params) { result, queryResult ->
            val productDetailsList = queryResult.productDetailsList
            if (result.responseCode == BillingResponseCode.OK && productDetailsList.isNotEmpty()) {
                _productDetails.value = productDetailsList.firstOrNull()
            } else {
                val unfetchedCount = queryResult.unfetchedProductList.size
                AppLog.w(
                    TAG,
                    "SKU query failed code=${result.responseCode} msg=${result.debugMessage} count=${productDetailsList.size} unfetched=$unfetchedCount"
                )
            }
        }
    }

    fun restorePurchases() {
        val client = billingClient ?: return
        restorePurchasesFor(client, BillingClient.ProductType.SUBS)
        restorePurchasesFor(client, BillingClient.ProductType.INAPP)
    }

    private fun restorePurchasesFor(client: BillingClient, productType: String) {
        client.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder()
                .setProductType(productType)
                .build()
        ) { result, purchases ->
            if (result.responseCode != BillingResponseCode.OK) {
                AppLog.w(TAG, "Restore $productType failed code=${result.responseCode} msg=${result.debugMessage}")
                return@queryPurchasesAsync
            }
            purchases.forEach { handlePurchase(it, fromUserFlow = false) }
        }
    }

    private fun handlePurchase(purchase: Purchase, fromUserFlow: Boolean) {
        if (purchase.purchaseState != Purchase.PurchaseState.PURCHASED) return

        val productId = when {
            purchase.products.contains(SKU_PRO_YEARLY) -> SKU_PRO_YEARLY
            purchase.products.contains(SKU_PRO_LIFETIME) -> SKU_PRO_LIFETIME
            else -> return
        }
        val productType = when (productId) {
            SKU_PRO_YEARLY -> BillingClient.ProductType.SUBS
            else -> BillingClient.ProductType.INAPP
        }

        billingScope.launch {
            val wasPaidPro = AppContainer.entitlementManager.isPaidPro()
            val verified = AppContainer.entitlementManager.verifyPlayPurchase(
                purchaseToken = purchase.purchaseToken,
                sku = productId,
                packageName = appContext.packageName,
                productType = productType
            )
            if (!verified) {
                AppLog.w(TAG, "Purchase verification failed for $productId")
                AppContainer.telemetry.logEvent(
                    "purchase_verification_failed",
                    mapOf("sku" to productId, "product_type" to productType)
                )
                if (fromUserFlow) {
                    _purchaseError.tryEmit("Purchase could not be verified. Restore again in a few minutes.")
                }
                return@launch
            }

            acknowledgeIfNeeded(purchase)

            if (!wasPaidPro) {
                val micros = if (productId == SKU_PRO_YEARLY) {
                    annualPriceAmountMicros(_productDetails.value)
                } else {
                    0L
                }
                val currency = if (productId == SKU_PRO_YEARLY) {
                    annualPriceCurrency(_productDetails.value)
                } else {
                    ""
                }
                AppContainer.telemetry.logPurchaseCompleted(
                    sku = productId,
                    value = micros / 1_000_000.0,
                    currency = currency
                )
            }

            if (!wasPaidPro && fromUserFlow) {
                _purchaseSuccess.tryEmit(Unit)
            }
        }
    }

    private fun acknowledgeIfNeeded(purchase: Purchase) {
        if (purchase.isAcknowledged) return
        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        billingClient?.acknowledgePurchase(params) { result ->
            if (result.responseCode != BillingResponseCode.OK) {
                AppLog.w(TAG, "Acknowledge failed: ${result.debugMessage}")
            }
        }
    }

    fun launchBillingFlow(activity: Activity) {
        val client = billingClient
        val pd = _productDetails.value
        if (client == null || !client.isReady || pd == null) {
            querySkuDetails()
            if (client == null || !client.isReady) startConnection()
            val reason = when {
                client == null || !client.isReady -> "Billing is not ready yet. Wait a moment and try again."
                pd == null -> "Product price is still loading. Check your connection and try again."
                else -> "Purchase could not start. Try again."
            }
            AppLog.w(TAG, "Billing not ready or product missing — $reason")
            _purchaseError.tryEmit(reason)
            return
        }

        val offer = selectedAnnualOffer(pd)
        if (offer == null) {
            querySkuDetails()
            AppLog.w(TAG, "No subscription offer token for $SKU_PRO_YEARLY")
            _purchaseError.tryEmit("Subscription price is still loading. Check your connection and try again.")
            return
        }

        AppContainer.telemetry.logBeginCheckout(SKU_PRO_YEARLY)
        _isLaunchingFlow.value = true
        val detailsParams = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(pd)
            .setOfferToken(offer.offerToken)
            .build()
        val flowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(detailsParams))
            .build()
        val launchResult = client.launchBillingFlow(activity, flowParams)
        if (launchResult.responseCode != BillingResponseCode.OK) {
            _isLaunchingFlow.value = false
            emitPurchaseFailure(launchResult)
        }
    }

    fun endConnection() {
        billingClient?.endConnection()
        billingClient = null
        _connected.value = false
    }

    private fun emitPurchaseFailure(billingResult: BillingResult) {
        val message = userFacingPurchaseError(billingResult)
        _purchaseError.tryEmit(message)
        AppContainer.telemetry.logEvent(
            "purchase_failed",
            mapOf(
                "sku" to SKU_PRO_YEARLY,
                "error_code" to billingResult.responseCode.toString(),
                "error_message" to sanitizeDebugMessage(billingResult.debugMessage)
            )
        )
    }

    private fun userFacingPurchaseError(billingResult: BillingResult): String {
        val debug = billingResult.debugMessage.trim()
        return when (billingResult.responseCode) {
            BillingResponseCode.BILLING_UNAVAILABLE ->
                "Google Play Billing is unavailable on this device."
            BillingResponseCode.ITEM_UNAVAILABLE ->
                "This purchase is not available in your Play Store region."
            BillingResponseCode.DEVELOPER_ERROR ->
                "Purchase could not start (app billing configuration). Try again later."
            BillingResponseCode.SERVICE_DISCONNECTED ->
                "Lost connection to Google Play. Try again."
            BillingResponseCode.NETWORK_ERROR ->
                "Network error during purchase. Check your connection and try again."
            else -> if (debug.isNotEmpty()) {
                "Purchase couldn't complete: $debug"
            } else {
                "Purchase couldn't complete — try again or restore."
            }
        }
    }

    /** Keep telemetry params free of long/noisy strings while preserving useful Play hints. */
    private fun sanitizeDebugMessage(message: String?): String =
        message?.trim()?.take(180).orEmpty()
}

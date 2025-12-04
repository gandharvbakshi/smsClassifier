package com.smsclassifier.app.classification

import android.content.Context
import ai.onnxruntime.OnnxTensor
import com.smsclassifier.app.util.AppLog
import ai.onnxruntime.OnnxValue
import ai.onnxruntime.OrtSession
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ConcurrentHashMap
import kotlin.sequences.asSequence

class OnDeviceClassifier(private val context: Context) : Classifier {
    private var phishingSession: OrtSession? = null
    private var isotpSession: OrtSession? = null
    private var intentSession: OrtSession? = null
    private var featureExtractor: FeatureExtractor = FeatureExtractor(context)
    private var loadTimeMs: Long = 0

    init {
        loadModels()
    }

    private fun loadModels() {
        val startTime = System.currentTimeMillis()
        try {
            // Load models from assets
            phishingSession = loadModel("model_phishing.onnx")
            isotpSession = loadModel("model_isotp.onnx")
            intentSession = loadModel("model_intent.onnx")
            
            loadTimeMs = System.currentTimeMillis() - startTime
            AppLog.d("OnDeviceClassifier", "Models loaded in ${loadTimeMs}ms")
        } catch (e: Exception) {
            AppLog.e("OnDeviceClassifier", "Failed to load models", e)
        }
    }

    private fun loadModel(assetName: String): OrtSession? {
        return try {
            SESSION_CACHE[assetName] ?: synchronized(SESSION_CACHE) {
                SESSION_CACHE[assetName]?.let { return it }

                val tempFile = File(context.cacheDir, assetName)
                context.assets.open(assetName).use { input ->
                    FileOutputStream(tempFile).use { output ->
                        input.copyTo(output)
                    }
                }

                val session = ORT_ENVIRONMENT.createSession(tempFile.absolutePath, SESSION_OPTIONS)
                session.inputNames.forEach { AppLog.d("OnDeviceClassifier", "$assetName input: $it") }
                session.outputNames.forEach { AppLog.d("OnDeviceClassifier", "$assetName output: $it") }
                SESSION_CACHE[assetName] = session
                session
            }
        } catch (e: Exception) {
            AppLog.e("OnDeviceClassifier", "Failed to load $assetName", e)
            null
        }
    }

    override suspend fun predict(input: MessageFeatures): Prediction = withContext(Dispatchers.Default) {
        val startTime = System.currentTimeMillis()
        
        try {
            // Combine TF-IDF and heuristic features
            val tfidfVector = input.tfidfVector ?: featureExtractor.extractTfIdfVector(input.text)
            val heuristicFeatures = input.heuristicFeatures ?: featureExtractor.extractHeuristicFeatures(input.text, input.sender)
            
            val combinedFeatures = FloatArray(tfidfVector.size + heuristicFeatures.size) { i ->
                when {
                    i < tfidfVector.size -> tfidfVector[i]
                    else -> heuristicFeatures[i - tfidfVector.size]
                }
            }
            
            val reasons = mutableListOf<String>()
            // Predict phishing
            val phishingScores = phishingSession?.let { session ->
                val inputName = session.inputNames.firstOrNull() ?: return@let floatArrayOf(0f, 0f)
                createInputTensor(combinedFeatures).use { tensor ->
                    session.run(mapOf(inputName to tensor)).use { result ->
                        result.firstValue().asFloatArray(floatArrayOf(0f, 0f))
                    }
                }
            } ?: floatArrayOf(0f, 0f)
            AppLog.d("OnDeviceClassifier", "phishingScores=${phishingScores.joinToString()}")
            val isPhishing = phishingScores.size > 1 && phishingScores[1] > 0.5f
            val phishScore = if (phishingScores.size > 1) phishingScores[1] else 0f
            
            if (isPhishing) {
                reasons.add("Phishing score: ${String.format("%.2f", phishScore)}")
            }
            
            // Heuristics-first approach: Run heuristics before ML
            val heuristicResult = HeuristicOtpClassifier.classify(input.text, input.sender)
            AppLog.d("OnDeviceClassifier", "Heuristic result: isOtp=${heuristicResult.isOtp}, confidence=${heuristicResult.confidence}")
            
            var isOtp: Boolean
            var otpIntent: String? = null
            
            // Use heuristics if high confidence, otherwise use ML
            if (heuristicResult.isOtp && heuristicResult.confidence > 0.8f) {
                // High confidence heuristic match - use it
                isOtp = true
                otpIntent = heuristicResult.suggestedIntent
                reasons.addAll(heuristicResult.reasons)
                reasons.add("OTP detected by heuristics (confidence: ${String.format("%.2f", heuristicResult.confidence)})")
                AppLog.d("OnDeviceClassifier", "Using heuristic classification (high confidence)")
            } else {
                // Low confidence or no heuristic match - use ML
                val isotpScores = isotpSession?.let { session ->
                    val inputName = session.inputNames.firstOrNull() ?: return@let floatArrayOf(0f, 0f)
                    createInputTensor(combinedFeatures).use { tensor ->
                        session.run(mapOf(inputName to tensor)).use { result ->
                            result.firstValue().asFloatArray(floatArrayOf(0f, 0f))
                        }
                    }
                } ?: floatArrayOf(0f, 0f)
                AppLog.d("OnDeviceClassifier", "isOtpScores=${isotpScores.joinToString()}")
                isOtp = isotpScores.size > 1 && isotpScores[1] > OTP_THRESHOLD
                
                if (!isOtp && heuristicResult.confidence > 0.5f) {
                    // ML says no but heuristics suggest yes with medium confidence - trust heuristics
                    isOtp = true
                    otpIntent = heuristicResult.suggestedIntent
                    reasons.addAll(heuristicResult.reasons)
                    reasons.add("ML negative but heuristics positive (confidence: ${String.format("%.2f", heuristicResult.confidence)})")
                    AppLog.d("OnDeviceClassifier", "Using heuristic classification (ML disagreed)")
                } else if (isOtp) {
                    reasons.add("OTP detected by ML (score: ${String.format("%.2f", isotpScores[1])})")
                }
            }
            
            // Predict intent (only if OTP) - use ML if heuristics didn't suggest one
            if (isOtp && otpIntent == null) {
                val intentScores = intentSession?.let { session ->
                    val inputName = session.inputNames.firstOrNull() ?: return@let FloatArray(9)
                    createInputTensor(combinedFeatures).use { tensor ->
                        session.run(mapOf(inputName to tensor)).use { result ->
                            result.firstValue().asFloatArray(FloatArray(9))
                        }
                    }
                } ?: FloatArray(9)
                AppLog.d("OnDeviceClassifier", "intentScores=${intentScores.joinToString()}")
                val maxIndex = intentScores.indices.maxByOrNull { intentScores[it] } ?: 0
                
                // Map index to intent (you'll need to load this from metadata)
                otpIntent = mapIntentIndex(maxIndex)
                reasons.add("OTP Intent: $otpIntent")
            }
            
            val inferenceTime = System.currentTimeMillis() - startTime
            
            Prediction(
                isOtp = isOtp,
                otpIntent = otpIntent,
                isPhishing = isPhishing,
                phishScore = phishScore,
                reasons = reasons,
                inferenceTimeMs = inferenceTime
            )
        } catch (e: Exception) {
            AppLog.e("OnDeviceClassifier", "Prediction failed", e)
            Prediction(
                isOtp = null,
                otpIntent = null,
                isPhishing = null,
                phishScore = 0f,
                reasons = listOf("Error: ${e.message}"),
                inferenceTimeMs = System.currentTimeMillis() - startTime
            )
        }
    }

    private fun mapIntentIndex(index: Int): String {
        // This should match your label encoder order
        val intents = listOf(
            "APP_ACCOUNT_CHANGE_OTP",
            "APP_LOGIN_OTP",
            "BANK_OR_CARD_TXN_OTP",
            "DELIVERY_OR_SERVICE_OTP",
            "FINANCIAL_LOGIN_OTP",
            "GENERIC_APP_ACTION_OTP",
            "KYC_OR_ESIGN_OTP",
            "NOT_OTP",
            "UPI_TXN_OR_PIN_OTP"
        )
        return intents.getOrNull(index) ?: "UNKNOWN"
    }

    override fun isAvailable(): Boolean {
        return phishingSession != null && isotpSession != null && intentSession != null
    }

    private fun createInputTensor(features: FloatArray): OnnxTensor =
        OnnxTensor.createTensor(ORT_ENVIRONMENT, arrayOf(features.copyOf()))

    companion object {
        private val ORT_ENVIRONMENT by lazy {
            ai.onnxruntime.OrtEnvironment.getEnvironment()
        }

        private val SESSION_OPTIONS by lazy {
            OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(1)
                setInterOpNumThreads(1)
                setExecutionMode(OrtSession.SessionOptions.ExecutionMode.SEQUENTIAL)
            }
        }

        private val SESSION_CACHE = ConcurrentHashMap<String, OrtSession>()

        private const val OTP_THRESHOLD = 0.5f
    }
}

private fun OrtSession.Result.firstValue(): OnnxValue? {
    return this.iterator().asSequence().firstOrNull()?.value
}

private fun OnnxValue?.asFloatArray(default: FloatArray): FloatArray {
    if (this !is OnnxTensor) {
        this?.close()
        return default
    }

    return try {
        val buffer = this.floatBuffer
        if (buffer != null) {
            buffer.rewind()
            val arr = FloatArray(buffer.remaining())
            buffer.get(arr)
            this.close()
            arr
        } else {
            val valueArray = (this.value as? FloatArray)
                ?: (this.value as? Array<FloatArray>)?.firstOrNull()
                ?: default
            this.close()
            valueArray
        }
    } catch (e: Exception) {
        this.close()
        default
    }
}


package com.smsclassifier.app.classification

import android.content.Context
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OnnxValue
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import kotlin.sequences.asSequence

class OnDeviceClassifier(private val context: Context) : Classifier {
    private var ortEnv: OrtEnvironment? = null
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
            ortEnv = OrtEnvironment.getEnvironment()
            
            // Load models from assets
            phishingSession = loadModel("model_phishing.onnx")
            isotpSession = loadModel("model_isotp.onnx")
            intentSession = loadModel("model_intent.onnx")
            
            loadTimeMs = System.currentTimeMillis() - startTime
            Log.d("OnDeviceClassifier", "Models loaded in ${loadTimeMs}ms")
        } catch (e: Exception) {
            Log.e("OnDeviceClassifier", "Failed to load models", e)
        }
    }

    private fun loadModel(assetName: String): OrtSession? {
        return try {
            val inputStream = context.assets.open(assetName)
            val tempFile = File(context.cacheDir, assetName)
            FileOutputStream(tempFile).use { output ->
                inputStream.copyTo(output)
            }
            val session = ortEnv?.createSession(tempFile.absolutePath)
            // Log input/output names for debugging
            session?.inputNames?.forEach { Log.d("OnDeviceClassifier", "$assetName input: $it") }
            session?.outputNames?.forEach { Log.d("OnDeviceClassifier", "$assetName output: $it") }
            session
        } catch (e: Exception) {
            Log.e("OnDeviceClassifier", "Failed to load $assetName", e)
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
            val shape = longArrayOf(1, combinedFeatures.size.toLong())
            
            // Predict phishing
            val phishingScores = phishingSession?.let { session ->
                val inputName = session.inputNames.firstOrNull() ?: return@let floatArrayOf(0f, 0f)
                createInputTensor(combinedFeatures, shape).use { tensor ->
                    session.run(mapOf(inputName to tensor)).use { result ->
                        result.firstValue().asFloatArray(floatArrayOf(0f, 0f))
                    }
                }
            } ?: floatArrayOf(0f, 0f)
            val isPhishing = phishingScores.size > 1 && phishingScores[1] > 0.5f
            val phishScore = if (phishingScores.size > 1) phishingScores[1] else 0f
            
            if (isPhishing) {
                reasons.add("Phishing score: ${String.format("%.2f", phishScore)}")
            }
            
            // Predict is_otp
            val isotpScores = isotpSession?.let { session ->
                val inputName = session.inputNames.firstOrNull() ?: return@let floatArrayOf(0f, 0f)
                createInputTensor(combinedFeatures, shape).use { tensor ->
                    session.run(mapOf(inputName to tensor)).use { result ->
                        result.firstValue().asFloatArray(floatArrayOf(0f, 0f))
                    }
                }
            } ?: floatArrayOf(0f, 0f)
            val isOtp = isotpScores.size > 1 && isotpScores[1] > 0.5f
            
            // Predict intent (only if OTP)
            var otpIntent: String? = null
            if (isOtp) {
                val intentScores = intentSession?.let { session ->
                    val inputName = session.inputNames.firstOrNull() ?: return@let FloatArray(9)
                    createInputTensor(combinedFeatures, shape).use { tensor ->
                        session.run(mapOf(inputName to tensor)).use { result ->
                            result.firstValue().asFloatArray(FloatArray(9))
                        }
                    }
                } ?: FloatArray(9)
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
            Log.e("OnDeviceClassifier", "Prediction failed", e)
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

    private fun createInputTensor(features: FloatArray, shape: LongArray): OnnxTensor =
        OnnxTensor.createTensor(ortEnv!!, features.copyOf(), shape)
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


package com.smsclassifier.app.classification

interface Classifier {
    suspend fun predict(input: MessageFeatures): Prediction
    fun isAvailable(): Boolean
}


package com.smsclassifier.app.classification

data class MessageFeatures(
    val text: String,
    val sender: String? = null,
    val tfidfVector: FloatArray? = null, // Dense TF-IDF vector
    val heuristicFeatures: FloatArray? = null // Heuristic features array
)


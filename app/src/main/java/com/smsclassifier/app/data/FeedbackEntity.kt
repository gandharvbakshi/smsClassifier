package com.smsclassifier.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "feedback")
data class FeedbackEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val messageId: Long,
    val originalIsOtp: Boolean?,
    val originalOtpIntent: String?,
    val originalIsPhishing: Boolean?,
    val originalPhishScore: Float?,
    val userCorrection: String, // JSON with user's corrections
    val timestamp: Long = System.currentTimeMillis()
)


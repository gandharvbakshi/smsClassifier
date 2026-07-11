package com.smsclassifier.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "misclassification_logs")
data class MisclassificationLogEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val messageId: Long,
    val sender: String,
    val body: String,
    val predictedIsOtp: Boolean?,
    val predictedOtpIntent: String?,
    val correctedOtpIntent: String? = null,
    val predictedIsPhishing: Boolean?,
    val predictedPhishScore: Float? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val feedbackKind: String? = null,
    val userNote: String? = null,
    val uploaded: Boolean = false,
    val lastUploadAttemptAt: Long? = null,
    val uploadAttempts: Int = 0
)

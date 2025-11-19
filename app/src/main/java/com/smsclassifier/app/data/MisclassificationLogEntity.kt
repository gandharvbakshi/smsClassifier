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
    val predictedIsPhishing: Boolean?,
    val createdAt: Long = System.currentTimeMillis(),
    val userNote: String? = null
)



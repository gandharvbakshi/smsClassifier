package com.smsclassifier.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverters

@Entity(tableName = "messages")
@TypeConverters(Converters::class)
data class MessageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val sender: String,
    val body: String,
    val ts: Long, // timestamp
    val language: String? = null,
    val featuresJson: String? = null, // JSON string of extracted features
    val isOtp: Boolean? = null,
    val otpIntent: String? = null,
    val isPhishing: Boolean? = null,
    val phishScore: Float? = null, // 0.0 to 1.0
    val reasonsJson: String? = null, // JSON array of reason strings
    val reviewed: Boolean = false,
    val version: Int = 1 // Schema version for migrations
)


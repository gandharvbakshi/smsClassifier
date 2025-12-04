package com.smsclassifier.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverters

@Entity(tableName = "messages")
@TypeConverters(Converters::class)
data class MessageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    // SMS Handler fields
    val sender: String,  // For incoming: sender number, For outgoing: recipient number
    val body: String,
    val ts: Long, // timestamp (date)
    val threadId: Long = 0,  // Thread ID (calculated from phone number)
    val type: Int = 1,  // 1=received, 2=sent, 3=draft, 4=outbox, 5=failed
    val read: Boolean = false,
    val seen: Boolean = false,
    val status: Int? = null,  // For sent messages: -1=pending, 0=complete, etc.
    val serviceCenter: String? = null,
    val dateSent: Long? = null,  // For sent messages
    
    // Classification fields (existing)
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


package com.smsclassifier.app.data

/**
 * Represents a conversation/thread with summary information.
 * This is computed from messages, not stored in database.
 */
data class ThreadInfo(
    val threadId: Long,
    val address: String,  // Phone number or contact name
    val snippet: String,  // Last message preview
    val lastMessageTime: Long,
    val messageCount: Int,
    val unreadCount: Int,
    val latestMessage: MessageEntity? = null  // Latest message for classification badges
)


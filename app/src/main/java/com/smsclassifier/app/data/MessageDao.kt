package com.smsclassifier.app.data

import androidx.paging.PagingSource
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface MessageDao {
    @Query("SELECT * FROM messages ORDER BY ts DESC")
    fun getAllPaged(): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages WHERE isOtp = 1 ORDER BY ts DESC")
    fun getOtpPaged(): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages WHERE isPhishing = 1 ORDER BY ts DESC")
    fun getPhishingPaged(): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages WHERE reviewed = 0 AND (isPhishing IS NULL OR phishScore IS NULL) ORDER BY ts DESC")
    fun getNeedsReviewPaged(): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages WHERE (isOtp IS NULL OR isOtp = 0) AND (isPhishing IS NULL OR isPhishing = 0) ORDER BY ts DESC")
    fun getGeneralPaged(): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages WHERE body LIKE :query OR sender LIKE :query ORDER BY ts DESC")
    fun searchPaged(query: String): PagingSource<Int, MessageEntity>

    @Query("SELECT * FROM messages ORDER BY ts DESC LIMIT 1")
    fun getLatestMessage(): Flow<MessageEntity?>

    @Query("SELECT * FROM messages WHERE id = :id")
    suspend fun getById(id: Long): MessageEntity?

    @Query("SELECT COUNT(*) FROM messages")
    fun getTotalCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM messages WHERE isOtp = 1")
    fun getOtpCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM messages WHERE isPhishing = 1")
    fun getPhishingCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM messages WHERE reviewed = 0 AND (isPhishing IS NULL OR phishScore IS NULL)")
    fun getNeedsReviewCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM messages WHERE (isOtp IS NULL OR isOtp = 0) AND (isPhishing IS NULL OR isPhishing = 0)")
    fun getGeneralCount(): Flow<Int>
    
    // Count distinct threads (conversations) instead of individual messages
    @Query("SELECT COUNT(DISTINCT threadId) FROM messages WHERE isOtp = 1")
    suspend fun getOtpThreadCount(): Int

    @Query("SELECT COUNT(DISTINCT threadId) FROM messages WHERE isPhishing = 1")
    suspend fun getPhishingThreadCount(): Int

    @Query("SELECT COUNT(DISTINCT threadId) FROM messages WHERE reviewed = 0 AND (isPhishing IS NULL OR phishScore IS NULL)")
    suspend fun getNeedsReviewThreadCount(): Int

    @Query("SELECT COUNT(DISTINCT threadId) FROM messages WHERE (isOtp IS NULL OR isOtp = 0) AND (isPhishing IS NULL OR isPhishing = 0)")
    suspend fun getGeneralThreadCount(): Int

    @Query("SELECT * FROM messages WHERE isOtp IS NULL OR isPhishing IS NULL ORDER BY ts DESC LIMIT :limit")
    suspend fun getUnclassified(limit: Int): List<MessageEntity>

    @Query("SELECT * FROM messages ORDER BY ts DESC")
    suspend fun getAllMessages(): List<MessageEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(message: MessageEntity): Long

    @Update
    suspend fun update(message: MessageEntity)

    @Query("UPDATE messages SET reviewed = 1 WHERE id = :id")
    suspend fun markReviewed(id: Long)

    @Query("DELETE FROM messages WHERE id = :id")
    suspend fun delete(id: Long)
    
    // Thread/Conversation queries
    @Query("SELECT * FROM messages WHERE threadId = :threadId ORDER BY ts ASC")
    suspend fun getMessagesByThread(threadId: Long): List<MessageEntity>
    
    @Query("SELECT * FROM messages WHERE threadId = :threadId ORDER BY ts ASC")
    fun getMessagesByThreadPaged(threadId: Long): PagingSource<Int, MessageEntity>
    
    @Query("SELECT DISTINCT threadId FROM messages ORDER BY (SELECT MAX(ts) FROM messages m WHERE m.threadId = messages.threadId) DESC")
    suspend fun getAllThreadIds(): List<Long>
    
    @Query("SELECT * FROM messages WHERE threadId = :threadId ORDER BY ts DESC LIMIT 1")
    suspend fun getLatestMessageByThread(threadId: Long): MessageEntity?
    
    @Query("SELECT COUNT(*) FROM messages WHERE threadId = :threadId")
    suspend fun getMessageCountForThread(threadId: Long): Int
    
    @Query("SELECT * FROM messages WHERE threadId = :threadId AND read = 0")
    suspend fun getUnreadMessagesByThread(threadId: Long): List<MessageEntity>
    
    @Query("UPDATE messages SET read = 1, seen = 1 WHERE threadId = :threadId")
    suspend fun markThreadAsRead(threadId: Long)
    
    @Query("UPDATE messages SET read = 1, seen = 1 WHERE id = :id")
    suspend fun markAsRead(id: Long)
    
    @Query("SELECT COUNT(*) FROM messages WHERE read = 0")
    fun getUnreadCount(): Flow<Int>
    
    @Query("SELECT COUNT(*) FROM messages WHERE threadId = :threadId AND read = 0")
    suspend fun getUnreadCountForThread(threadId: Long): Int
    
    @Query("DELETE FROM messages WHERE threadId = :threadId")
    suspend fun deleteThread(threadId: Long)
}


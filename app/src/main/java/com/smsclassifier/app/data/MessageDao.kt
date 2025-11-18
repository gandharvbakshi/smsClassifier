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
}


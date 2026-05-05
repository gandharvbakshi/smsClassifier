package com.smsclassifier.app.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface MisclassificationLogDao {
    @Query("SELECT * FROM misclassification_logs ORDER BY createdAt DESC")
    fun getAll(): Flow<List<MisclassificationLogEntity>>

    @Insert
    suspend fun insert(log: MisclassificationLogEntity)

    @Delete
    suspend fun delete(log: MisclassificationLogEntity)

    @Query("DELETE FROM misclassification_logs")
    suspend fun clear()

    @Query(
        "SELECT * FROM misclassification_logs WHERE uploaded = 0 " +
            "ORDER BY createdAt ASC LIMIT :limit"
    )
    suspend fun getPendingUpload(limit: Int): List<MisclassificationLogEntity>

    @Query(
        "UPDATE misclassification_logs SET uploaded = 1, lastUploadAttemptAt = :ts WHERE id = :id"
    )
    suspend fun markUploaded(id: Long, ts: Long)

    @Query(
        "UPDATE misclassification_logs SET uploadAttempts = uploadAttempts + 1, " +
            "lastUploadAttemptAt = :ts WHERE id = :id"
    )
    suspend fun markUploadAttempt(id: Long, ts: Long)
}

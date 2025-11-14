package com.smsclassifier.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface FeedbackDao {
    @Query("SELECT * FROM feedback ORDER BY timestamp DESC")
    fun getAll(): Flow<List<FeedbackEntity>>

    @Insert
    suspend fun insert(feedback: FeedbackEntity): Long

    @Query("DELETE FROM feedback")
    suspend fun deleteAll()
}


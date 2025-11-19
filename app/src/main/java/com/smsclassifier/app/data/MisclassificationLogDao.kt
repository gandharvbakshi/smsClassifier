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
}



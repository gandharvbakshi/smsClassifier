package com.smsclassifier.app.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface NotificationDebugLogDao {
    @Query("SELECT * FROM notification_debug_logs ORDER BY createdAt DESC LIMIT 50")
    fun getRecent(): Flow<List<NotificationDebugLogEntity>>

    @Insert
    suspend fun insert(log: NotificationDebugLogEntity)

    @Query("DELETE FROM notification_debug_logs")
    suspend fun clear()

    @Query(
        "DELETE FROM notification_debug_logs WHERE id NOT IN " +
            "(SELECT id FROM notification_debug_logs ORDER BY createdAt DESC LIMIT 50)"
    )
    suspend fun pruneOldest()
}

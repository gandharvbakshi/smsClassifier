package com.smsclassifier.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [MessageEntity::class, FeedbackEntity::class, MisclassificationLogEntity::class],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao
    abstract fun feedbackDao(): FeedbackDao
    abstract fun misclassificationLogDao(): MisclassificationLogDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "sms_classifier.db"
                )
                    .addMigrations(MIGRATION_1_2)
                    .build()
                INSTANCE = instance
                instance
            }
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS misclassification_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        messageId INTEGER NOT NULL,
                        sender TEXT NOT NULL,
                        body TEXT NOT NULL,
                        predictedIsOtp INTEGER,
                        predictedOtpIntent TEXT,
                        predictedIsPhishing INTEGER,
                        createdAt INTEGER NOT NULL,
                        userNote TEXT
                    )
                    """.trimIndent()
                )
            }
        }
    }
}


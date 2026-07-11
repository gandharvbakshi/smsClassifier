package com.smsclassifier.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        MessageEntity::class,
        FeedbackEntity::class,
        MisclassificationLogEntity::class,
        NotificationDebugLogEntity::class
    ],
    version = 10,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao
    abstract fun feedbackDao(): FeedbackDao
    abstract fun misclassificationLogDao(): MisclassificationLogDao
    abstract fun notificationDebugLogDao(): NotificationDebugLogDao

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
                    .addMigrations(
                        MIGRATION_1_2,
                        MIGRATION_2_3,
                        MIGRATION_3_4,
                        MIGRATION_4_5,
                        MIGRATION_5_6,
                        MIGRATION_6_7,
                        MIGRATION_7_8,
                        MIGRATION_8_9,
                        MIGRATION_9_10
                    )
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

        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                // Add new columns for SMS handler functionality
                db.execSQL("ALTER TABLE messages ADD COLUMN threadId INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE messages ADD COLUMN type INTEGER NOT NULL DEFAULT 1")
                db.execSQL("ALTER TABLE messages ADD COLUMN read INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE messages ADD COLUMN seen INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE messages ADD COLUMN status INTEGER")
                db.execSQL("ALTER TABLE messages ADD COLUMN serviceCenter TEXT")
                db.execSQL("ALTER TABLE messages ADD COLUMN dateSent INTEGER")
                
                // Calculate thread_id for existing messages based on sender
                // Use a simpler approach: hash the sender string
                val cursor = db.query("SELECT id, sender FROM messages WHERE sender IS NOT NULL AND sender != ''")
                try {
                    while (cursor.moveToNext()) {
                        val id = cursor.getLong(0)
                        val sender = cursor.getString(1)
                        // Normalize phone number and calculate hash
                        val normalized = sender.replace(Regex("[^0-9]"), "")
                        val threadId = if (normalized.isNotEmpty()) {
                            normalized.hashCode().toLong().and(0x7FFFFFFF)
                        } else {
                            0L
                        }
                        db.execSQL("UPDATE messages SET threadId = ? WHERE id = ?", arrayOf(threadId, id))
                    }
                } finally {
                    cursor.close()
                }
            }
        }

        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN predictedPhishScore REAL"
                )
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN uploaded INTEGER NOT NULL DEFAULT 0"
                )
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN lastUploadAttemptAt INTEGER"
                )
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN uploadAttempts INTEGER NOT NULL DEFAULT 0"
                )
            }
        }

        private val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS notification_debug_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        createdAt INTEGER NOT NULL,
                        messageId INTEGER NOT NULL,
                        sender TEXT NOT NULL,
                        isOtp INTEGER NOT NULL,
                        otpCode TEXT,
                        channelId TEXT NOT NULL,
                        styleClass TEXT NOT NULL,
                        categoryStr TEXT,
                        priority INTEGER NOT NULL,
                        extraTitle TEXT,
                        extraText TEXT,
                        extraBigText TEXT,
                        extraSubText TEXT,
                        hasCustomContentView INTEGER NOT NULL,
                        hasCustomBigContentView INTEGER NOT NULL,
                        rawBody TEXT NOT NULL
                    )
                    """.trimIndent()
                )
            }
        }

        private val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN feedbackKind TEXT"
                )
            }
        }

        private val MIGRATION_6_7 = object : Migration(6, 7) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE messages ADD COLUMN userCorrected INTEGER NOT NULL DEFAULT 0")
            }
        }

        private val MIGRATION_7_8 = object : Migration(7, 8) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE messages ADD COLUMN sourceProviderId INTEGER")
                db.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_messages_sourceProviderId ON messages(sourceProviderId)"
                )
            }
        }

        private val MIGRATION_8_9 = object : Migration(8, 9) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_messages_threadId_ts ON messages(threadId, ts)"
                )
                db.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_messages_ts ON messages(ts)"
                )
            }
        }

        private val MIGRATION_9_10 = object : Migration(9, 10) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "ALTER TABLE misclassification_logs ADD COLUMN correctedOtpIntent TEXT"
                )
            }
        }
    }
}


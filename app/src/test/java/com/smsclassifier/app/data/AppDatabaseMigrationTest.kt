package com.smsclassifier.app.data

import androidx.sqlite.db.SupportSQLiteDatabase
import org.junit.Assert.assertTrue
import org.junit.Test
import java.lang.reflect.InvocationHandler
import java.lang.reflect.Method
import java.lang.reflect.Proxy

class AppDatabaseMigrationTest {

    @Test
    fun appDatabase_declaresMigration9To10() {
        assertTrue(
            AppDatabase::class.java.declaredFields.any { it.name == "MIGRATION_9_10" }
        )
    }

    @Test
    fun migration9To10_addsCorrectedOtpIntentColumn() {
        val migration = migrationByName("MIGRATION_9_10")
        val statements = mutableListOf<String>()
        val database = supportSqliteProxy(statements)

        migration.migrate(database)

        assertTrue(
            statements.any {
                it.contains("ALTER TABLE misclassification_logs ADD COLUMN correctedOtpIntent TEXT")
            }
        )
    }

    private fun migrationByName(fieldName: String): androidx.room.migration.Migration {
        val field = AppDatabase::class.java.getDeclaredField(fieldName).apply {
            isAccessible = true
        }
        return field.get(null) as androidx.room.migration.Migration
    }

    private fun supportSqliteProxy(statements: MutableList<String>): SupportSQLiteDatabase {
        val handler = InvocationHandler { _: Any, method: Method, args: Array<out Any>? ->
            when (method.name) {
                "execSQL" -> {
                    statements += args?.firstOrNull()?.toString().orEmpty()
                    null
                }
                "toString" -> "SupportSQLiteDatabaseProxy"
                else -> defaultReturn(method.returnType)
            }
        }
        return Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java),
            handler
        ) as SupportSQLiteDatabase
    }

    private fun defaultReturn(returnType: Class<*>): Any? {
        return when (returnType) {
            java.lang.Boolean.TYPE -> false
            java.lang.Byte.TYPE -> 0.toByte()
            java.lang.Short.TYPE -> 0.toShort()
            java.lang.Integer.TYPE -> 0
            java.lang.Long.TYPE -> 0L
            java.lang.Float.TYPE -> 0f
            java.lang.Double.TYPE -> 0.0
            java.lang.Character.TYPE -> '\u0000'
            else -> null
        }
    }
}

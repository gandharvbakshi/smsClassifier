package com.smsclassifier.app.ui.viewmodel

import android.content.Context
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.MisclassificationLogDao
import com.smsclassifier.app.data.MisclassificationLogEntity
import com.smsclassifier.app.data.SettingsRepository
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class LogsViewModel(
    database: AppDatabase,
    context: Context
) : ViewModel() {
    private val dao: MisclassificationLogDao = database.misclassificationLogDao()
    private val settingsRepository = SettingsRepository(context.applicationContext)

    private val _feedbackUploadEnabled =
        MutableStateFlow(settingsRepository.feedbackUploadEnabled)
    val feedbackUploadEnabled: StateFlow<Boolean> = _feedbackUploadEnabled.asStateFlow()

    fun refreshFeedbackEnabledFromPrefs() {
        _feedbackUploadEnabled.value = settingsRepository.feedbackUploadEnabled
    }

    val logs = dao.getAll().stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = emptyList()
    )

    fun delete(log: MisclassificationLogEntity) {
        viewModelScope.launch { dao.delete(log) }
    }

    fun clear() {
        viewModelScope.launch { dao.clear() }
    }

    fun exportAll(
        context: Context,
        logs: List<MisclassificationLogEntity>,
        onExported: (android.net.Uri?) -> Unit
    ) {
        viewModelScope.launch {
            if (logs.isEmpty()) {
                onExported(null)
                return@launch
            }
            val file = writeCsv(context, logs)
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                file
            )
            onExported(uri)
        }
    }

    fun exportSingle(
        context: Context,
        log: MisclassificationLogEntity,
        onExported: (android.net.Uri?) -> Unit
    ) {
        exportAll(context, listOf(log), onExported)
    }

    private fun writeCsv(context: Context, logs: List<MisclassificationLogEntity>): File {
        val dir = File(context.filesDir, "log_exports").apply { mkdirs() }
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val file = File(dir, "misclassification_logs_$timestamp.csv")
        FileWriter(file).use { writer ->
            writer.appendLine(
                "id,messageId,sender,body,predictedIsOtp,predictedOtpIntent,predictedIsPhishing,predictedPhishScore,userNote,createdAt,uploaded,uploadAttempts,lastUploadAttemptAt"
            )
            logs.forEach { log ->
                val sanitizedBody = log.body.replace("\"", "\"\"")
                val sanitizedNote = log.userNote?.replace("\"", "\"\"") ?: ""
                writer.appendLine(
                    "${log.id},${log.messageId},\"${log.sender}\",\"$sanitizedBody\",${log.predictedIsOtp}," +
                        "\"${log.predictedOtpIntent ?: ""}\",${log.predictedIsPhishing},${log.predictedPhishScore ?: ""}," +
                        "\"$sanitizedNote\",${log.createdAt},${log.uploaded},${log.uploadAttempts},${log.lastUploadAttemptAt ?: ""}"
                )
            }
        }
        return file
    }
}

package com.smsclassifier.app.ui.components

import android.content.ContentResolver
import android.text.format.DateUtils
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.BulkSmsDeletePlan
import com.smsclassifier.app.data.BulkSmsDeletion
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.data.SmsDeletionIdentity
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

internal class BulkDeleteSelection {
    var active by mutableStateOf(false)
        private set
    var rows by mutableStateOf(emptyMap<Long, SmsDeletionIdentity?>())
        private set
    var busy by mutableStateOf(false)
    var plan by mutableStateOf<BulkSmsDeletePlan?>(null)
    var status by mutableStateOf<String?>(null)

    fun start() {
        active = true
        status = null
        plan = null
    }

    fun clear() {
        active = false
        rows = emptyMap()
        plan = null
    }

    fun toggle(id: Long, identity: SmsDeletionIdentity?) {
        if (!busy && plan == null) {
            rows = if (id in rows) rows - id else rows + (id to identity)
            status = null
        }
    }
}

@Composable
internal fun rememberBulkDeleteSelection(scopeKey: Any? = Unit): BulkDeleteSelection =
    remember(scopeKey) { BulkDeleteSelection() }

@Composable
internal fun BulkDeleteControls(
    selection: BulkDeleteSelection,
    deletion: BulkSmsDeletion,
    conversations: Boolean = false,
    canSelect: Boolean,
    modifier: Modifier = Modifier,
    contentResolver: ContentResolver? = null
) {
    val context = LocalContext.current
    val resolver = contentResolver ?: context.contentResolver
    val scope = rememberCoroutineScope()
    val unit = if (conversations) "conversations" else "messages"
    val controlsLocked = selection.busy || selection.plan != null
    BackHandler(enabled = selection.active && selection.plan == null) {
        if (!selection.busy) selection.clear()
    }
    BackHandler(enabled = selection.plan != null && !selection.busy) {
        selection.plan = null
    }

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (selection.active) {
                Text(
                    text = if (selection.busy) "Working…" else "${selection.rows.size} selected",
                    modifier = Modifier.weight(1f).padding(start = 12.dp).semantics {
                        liveRegion = LiveRegionMode.Polite
                    },
                    style = MaterialTheme.typography.bodyMedium
                )
                TextButton(
                    onClick = selection::clear,
                    enabled = !controlsLocked,
                    modifier = Modifier
                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                        .testTag("bulk-cancel")
                ) { Text("Cancel") }
                TextButton(
                    enabled = selection.rows.isNotEmpty() && !controlsLocked,
                    modifier = Modifier
                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                        .testTag("bulk-request-delete"),
                    onClick = {
                        val rows = selection.rows
                        selection.busy = true
                        selection.status = null
                        scope.launch {
                            try {
                                val plan = deletion.prepare(resolver, rows, conversations)
                                if (plan.messages.isEmpty()) {
                                    selection.status = "No selected $unit are still available to delete."
                                    selection.clear()
                                } else {
                                    selection.plan = plan
                                }
                            } catch (e: CancellationException) {
                                throw e
                            } catch (_: Exception) {
                                selection.status = "Could not load the selected $unit. Try again."
                            } finally {
                                selection.busy = false
                            }
                        }
                    }
                ) { Text("Delete") }
            } else {
                TextButton(
                    onClick = selection::start,
                    enabled = canSelect,
                    modifier = Modifier
                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                        .testTag("bulk-select")
                ) { Text("Select $unit") }
            }
        }
        selection.status?.let {
            Text(
                text = it,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp).semantics {
                    liveRegion = LiveRegionMode.Polite
                },
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }

    selection.plan?.let { plan ->
        val messages = smsCount(plan.messages.size, "message")
        val confirmedScope = if (plan.conversations) {
            "${smsCount(plan.conversationCount, "conversation")} containing $messages"
        } else {
            messages
        }
        AlertDialog(
            onDismissRequest = { selection.plan = null },
            title = { Text("Delete $confirmedScope?") },
            text = {
                val description = if (plan.conversations) {
                    "This permanently deletes the $messages included in the selected conversations, including messages outside the current filter."
                } else {
                    "This permanently deletes the $messages included in this selection."
                }
                Text(description)
            },
            dismissButton = {
                TextButton(
                    onClick = { selection.plan = null },
                    modifier = Modifier
                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                        .testTag("bulk-dismiss")
                ) { Text("Cancel") }
            },
            confirmButton = {
                TextButton(
                    modifier = Modifier
                        .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                        .testTag("bulk-confirm"),
                    onClick = {
                        selection.plan = null
                        selection.busy = true
                        scope.launch {
                            try {
                                val result = deletion.delete(resolver, plan)
                                val summary = mutableListOf<String>()
                                if (result.removed > 0) summary += "Deleted ${smsCount(result.removed, "message")}."
                                if (result.alreadyAbsent > 0) {
                                    summary += "${smsCount(result.alreadyAbsent, "message")} already gone."
                                }
                                if (result.failed > 0) {
                                    summary += "Could not finish deleting ${smsCount(result.failed, "message")}."
                                }
                                selection.status = summary.joinToString(" ")
                                selection.clear()
                            } finally {
                                selection.busy = false
                            }
                        }
                    }
                ) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            }
        )
    }
}

@Composable
internal fun BulkDeleteMessageRow(
    selection: BulkDeleteSelection,
    message: MessageEntity,
    title: String = message.sender
) {
    BulkDeleteRow(
        selection, message.id, title, message.body, message.ts,
        identity = SmsDeletionIdentity(message)
    )
}

@Composable
internal fun BulkDeleteRow(
    selection: BulkDeleteSelection,
    id: Long,
    title: String,
    preview: String,
    timestamp: Long,
    modifier: Modifier = Modifier,
    identity: SmsDeletionIdentity? = null
) {
    val checked = id in selection.rows
    val context = LocalContext.current
    val enabled = !selection.busy && selection.plan == null
    Row(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp)
            .testTag("bulk-row-$id")
            .semantics(mergeDescendants = true) {}
            .toggleable(
                value = checked,
                enabled = enabled,
                role = Role.Checkbox,
                onValueChange = { isChecked ->
                    if (isChecked != checked) selection.toggle(id, identity)
                }
            )
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Checkbox(
            checked = checked,
            onCheckedChange = null,
            enabled = enabled,
            modifier = Modifier.clearAndSetSemantics {}
        )
        Column {
            Text(title, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                DateUtils.formatDateTime(context, timestamp, DateUtils.FORMAT_SHOW_DATE or DateUtils.FORMAT_SHOW_TIME),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(preview, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)
        }
    }
}

private fun smsCount(count: Int, unit: String): String = "$count $unit${if (count == 1) "" else "s"}"

package com.smsclassifier.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Forward
import androidx.compose.material.icons.filled.Report
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.ClassificationUtils
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun MessageBubble(
    message: MessageEntity,
    onCopy: (() -> Unit)? = null,
    onDelete: (() -> Unit)? = null,
    onForward: (() -> Unit)? = null,
    onReport: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var showMenu by remember { mutableStateOf(false) }
    val clipboardManager = LocalClipboardManager.current
    val isSent = message.type == 2 // 2 = sent
    
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalArrangement = if (isSent) Arrangement.End else Arrangement.Start
    ) {
        Box {
            Box(
                modifier = Modifier
                    .widthIn(max = 280.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        if (isSent) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.surfaceVariant
                        }
                    )
                    .clickable { showMenu = true }
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        text = message.body,
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isSent) {
                            MaterialTheme.colorScheme.onPrimary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = formatTimestamp(message.ts),
                        style = MaterialTheme.typography.bodySmall,
                        color = if (isSent) {
                            MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f)
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                        },
                        modifier = Modifier.align(Alignment.End)
                    )
                }
            }
            
            // Dropdown menu for actions
            DropdownMenu(
                expanded = showMenu,
                onDismissRequest = { showMenu = false }
            ) {
                val otpCode = ClassificationUtils.extractOtpCode(message.body)
                if (otpCode != null) {
                    DropdownMenuItem(
                        text = { Text("Copy OTP ($otpCode)") },
                        leadingIcon = { Icon(Icons.Default.ContentCopy, null) },
                        onClick = {
                            clipboardManager.setText(AnnotatedString(otpCode))
                            onCopy?.invoke()
                            showMenu = false
                        }
                    )
                }
                DropdownMenuItem(
                    text = { Text("Copy") },
                    leadingIcon = { Icon(Icons.Default.ContentCopy, null) },
                    onClick = {
                        clipboardManager.setText(AnnotatedString(message.body))
                        onCopy?.invoke()
                        showMenu = false
                    }
                )
                if (onForward != null) {
                    DropdownMenuItem(
                        text = { Text("Forward") },
                        leadingIcon = { Icon(Icons.Default.Forward, null) },
                        onClick = {
                            onForward()
                            showMenu = false
                        }
                    )
                }
                if (onReport != null) {
                    DropdownMenuItem(
                        text = { Text("Report Classification") },
                        leadingIcon = { Icon(Icons.Default.Report, null) },
                        onClick = {
                            onReport()
                            showMenu = false
                        }
                    )
                }
                if (onDelete != null) {
                    DropdownMenuItem(
                        text = { Text("Delete", color = MaterialTheme.colorScheme.error) },
                        leadingIcon = { 
                            Icon(
                                Icons.Default.Delete, 
                                null,
                                tint = MaterialTheme.colorScheme.error
                            ) 
                        },
                        onClick = {
                            onDelete()
                            showMenu = false
                        }
                    )
                }
            }
        }
    }
}

private fun formatTimestamp(timestamp: Long): String {
    val date = Date(timestamp)
    val now = Date()
    val diff = now.time - date.time
    
    return when {
        diff < 60000 -> "Just now" // Less than 1 minute
        diff < 3600000 -> "${diff / 60000}m ago" // Less than 1 hour
        diff < 86400000 -> "${diff / 3600000}h ago" // Less than 1 day
        else -> SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()).format(date)
    }
}


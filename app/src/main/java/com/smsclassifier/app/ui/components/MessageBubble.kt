package com.smsclassifier.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.ExperimentalFoundationApi
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.badges.ClassificationBadge
import com.smsclassifier.app.util.ClassificationUtils
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalFoundationApi::class)
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
    val isSent = message.type == 2

    val otpCode = remember(message.body, message.sender, message.isOtp) {
        ClassificationUtils.extractOtpForCopy(message.body, message.sender, message.isOtp)
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = if (isSent) Arrangement.End else Arrangement.Start
    ) {
        Box {
            Column(
                modifier = Modifier
                    .widthIn(max = 320.dp)
                    .clip(
                        RoundedCornerShape(
                            topStart = 18.dp,
                            topEnd = 18.dp,
                            bottomEnd = if (isSent) 4.dp else 18.dp,
                            bottomStart = if (isSent) 18.dp else 4.dp
                        )
                    )
                    .background(
                        if (isSent) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.surfaceVariant
                    )
                    .combinedClickable(
                        onClick = { showMenu = true },
                        onLongClick = { showMenu = true }
                    )
                    .padding(horizontal = 14.dp, vertical = 10.dp)
            ) {
                if (otpCode != null && !isSent) {
                    OtpHighlight(
                        otpCode = otpCode,
                        body = message.body,
                        onTapCopy = {
                            clipboardManager.setText(AnnotatedString(otpCode))
                            onCopy?.invoke()
                        }
                    )
                } else {
                    Text(
                        text = message.body,
                        style = MaterialTheme.typography.bodyLarge,
                        color = if (isSent) MaterialTheme.colorScheme.onPrimary
                        else MaterialTheme.colorScheme.onSurface
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = formatTimestamp(message.ts),
                    style = MaterialTheme.typography.labelSmall,
                    color = if (isSent) MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.75f)
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.align(Alignment.End)
                )
            }

            DropdownMenu(
                expanded = showMenu,
                onDismissRequest = { showMenu = false }
            ) {
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
                    text = { Text("Copy message") },
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
                        onClick = { onForward(); showMenu = false }
                    )
                }
                if (onReport != null) {
                    DropdownMenuItem(
                        text = { Text("Report classification") },
                        leadingIcon = { Icon(Icons.Default.Report, null) },
                        onClick = { onReport(); showMenu = false }
                    )
                }
                if (onDelete != null) {
                    DropdownMenuItem(
                        text = {
                            Text("Delete", color = MaterialTheme.colorScheme.error)
                        },
                        leadingIcon = {
                            Icon(Icons.Default.Delete, null, tint = MaterialTheme.colorScheme.error)
                        },
                        onClick = { onDelete(); showMenu = false }
                    )
                }
            }
        }
    }
}

@Composable
private fun OtpHighlight(
    otpCode: String,
    body: String,
    onTapCopy: () -> Unit
) {
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            ClassificationBadge(
                type = com.smsclassifier.app.ui.badges.BadgeType.OTP
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Verification code",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = otpCode,
            fontSize = 36.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 4.sp,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(8.dp))
        FilledTonalButton(
            onClick = onTapCopy,
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
        ) {
            Icon(
                Icons.Default.ContentCopy,
                contentDescription = null,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text("Copy code", style = MaterialTheme.typography.labelLarge)
        }
        Spacer(modifier = Modifier.height(10.dp))
        Text(
            text = body,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
        )
    }
}

private fun formatTimestamp(timestamp: Long): String {
    val date = Date(timestamp)
    val now = Date()
    val diff = now.time - date.time

    return when {
        diff < 60_000 -> "Just now"
        diff < 3_600_000 -> "${diff / 60_000}m ago"
        diff < 86_400_000 -> SimpleDateFormat("h:mm a", Locale.getDefault()).format(date)
        else -> SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()).format(date)
    }
}

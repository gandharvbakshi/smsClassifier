package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.NotificationDebugLogEntity
import com.smsclassifier.app.ui.viewmodel.NotificationDebugViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.abs

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationDebugScreen(
    viewModel: NotificationDebugViewModel,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val logs by viewModel.logs.collectAsState()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "Notification debug",
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.titleMedium
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (logs.isNotEmpty()) {
                        IconButton(onClick = viewModel::clear) {
                            Icon(Icons.Default.Delete, contentDescription = "Clear")
                        }
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            if (logs.isEmpty()) {
                Text(
                    text = "No notifications captured yet. Send / receive an SMS to see what " +
                        "the system OTP-autofill scraper would have seen.",
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(logs, key = { it.id }) { log ->
                        DebugCard(log)
                    }
                }
            }
        }
    }
}

@Composable
private fun DebugCard(log: NotificationDebugLogEntity) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = log.sender,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                if (log.isOtp) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = MaterialTheme.colorScheme.primaryContainer
                    ) {
                        Text(
                            text = "OTP ${log.otpCode ?: "?"}",
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }
                }
                Text(
                    text = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                        .format(Date(log.createdAt)),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            kvLine("style", log.styleClass)
            kvLine("category", log.categoryStr ?: "—")
            kvLine("hasCustomCV", log.hasCustomContentView.toString())
            kvLine("hasCustomBigCV", log.hasCustomBigContentView.toString())
            kvLine("EXTRA_TITLE", log.extraTitle ?: "—")
            kvLine("EXTRA_TEXT", log.extraText ?: "—")
            kvLine("EXTRA_BIG_TEXT", log.extraBigText ?: "—")
            kvLine("EXTRA_SUB_TEXT", log.extraSubText ?: "—")
            kvLine("rawBody", log.rawBody)

            val verdict = autofillVerdict(log)
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = if (verdict.first) MaterialTheme.colorScheme.tertiaryContainer
                else MaterialTheme.colorScheme.errorContainer,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Autofill scraper would ${if (verdict.first) "FIND" else "MISS"} the OTP — ${verdict.second}",
                    modifier = Modifier.padding(10.dp),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

@Composable
private fun kvLine(label: String, value: String) {
    Row {
        Text(
            text = label,
            modifier = Modifier.width(112.dp),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            fontFamily = FontFamily.Monospace
        )
    }
}

private fun autofillVerdict(log: NotificationDebugLogEntity): Pair<Boolean, String> {
    val haystacks = listOfNotNull(log.extraText, log.extraBigText)
    if (haystacks.isEmpty()) return false to "no EXTRA_TEXT / EXTRA_BIG_TEXT set"
    val keyword = Regex("(?i)\\b(otp|code|verification|password|pin)\\b")
    val codeRx = Regex("\\b\\d{4,8}\\b")
    for (h in haystacks) {
        val codes = codeRx.findAll(h).toList()
        if (codes.isEmpty()) continue
        val keywords = keyword.findAll(h).toList()
        if (keywords.isEmpty()) continue
        val pairs = codes.flatMap { c -> keywords.map { k -> abs(c.range.first - k.range.first) } }
        val nearest = pairs.minOrNull() ?: Int.MAX_VALUE
        if (nearest <= 50) return true to "code within $nearest chars of an OTP keyword"
    }
    return false to "code present but no OTP keyword within 50 chars (or vice versa)"
}

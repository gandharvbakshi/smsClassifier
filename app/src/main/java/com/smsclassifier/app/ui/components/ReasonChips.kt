package com.smsclassifier.app.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.theme.DoNotShareOrange
import com.smsclassifier.app.ui.theme.InfoGray
import com.smsclassifier.app.ui.theme.SuspiciousAmber

@Composable
fun ReasonChips(
    reasons: List<String>,
    modifier: Modifier = Modifier
) {
    LazyRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(reasons) { reason ->
            val tone = determineReasonTone(reason)
            val colors = when (tone) {
                ReasonTone.WARNING -> AssistChipDefaults.assistChipColors(
                    containerColor = DoNotShareOrange.copy(alpha = 0.15f),
                    labelColor = DoNotShareOrange
                )
                ReasonTone.ALERT -> AssistChipDefaults.assistChipColors(
                    containerColor = SuspiciousAmber.copy(alpha = 0.2f),
                    labelColor = SuspiciousAmber
                )
                ReasonTone.INFO -> AssistChipDefaults.assistChipColors(
                    containerColor = InfoGray.copy(alpha = 0.12f),
                    labelColor = InfoGray
                )
            }
            AssistChip(
                onClick = { },
                label = { Text(reason, style = MaterialTheme.typography.labelSmall) },
                colors = colors
            )
        }
    }
}

private enum class ReasonTone { INFO, WARNING, ALERT }

private fun determineReasonTone(reason: String): ReasonTone {
    val text = reason.lowercase()
    return when {
        text.contains("never share") || text.contains("do not share") -> ReasonTone.WARNING
        text.contains("phishing") || text.contains("failed") -> ReasonTone.ALERT
        else -> ReasonTone.INFO
    }
}


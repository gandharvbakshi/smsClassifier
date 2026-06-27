package com.smsclassifier.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.util.ClassificationUtils
import com.smsclassifier.app.ui.theme.PhishingRed
import com.smsclassifier.app.ui.theme.PhishingRedSoft
import com.smsclassifier.app.ui.theme.SafeGreen
import com.smsclassifier.app.ui.theme.SafeGreenSoft
import com.smsclassifier.app.ui.theme.SuspiciousAmber
import com.smsclassifier.app.ui.theme.SuspiciousAmberText
import com.smsclassifier.app.ui.theme.avatarColor

enum class MessageVerdictTone { SAFE, OTP, SCAM }

@Composable
fun MessageSenderCard(
    friendlySender: String,
    rawSender: String,
    timestamp: String,
    body: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.Top
            ) {
                Surface(
                    modifier = Modifier.size(40.dp),
                    shape = CircleShape,
                    color = avatarColor(rawSender),
                    contentColor = Color.White
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = friendlySender.firstOrNull()?.uppercaseChar()?.toString() ?: "?",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = friendlySender,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    if (friendlySender != rawSender) {
                        Text(
                            text = rawSender,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Text(
                    text = timestamp,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.End
                )
            }
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp),
                color = MaterialTheme.colorScheme.outlineVariant
            ) {}
            Text(
                text = body,
                style = MaterialTheme.typography.bodyLarge,
                lineHeight = MaterialTheme.typography.bodyLarge.lineHeight
            )
        }
    }
}

@Composable
fun MessageVerdictBand(
    tone: MessageVerdictTone,
    title: String,
    body: String,
    modifier: Modifier = Modifier
) {
    val dark = isSystemInDarkTheme()
    val contentColor = when (tone) {
        MessageVerdictTone.SAFE -> SafeGreen
        MessageVerdictTone.OTP -> MaterialTheme.colorScheme.primary
        MessageVerdictTone.SCAM -> MaterialTheme.colorScheme.error
    }
    val containerColor = when (tone) {
        MessageVerdictTone.SAFE -> if (dark) SafeGreen.copy(alpha = 0.18f) else SafeGreenSoft
        MessageVerdictTone.OTP -> MaterialTheme.colorScheme.primaryContainer
        MessageVerdictTone.SCAM -> if (dark) PhishingRed.copy(alpha = 0.18f) else PhishingRedSoft
    }
    val icon = when (tone) {
        MessageVerdictTone.SAFE -> Icons.Default.CheckCircle
        MessageVerdictTone.OTP -> Icons.Default.ContentCopy
        MessageVerdictTone.SCAM -> Icons.Default.Warning
    }

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = containerColor,
        contentColor = contentColor
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(22.dp)
            )
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = body,
                    style = MaterialTheme.typography.bodyMedium,
                    color = contentColor
                )
            }
        }
    }
}

@Composable
fun ScamRiskMeter(
    level: ClassificationUtils.RiskLevel,
    label: String,
    modifier: Modifier = Modifier
) {
    val activeCount = when (level) {
        ClassificationUtils.RiskLevel.HIGH -> 3
        ClassificationUtils.RiskLevel.MEDIUM -> 2
        else -> 1
    }
    val activeColor = when (level) {
        ClassificationUtils.RiskLevel.HIGH -> PhishingRed
        ClassificationUtils.RiskLevel.MEDIUM -> SuspiciousAmber
        else -> SafeGreen
    }
    val labelColor = when (level) {
        ClassificationUtils.RiskLevel.HIGH -> PhishingRed
        ClassificationUtils.RiskLevel.MEDIUM -> SuspiciousAmberText
        else -> SafeGreen
    }

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Scam risk",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                repeat(3) { index ->
                    Surface(
                        modifier = Modifier
                            .weight(1f)
                            .height(5.dp),
                        shape = RoundedCornerShape(100.dp),
                        color = if (index < activeCount) {
                            activeColor
                        } else {
                            MaterialTheme.colorScheme.surfaceVariant
                        }
                    ) {}
                }
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = labelColor
            )
        }
    }
}

@Composable
fun WhyList(
    title: String,
    reasons: List<String>,
    tone: MessageVerdictTone = MessageVerdictTone.SAFE,
    modifier: Modifier = Modifier
) {
    val icon = when (tone) {
        MessageVerdictTone.SCAM -> Icons.Default.Warning
        MessageVerdictTone.OTP -> Icons.Default.Info
        MessageVerdictTone.SAFE -> Icons.Default.CheckCircle
    }
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text(
            text = title.uppercase(),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        reasons.forEach { reason ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.Top
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = reason,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

@Composable
fun ReportWrongButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        colors = ButtonDefaults.outlinedButtonColors(
            contentColor = MaterialTheme.colorScheme.onSurfaceVariant
        )
    ) {
        Icon(
            imageVector = Icons.Default.Info,
            contentDescription = null,
            modifier = Modifier.size(18.dp)
        )
        Text(
            text = "Report a mistake",
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(start = 8.dp)
        )
    }
}

@Composable
fun DeleteMessageButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.error,
            contentColor = MaterialTheme.colorScheme.onError
        )
    ) {
        Icon(
            imageVector = Icons.Default.Delete,
            contentDescription = null,
            modifier = Modifier.size(20.dp)
        )
        Text(
            text = "Delete message",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(start = 8.dp)
        )
    }
}

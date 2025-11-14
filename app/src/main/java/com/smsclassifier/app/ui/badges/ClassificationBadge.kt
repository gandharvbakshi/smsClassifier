package com.smsclassifier.app.ui.badges

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.theme.*

enum class BadgeType(val label: String, val color: androidx.compose.ui.graphics.Color) {
    SAFE("Safe", SafeGreen),
    SUSPICIOUS("Suspicious", SuspiciousAmber),
    PHISHING("Phishing", PhishingRed),
    OTP("OTP", OTPBlue)
}

@Composable
fun ClassificationBadge(
    type: BadgeType,
    modifier: Modifier = Modifier
) {
    Surface(
        color = type.color.copy(alpha = 0.2f),
        shape = MaterialTheme.shapes.small,
        modifier = modifier
    ) {
        Text(
            text = type.label,
            style = MaterialTheme.typography.labelSmall,
            color = type.color,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}


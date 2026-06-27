package com.smsclassifier.app.ui.badges

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.theme.OTPBlue
import com.smsclassifier.app.ui.theme.OTPBlueSoft
import com.smsclassifier.app.ui.theme.PhishingRed
import com.smsclassifier.app.ui.theme.PhishingRedSoft
import com.smsclassifier.app.ui.theme.SafeGreen
import com.smsclassifier.app.ui.theme.SafeGreenSoft
import com.smsclassifier.app.ui.theme.SuspiciousAmberSoft
import com.smsclassifier.app.ui.theme.SuspiciousAmberText

enum class BadgeType(
    val label: String,
    val color: Color,
    val backgroundColor: Color
) {
    SAFE("No scam signs", SafeGreen, SafeGreenSoft),
    SUSPICIOUS("Suspicious", SuspiciousAmberText, SuspiciousAmberSoft),
    PHISHING("Scam", PhishingRed, PhishingRedSoft),
    OTP("OTP", OTPBlue, OTPBlueSoft)
}

@Composable
fun ClassificationBadge(
    type: BadgeType,
    modifier: Modifier = Modifier
) {
    Surface(
        color = type.backgroundColor,
        shape = RoundedCornerShape(50),
        modifier = modifier
    ) {
        Text(
            text = type.label,
            style = MaterialTheme.typography.labelLarge,
            color = type.color,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}

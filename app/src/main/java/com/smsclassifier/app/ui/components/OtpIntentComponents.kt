package com.smsclassifier.app.ui.components

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.theme.CourierBlue
import com.smsclassifier.app.util.OtpIntentPresentation
import com.smsclassifier.app.util.OtpSharingGuidance

@Composable
fun OtpPurposeLabel(
    presentation: OtpIntentPresentation,
    modifier: Modifier = Modifier,
    centered: Boolean = false
) {
    Text(
        text = presentation.label,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = if (centered) TextAlign.Center else TextAlign.Start,
        maxLines = 2,
        overflow = TextOverflow.Ellipsis,
        modifier = modifier
    )
}

@Composable
fun OtpSafetyLine(
    presentation: OtpIntentPresentation,
    modifier: Modifier = Modifier,
    centered: Boolean = false
) {
    val message = presentation.safetyMessage ?: return
    val color = when (presentation.sharingGuidance) {
        OtpSharingGuidance.NEVER_SHARE -> MaterialTheme.colorScheme.error
        OtpSharingGuidance.COURIER_ONLY -> {
            if (isSystemInDarkTheme()) MaterialTheme.colorScheme.primary else CourierBlue
        }
        OtpSharingGuidance.NONE -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = if (centered) Arrangement.Center else Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (presentation.sharingGuidance == OtpSharingGuidance.NEVER_SHARE) {
            Icon(
                imageVector = Icons.Default.WarningAmber,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(6.dp))
        }
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = color,
            textAlign = if (centered) TextAlign.Center else TextAlign.Start,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

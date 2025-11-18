package com.smsclassifier.app.ui.badges

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.theme.CourierBlue
import com.smsclassifier.app.ui.theme.DoNotShareOrange
import com.smsclassifier.app.ui.theme.InfoGray

enum class SensitivityType(val label: String, val color: androidx.compose.ui.graphics.Color) {
    DO_NOT_SHARE("Do Not Share", DoNotShareOrange),
    COURIER_ONLY("Share with Courier", CourierBlue),
    INFO("Info", InfoGray),
    NONE("", InfoGray)
}

@Composable
fun SensitivityBadge(
    type: SensitivityType,
    modifier: Modifier = Modifier
) {
    if (type == SensitivityType.NONE) return

    Surface(
        color = type.color.copy(alpha = 0.15f),
        shape = MaterialTheme.shapes.small,
        modifier = modifier
    ) {
        Text(
            text = type.label,
            style = MaterialTheme.typography.labelSmall,
            color = type.color,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}


package com.smsclassifier.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.OtpIntentResolver
import com.smsclassifier.app.util.SenderNameResolver
import com.smsclassifier.app.util.formatFriendlyTime
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun OtpHeroCard(
    message: MessageEntity,
    code: String,
    onCopy: () -> Unit,
    modifier: Modifier = Modifier
) {
    val presentation = OtpIntentResolver.resolve(message)
    val friendlySender = SenderNameResolver.resolve(message.sender)
    val talkBackDescription = OtpIntentResolver.talkBackDescription(
        presentation = presentation,
        senderName = friendlySender,
        code = code
    )
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.onSurface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OtpPurposeLabel(
                presentation = presentation,
                centered = true,
                modifier = Modifier.fillMaxWidth()
            )
            OtpCodeText(code = code)
            OtpSafetyLine(presentation = presentation, centered = true)
            Spacer(modifier = Modifier.height(2.dp))
            CopyOtpButton(
                onClick = onCopy,
                accessibilityLabel = talkBackDescription
            )
        }
    }
}

@Composable
fun OtpListCard(
    message: MessageEntity,
    code: String,
    onClick: () -> Unit,
    onCopy: () -> Unit,
    modifier: Modifier = Modifier
) {
    val friendlySender = SenderNameResolver.resolve(message.sender)
    val presentation = OtpIntentResolver.resolve(message)
    val talkBackDescription = OtpIntentResolver.talkBackDescription(
        presentation = presentation,
        senderName = friendlySender,
        code = code
    )

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClickLabel = "Open OTP details", onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.onSurface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "OTP",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = friendlySender,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Text(
                    text = formatFriendlyTime(message.ts),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1
                )
            }
            OtpPurposeLabel(
                presentation = presentation,
                centered = true,
                modifier = Modifier.fillMaxWidth()
            )
            OtpCodeText(code = code)
            OtpSafetyLine(presentation = presentation, centered = true)
            CopyOtpButton(
                onClick = onCopy,
                accessibilityLabel = talkBackDescription
            )
        }
    }
}

@Composable
private fun OtpCodeText(code: String) {
    Text(
        text = code,
        fontSize = 46.sp,
        lineHeight = 54.sp,
        fontWeight = FontWeight.Bold,
        fontFamily = FontFamily.Monospace,
        letterSpacing = 4.sp,
        color = MaterialTheme.colorScheme.onSurface,
        textAlign = TextAlign.Center,
        maxLines = 1,
        modifier = Modifier
            .fillMaxWidth()
            .semantics {
                contentDescription = code.filter(Char::isDigit).toCharArray().joinToString(" ")
            }
    )
}

@Composable
private fun CopyOtpButton(
    onClick: () -> Unit,
    accessibilityLabel: String
) {
    var copiedState by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    var resetJob by remember { mutableStateOf<Job?>(null) }

    LaunchedEffect(copiedState) {
        if (!copiedState) {
            resetJob?.cancel()
            resetJob = null
        }
    }

    Button(
        onClick = {
            onClick()
            resetJob?.cancel()
            copiedState = true
            resetJob = scope.launch {
                delay(2_000)
                copiedState = false
            }
        },
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp)
            .semantics { contentDescription = accessibilityLabel }
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = if (copiedState) Icons.Default.Check else Icons.Default.ContentCopy,
                contentDescription = null,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (copiedState) "OTP copied" else "Copy OTP",
                style = MaterialTheme.typography.titleMedium
            )
        }
    }
}

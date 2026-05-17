package com.smsclassifier.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.BasicAlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.google.android.play.core.review.ReviewManagerFactory
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.feedback.SatisfactionPromptKind
import com.smsclassifier.app.feedback.SatisfactionPromptManager
import com.smsclassifier.app.ui.theme.Spacing
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

private fun isSuppressedRoute(route: String?): Boolean {
    if (route == null) return false
    if (route == "consent_onboarding" || route == "phone_auth") return true
    if (route.startsWith("paywall/")) return true
    return false
}

/**
 * Phase 6 — one satisfaction dialog per app session when eligible.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SatisfactionPromptHost(
    consentCompleted: Boolean,
    currentRoute: String? = null,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val mgr = remember { SatisfactionPromptManager(context) }

    var prompt by remember { mutableStateOf<SatisfactionPromptKind?>(null) }
    var sessionShown by remember { mutableStateOf(false) }

    LaunchedEffect(consentCompleted, currentRoute) {
        if (!consentCompleted || sessionShown) return@LaunchedEffect
        if (isSuppressedRoute(currentRoute)) return@LaunchedEffect
        kotlinx.coroutines.delay(1800)
        if (isSuppressedRoute(currentRoute)) return@LaunchedEffect
        val next = mgr.peekNextPrompt() ?: return@LaunchedEffect
        prompt = next
        sessionShown = true
        AppContainer.telemetry.logEvent(
            "satisfaction_prompted",
            mapOf("prompt_kind" to if (next == SatisfactionPromptKind.D1) "d1" else "d5")
        )
    }

    fun finish(kind: SatisfactionPromptKind) {
        mgr.markDismissedSession()
        mgr.markPromptFinished(kind)
        prompt = null
    }

    fun onEmoji(score: Int) {
        val kind = prompt ?: return
        val kindStr = if (kind == SatisfactionPromptKind.D1) "d1" else "d5"
        AppContainer.telemetry.logEvent(
            "satisfaction_response",
            mapOf("prompt_kind" to kindStr, "score" to score)
        )
        val activity = context as? android.app.Activity
        if (kind == SatisfactionPromptKind.D5 && score >= 4 && activity != null) {
            scope.launch {
                runCatching {
                    val rm = ReviewManagerFactory.create(context)
                    val flow = rm.requestReviewFlow().await()
                    rm.launchReviewFlow(activity, flow).await()
                }
                finish(kind)
            }
        } else {
            finish(kind)
        }
    }

    if (prompt != null) {
        val kind = prompt!!
        BasicAlertDialog(
            onDismissRequest = { finish(kind) },
            modifier = modifier
        ) {
            Surface(shape = MaterialTheme.shapes.large) {
                Column(modifier = Modifier.padding(Spacing.xl)) {
                    Text(
                        text = if (kind == SatisfactionPromptKind.D1) "How's it going so far?"
                        else "How's the app feeling?",
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(Spacing.sm))
                    Text(
                        text = "Tap a face. Tap 1 if it's bad, 5 if you love it.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(Spacing.xl))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        val faces = listOf("😡", "🙁", "😐", "🙂", "😍")
                        val labels = listOf("Bad", "Meh", "OK", "Good", "Love it")
                        faces.forEachIndexed { index, face ->
                            val n = index + 1
                            FaceButton(
                                emoji = face,
                                label = labels[index],
                                ratingValue = n,
                                onTap = { onEmoji(n) }
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(Spacing.lg))
                    TextButton(
                        onClick = { finish(kind) },
                        modifier = Modifier.align(Alignment.End)
                    ) {
                        Text(
                            text = "Maybe later",
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun FaceButton(
    emoji: String,
    label: String,
    ratingValue: Int,
    onTap: () -> Unit
) {
    val desc = "Rate $ratingValue of 5: $label"
    Column(
        modifier = Modifier
            .clip(MaterialTheme.shapes.medium)
            .clickable(onClick = onTap)
            .heightIn(min = 72.dp)
            .padding(horizontal = Spacing.sm, vertical = Spacing.sm)
            .semantics { contentDescription = desc },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.surfaceVariant),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = emoji,
                style = MaterialTheme.typography.headlineSmall,
                textAlign = TextAlign.Center
            )
        }
        Spacer(modifier = Modifier.height(Spacing.xs))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
    }
}

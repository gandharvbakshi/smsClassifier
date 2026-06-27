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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.BasicAlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import com.smsclassifier.app.BuildConfig
import com.smsclassifier.app.data.SettingsRepository
import com.smsclassifier.app.feedback.SatisfactionPromptKind
import com.smsclassifier.app.feedback.SatisfactionPromptManager
import com.smsclassifier.app.feedback.FeedbackRequest
import com.smsclassifier.app.feedback.FeedbackUploader
import com.smsclassifier.app.ui.theme.Spacing
import com.smsclassifier.app.util.SmsRedactor
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
    var privateFeedbackPrompt by remember { mutableStateOf<Pair<SatisfactionPromptKind, Int>?>(null) }
    var reviewPrompt by remember { mutableStateOf<SatisfactionPromptKind?>(null) }
    var feedbackComment by remember { mutableStateOf("") }
    var feedbackSending by remember { mutableStateOf(false) }

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
        privateFeedbackPrompt = null
        reviewPrompt = null
        feedbackComment = ""
        feedbackSending = false
    }

    fun onEmoji(score: Int) {
        val kind = prompt ?: return
        val kindStr = if (kind == SatisfactionPromptKind.D1) "d1" else "d5"
        AppContainer.telemetry.logEvent(
            "satisfaction_response",
            mapOf("prompt_kind" to kindStr, "score" to score)
        )
        if (score <= 3) {
            prompt = null
            feedbackComment = ""
            privateFeedbackPrompt = kind to score
            return
        }
        if (score >= 4) {
            AppContainer.telemetry.logEvent(
                "satisfaction_positive",
                mapOf("prompt_kind" to kindStr, "score" to score)
            )
        }
        val activity = context as? android.app.Activity
        if (kind == SatisfactionPromptKind.D5 && score >= 4 && activity != null) {
            prompt = null
            reviewPrompt = kind
        } else {
            finish(kind)
        }
    }

    fun sendPrivateFeedback(kind: SatisfactionPromptKind, score: Int) {
        if (feedbackSending) return
        val appContext = context.applicationContext
        val kindStr = if (kind == SatisfactionPromptKind.D1) "d1" else "d5"
        feedbackSending = true
        scope.launch {
            val ok = runCatching {
                val settings = SettingsRepository(appContext)
                val installId = settings.installId
                val cleanedComment = feedbackComment.trim().take(PRIVATE_FEEDBACK_MAX_CHARS)
                val body = if (cleanedComment.isBlank()) {
                    "Satisfaction score $score of 5"
                } else {
                    SmsRedactor.redactForTraining(cleanedComment, installId)
                }
                FeedbackUploader().upload(
                    FeedbackRequest(
                        installId = installId,
                        firebaseUid = null,
                        appVersionCode = BuildConfig.VERSION_CODE,
                        appVersionName = BuildConfig.VERSION_NAME,
                        sender = "APP_FEEDBACK",
                        body = body,
                        predictedIsOtp = null,
                        predictedOtpIntent = null,
                        predictedIsPhishing = null,
                        predictedPhishScore = null,
                        userCorrection = null,
                        userNote = body.takeIf { cleanedComment.isNotBlank() },
                        clientCreatedAt = System.currentTimeMillis(),
                        feedbackKind = "satisfaction_$kindStr",
                        satisfactionScore = score
                    )
                ).isSuccess
            }.getOrDefault(false)
            AppContainer.telemetry.logEvent(
                "satisfaction_private_feedback_result",
                mapOf("prompt_kind" to kindStr, "score" to score, "success" to ok.toString())
            )
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
                        val labels = listOf("Bad", "Meh", "OK", "Good", "Love")
                        faces.forEachIndexed { index, face ->
                            val n = index + 1
                            FaceButton(
                                emoji = face,
                                label = labels[index],
                                ratingValue = n,
                                modifier = Modifier.weight(1f),
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

    privateFeedbackPrompt?.let { (kind, score) ->
        AlertDialog(
            onDismissRequest = { finish(kind) },
            title = { Text("Tell us what went wrong") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    Text(
                        text = "Your note goes privately to the developer. We do not attach any SMS from your phone.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = feedbackComment,
                        onValueChange = { feedbackComment = it.take(PRIVATE_FEEDBACK_MAX_CHARS) },
                        label = { Text("Feedback") },
                        minLines = 3,
                        enabled = !feedbackSending
                    )
                }
            },
            confirmButton = {
                Button(
                    enabled = !feedbackSending,
                    onClick = { sendPrivateFeedback(kind, score) }
                ) {
                    Text(if (feedbackSending) "Sending..." else "Send")
                }
            },
            dismissButton = {
                TextButton(
                    enabled = !feedbackSending,
                    onClick = { finish(kind) }
                ) {
                    Text("Skip")
                }
            }
        )
    }

    reviewPrompt?.let { kind ->
        val activity = context as? android.app.Activity
        AlertDialog(
            onDismissRequest = { finish(kind) },
            title = { Text("Glad it's helping") },
            text = {
                Text(
                    text = "Would you like to rate SMS Classifier on Google Play?",
                    style = MaterialTheme.typography.bodyMedium
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        scope.launch {
                            if (activity != null) {
                                runCatching {
                                    val rm = ReviewManagerFactory.create(context)
                                    val flow = rm.requestReviewFlow().await()
                                    rm.launchReviewFlow(activity, flow).await()
                                }
                            }
                            finish(kind)
                        }
                    }
                ) {
                    Text("Rate")
                }
            },
            dismissButton = {
                TextButton(onClick = { finish(kind) }) {
                    Text("Not now")
                }
            }
        )
    }
}

@Composable
private fun FaceButton(
    emoji: String,
    label: String,
    ratingValue: Int,
    modifier: Modifier = Modifier,
    onTap: () -> Unit
) {
    val desc = "Rate $ratingValue of 5: $label"
    Column(
        modifier = modifier
            .clip(MaterialTheme.shapes.medium)
            .clickable(onClick = onTap)
            .heightIn(min = 72.dp)
            .padding(horizontal = 2.dp, vertical = Spacing.sm)
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

private const val PRIVATE_FEEDBACK_MAX_CHARS = 600

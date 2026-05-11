package com.smsclassifier.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.google.android.play.core.review.ReviewManagerFactory
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.feedback.SatisfactionPromptKind
import com.smsclassifier.app.feedback.SatisfactionPromptManager
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
        val faceNames = listOf("angry", "unhappy", "neutral", "smiling", "loving")
        BasicAlertDialog(
            onDismissRequest = { finish(kind) },
            modifier = modifier
        ) {
            Surface(shape = MaterialTheme.shapes.large) {
                Column(modifier = Modifier.padding(24.dp)) {
                    Text(
                        text = if (kind == SatisfactionPromptKind.D1) "How's it going?"
                        else "Quick check-in",
                        style = MaterialTheme.typography.headlineSmall
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Tap an emoji (1 = lowest, 5 = best)",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        val faces = listOf("😡", "😕", "😐", "🙂", "😍")
                        faces.forEachIndexed { index, face ->
                            val n = index + 1
                            val desc = "Rate $n of 5: ${faceNames[index]}"
                            TextButton(
                                onClick = { onEmoji(n) },
                                modifier = Modifier.semantics { contentDescription = desc }
                            ) {
                                Text(face)
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    TextButton(
                        onClick = { finish(kind) },
                        modifier = Modifier.align(Alignment.End)
                    ) {
                        Text("Skip")
                    }
                }
            }
        }
    }
}

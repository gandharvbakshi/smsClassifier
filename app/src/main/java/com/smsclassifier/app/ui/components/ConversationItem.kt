package com.smsclassifier.app.ui.components

import android.net.Uri
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.smsclassifier.app.data.ThreadInfo
import com.smsclassifier.app.ui.badges.ClassificationBadge
import com.smsclassifier.app.ui.badges.SensitivityBadge
import com.smsclassifier.app.ui.badges.SensitivityType
import com.smsclassifier.app.ui.theme.SuspiciousAmber
import com.smsclassifier.app.ui.theme.SuspiciousAmberSoft
import com.smsclassifier.app.ui.theme.avatarColor
import com.smsclassifier.app.util.ClassificationUtils
import com.smsclassifier.app.util.SenderNameResolver
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun ConversationItem(
    thread: ThreadInfo,
    displayName: String? = null,
    contactPhotoUri: Uri? = null,
    onClick: () -> Unit,
    onLongClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val nameToShow = displayName ?: SenderNameResolver.resolve(thread.address)
    val isUnread = thread.unreadCount > 0
    val risk = ClassificationUtils.riskLevelForThread(thread.latestMessage)
    val accentColor = when (risk) {
        ClassificationUtils.RiskLevel.HIGH -> MaterialTheme.colorScheme.error
        ClassificationUtils.RiskLevel.MEDIUM -> SuspiciousAmber
        ClassificationUtils.RiskLevel.LOW -> SuspiciousAmberSoft
        ClassificationUtils.RiskLevel.NONE -> Color.Transparent
    }
    val ringColor = if (risk == ClassificationUtils.RiskLevel.HIGH) {
        MaterialTheme.colorScheme.error
    } else {
        null
    }

    Surface(
        color = MaterialTheme.colorScheme.surface,
        modifier = modifier
            .fillMaxWidth()
            .combinedClickable(
                onClick = onClick,
                onLongClick = { onLongClick?.invoke() }
            )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ContactAvatar(
                name = nameToShow,
                photoUri = contactPhotoUri,
                size = 40.dp,
                ringColor = ringColor
            )

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = nameToShow,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = if (isUnread) FontWeight.Bold else FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    if (accentColor != Color.Transparent) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(accentColor)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(
                        text = formatTimestamp(thread.lastMessageTime),
                        style = MaterialTheme.typography.labelMedium,
                        color = if (isUnread) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = if (isUnread) FontWeight.SemiBold else FontWeight.Normal
                    )
                }

                Spacer(modifier = Modifier.height(2.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = thread.snippet,
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isUnread) MaterialTheme.colorScheme.onSurface
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = if (isUnread) FontWeight.Medium else FontWeight.Normal,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    if (isUnread) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(
                            modifier = Modifier
                                .size(18.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = if (thread.unreadCount > 99) "99+" else thread.unreadCount.toString(),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onPrimary,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                thread.latestMessage?.let { message ->
                    val sensitivity = ClassificationUtils.sensitivityType(message)
                    val hasCloudRiskResult = message.isPhishing != null || message.phishScore != null
                    val showRiskBadge = message.isPhishing == true ||
                        (message.phishScore ?: 0f) >= 0.3f ||
                        (hasCloudRiskResult && message.isOtp == true)
                    if (showRiskBadge || sensitivity != SensitivityType.NONE) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            if (showRiskBadge) {
                                ClassificationBadge(type = ClassificationUtils.riskBadgeType(message))
                            }
                            SensitivityBadge(type = sensitivity)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ContactAvatar(
    name: String,
    photoUri: Uri? = null,
    size: androidx.compose.ui.unit.Dp = 48.dp,
    ringColor: Color? = null,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val initial = name.firstOrNull()?.uppercaseChar()?.toString() ?: "?"
    val color = avatarColor(name)

    @Composable
    fun AvatarCore() {
        Box(
            modifier = Modifier
                .size(size)
                .clip(CircleShape)
                .background(color),
            contentAlignment = Alignment.Center
        ) {
            if (photoUri != null) {
                AsyncImage(
                    model = ImageRequest.Builder(context)
                        .data(photoUri)
                        .crossfade(true)
                        .build(),
                    contentDescription = name,
                    modifier = Modifier
                        .fillMaxSize()
                        .clip(CircleShape),
                    contentScale = ContentScale.Crop
                )
            } else {
                Text(
                    text = initial,
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }

    if (ringColor != null) {
        Box(
            modifier = modifier
                .border(2.dp, ringColor, CircleShape)
                .padding(2.dp),
            contentAlignment = Alignment.Center
        ) {
            AvatarCore()
        }
    } else {
        Box(modifier = modifier) {
            AvatarCore()
        }
    }
}

private fun formatTimestamp(timestamp: Long): String {
    val date = Date(timestamp)
    val now = Calendar.getInstance()
    val msgCal = Calendar.getInstance().apply { time = date }

    return when {
        sameDay(now, msgCal) -> SimpleDateFormat("h:mm a", Locale.getDefault()).format(date)
        isYesterday(now, msgCal) -> "Yesterday"
        sameWeek(now, msgCal) -> SimpleDateFormat("EEE", Locale.getDefault()).format(date)
        sameYear(now, msgCal) -> SimpleDateFormat("MMM d", Locale.getDefault()).format(date)
        else -> SimpleDateFormat("MMM d, yyyy", Locale.getDefault()).format(date)
    }
}

private fun sameDay(a: Calendar, b: Calendar) =
    a.get(Calendar.YEAR) == b.get(Calendar.YEAR) &&
        a.get(Calendar.DAY_OF_YEAR) == b.get(Calendar.DAY_OF_YEAR)

private fun isYesterday(now: Calendar, msg: Calendar): Boolean {
    val yesterday = (now.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, -1) }
    return sameDay(yesterday, msg)
}

private fun sameWeek(a: Calendar, b: Calendar) =
    a.get(Calendar.YEAR) == b.get(Calendar.YEAR) &&
        a.get(Calendar.WEEK_OF_YEAR) == b.get(Calendar.WEEK_OF_YEAR)

private fun sameYear(a: Calendar, b: Calendar) =
    a.get(Calendar.YEAR) == b.get(Calendar.YEAR)

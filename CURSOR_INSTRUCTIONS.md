# SMS Classifier — Inbox UI Redesign

> **Goal:** Make the inbox feel modern, clean, and efficient. Eliminate the ~40% of vertical space currently wasted at the top, default to a flat "Messages" list (since SMS today is transactional, not conversational), and condense 5 stacked control rows into 1 sticky header.
>
> **Audience:** Cursor / smaller coding models. Each task is self-contained: file path, what to do, why, exact code. Implement tasks in order — later tasks depend on earlier ones.
>
> **Stack:** Jetpack Compose, Material 3, Kotlin. Theme is already defined in `ui/theme/Theme.kt` and `ui/theme/Color.kt` — use existing `MaterialTheme.colorScheme.*` tokens; do not introduce new colors.

---

## Summary of Changes

| # | Task | File(s) |
|---|------|---------|
| 1 | Default ViewMode to `MESSAGES`, not `THREADS` | `InboxViewModel.kt` |
| 2 | Add friendly-name resolver for transactional senders | `util/SenderNameResolver.kt` (NEW) |
| 3 | Replace `CenterAlignedTopAppBar` + `DockedSearchBar` with one compact pill search header | `InboxScreen.kt` |
| 4 | Replace SegmentedButton FilterChips with horizontally scrollable `FilterChip` pills (hide zero counts, format `OTP · 163`) | `components/FilterChips.kt` |
| 5 | Move Threads/Messages mode toggle into an overflow menu in the header | `InboxScreen.kt` |
| 6 | Tighten `ConversationItem` (smaller avatar, less padding, friendly name, risk dot replaces stripe) | `components/ConversationItem.kt` |
| 7 | Tighten `MessageItem` (compact card, friendly name, inline metadata) | `components/MessageItem.kt` |
| 8 | Reposition the FAB so it doesn't cover content; trim the `OtpStrip` to one line | `InboxScreen.kt`, `components/OtpStrip.kt` |
| 9 | (Optional) Drop the "OTPs" bottom-nav tab — it duplicates the OTP filter | `screens/MainScaffold.kt` |

---

## Task 1 — Default to Messages view

**File:** `app/src/main/java/com/smsclassifier/app/ui/viewmodel/InboxViewModel.kt`

**Why:** Modern SMS traffic is transactional (OTPs, banking, deliveries). A flat reverse-chronological message list is more useful than a Threads-grouped list. Threads stays available via overflow.

**Change:** find the line

```kotlin
private val _viewMode = MutableStateFlow(ViewMode.THREADS)
```

and replace with

```kotlin
private val _viewMode = MutableStateFlow(ViewMode.MESSAGES)
```

That's the entire change for this task.

---

## Task 2 — Friendly name resolver (NEW FILE)

**Why:** Senders like `VD-HSBCIN-S`, `VM-ICICIT-S`, `AX-ICICIT-S` are unreadable. Indian SMS sender IDs follow a `<route>-<brand><region>-<entity>` format. Strip the route prefix and trailing `-S`/`-P`/`-T`, normalize known brands.

**Create file:** `app/src/main/java/com/smsclassifier/app/util/SenderNameResolver.kt`

```kotlin
package com.smsclassifier.app.util

/**
 * Resolves Indian transactional/promotional SMS sender IDs to friendly brand names.
 *
 * Input examples → output:
 *   "VD-HSBCIN-S"  → "HSBC"
 *   "VM-ICICIT-S"  → "ICICI Bank"
 *   "AX-ICICIT-S"  → "ICICI Bank"
 *   "JD-AMAZON-S"  → "Amazon"
 *   "+919876543210" → "+91 98765 43210"
 *   "John"         → "John"  (already friendly)
 */
object SenderNameResolver {

    // Known brand mappings. Keys are uppercase, after route prefix/suffix stripped.
    private val brandMap: Map<String, String> = mapOf(
        "HSBCIN" to "HSBC",
        "HSBC" to "HSBC",
        "ICICIT" to "ICICI Bank",
        "ICICIB" to "ICICI Bank",
        "ICICI" to "ICICI Bank",
        "SBIINB" to "SBI",
        "SBIPSG" to "SBI",
        "SBI" to "SBI",
        "HDFCBK" to "HDFC Bank",
        "HDFC" to "HDFC Bank",
        "AXISBK" to "Axis Bank",
        "AXIS" to "Axis Bank",
        "KOTAKB" to "Kotak Bank",
        "KOTAK" to "Kotak Bank",
        "PAYTM" to "Paytm",
        "PHONPE" to "PhonePe",
        "GPAY" to "Google Pay",
        "AMAZON" to "Amazon",
        "FLPKRT" to "Flipkart",
        "MYNTRA" to "Myntra",
        "SWIGGY" to "Swiggy",
        "ZOMATO" to "Zomato",
        "UBER" to "Uber",
        "OLA" to "Ola",
        "JIO" to "Jio",
        "AIRTEL" to "Airtel",
        "VI" to "Vi",
        "BSNL" to "BSNL"
    )

    // Common Indian DLT route prefixes (2 letters, then dash)
    private val routePrefixes = setOf(
        "VD", "VM", "VK", "AX", "AD", "JD", "JM", "JK",
        "BP", "BT", "BX", "BV", "TX", "DM", "MD", "PM", "PD"
    )

    fun resolve(rawSender: String): String {
        if (rawSender.isBlank()) return rawSender

        // Phone numbers: format with spaces for readability
        if (rawSender.startsWith("+") || rawSender.all { it.isDigit() || it == '+' || it == ' ' }) {
            return formatPhoneNumber(rawSender)
        }

        // Already a human name (contains lowercase letters or spaces)
        if (rawSender.any { it.isLowerCase() } || rawSender.contains(' ')) {
            return rawSender
        }

        // Strip Indian DLT format: <2-char-route>-<brand>-<entity>
        var core = rawSender.uppercase()

        // Strip leading route prefix like "VD-" / "AX-"
        val firstDash = core.indexOf('-')
        if (firstDash == 2 && core.substring(0, 2) in routePrefixes) {
            core = core.substring(firstDash + 1)
        }

        // Strip trailing entity suffix like "-S" / "-P" / "-T" / "-G"
        val lastDash = core.lastIndexOf('-')
        if (lastDash > 0 && core.length - lastDash <= 2) {
            core = core.substring(0, lastDash)
        }

        // Look up known brand; otherwise return cleaned-up core
        return brandMap[core] ?: core
    }

    private fun formatPhoneNumber(number: String): String {
        val digits = number.filter { it.isDigit() }
        return when {
            number.startsWith("+91") && digits.length == 12 ->
                "+91 ${digits.substring(2, 7)} ${digits.substring(7)}"
            digits.length == 10 ->
                "${digits.substring(0, 5)} ${digits.substring(5)}"
            else -> number
        }
    }
}
```

---

## Task 3 — Compact pill-search header

**File:** `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`

**Why:** Currently `CenterAlignedTopAppBar` + `DockedSearchBar` consume ~140dp before any content. Replacing them with a single 56dp pill saves ~80dp. The "Messages" title is redundant — the search placeholder ("Search messages") already conveys context, and the bottom-nav already shows "Inbox" is selected.

This task is a series of **seven small surgical edits** in `InboxScreen.kt`. Apply them in order. Each `old_string` is verbatim from the current file — do not paraphrase.

### 3.1 — Remove the `var searchExpanded` line

Find:

```kotlin
    var searchExpanded by remember { mutableStateOf(false) }

```

Replace with: nothing (delete the entire line, including the trailing blank line).

### 3.2 — Remove the `topBar` parameter from the `Scaffold`

Find:

```kotlin
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = "Messages",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                },
                actions = {},
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        floatingActionButton = {
```

Replace with:

```kotlin
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
```

### 3.3 — Replace the `DockedSearchBar` block with the new `InboxHeader` call

Find:

```kotlin
            DockedSearchBar(
                query = searchQuery,
                onQueryChange = viewModel::setSearchQuery,
                onSearch = { searchExpanded = false },
                active = searchExpanded,
                onActiveChange = { searchExpanded = it },
                placeholder = { Text("Search messages") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { viewModel.setSearchQuery("") }) {
                            Icon(Icons.Default.Close, contentDescription = "Clear")
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp)
            ) {
                // Suggestions slot unused for now
            }
```

Replace with:

```kotlin
            InboxHeader(
                searchQuery = searchQuery,
                onSearchChange = viewModel::setSearchQuery,
                viewMode = viewMode,
                onViewModeChange = viewModel::setViewMode,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            )
```

### 3.4 — Remove the `SingleChoiceSegmentedButtonRow` (Threads/Messages toggle)

Find:

```kotlin
            SingleChoiceSegmentedButtonRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                SegmentedButton(
                    selected = viewMode == ViewMode.THREADS,
                    onClick = { viewModel.setViewMode(ViewMode.THREADS) },
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
                ) {
                    Text("Threads")
                }
                SegmentedButton(
                    selected = viewMode == ViewMode.MESSAGES,
                    onClick = { viewModel.setViewMode(ViewMode.MESSAGES) },
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
                ) {
                    Text("Messages")
                }
            }

```

Replace with: nothing (delete the entire block, including the trailing blank line).

### 3.5 — Drop the `filterOrder` argument from the `FilterChips` call

Find:

```kotlin
            FilterChips(
                selectedFilter = filter,
                onFilterSelected = viewModel::setFilter,
                counts = mapOf(
                    FilterType.OTP to otpCount,
                    FilterType.PHISHING to phishingCount,
                    FilterType.NEEDS_REVIEW to needsReviewCount,
                    FilterType.GENERAL to generalCount,
                    FilterType.ALL to totalCount
                ),
                modifier = Modifier.fillMaxWidth(),
                filterOrder = listOf(
                    FilterType.OTP,
                    FilterType.PHISHING,
                    FilterType.NEEDS_REVIEW,
                    FilterType.GENERAL,
                    FilterType.ALL
                )
            )
```

Replace with:

```kotlin
            FilterChips(
                selectedFilter = filter,
                onFilterSelected = viewModel::setFilter,
                counts = mapOf(
                    FilterType.OTP to otpCount,
                    FilterType.PHISHING to phishingCount,
                    FilterType.NEEDS_REVIEW to needsReviewCount,
                    FilterType.GENERAL to generalCount,
                    FilterType.ALL to totalCount
                ),
                modifier = Modifier.fillMaxWidth()
            )
```

### 3.6 — Add the `InboxHeader` composable

Append this composable to the bottom of `InboxScreen.kt` (after the `EmptyInboxState` composable):

```kotlin
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InboxHeader(
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    viewMode: ViewMode,
    onViewModeChange: (ViewMode) -> Unit,
    modifier: Modifier = Modifier
) {
    var menuExpanded by remember { mutableStateOf(false) }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // Search pill — flexible width
        Surface(
            modifier = Modifier
                .weight(1f)
                .height(44.dp),
            shape = RoundedCornerShape(22.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
                BasicTextField(
                    value = searchQuery,
                    onValueChange = onSearchChange,
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = MaterialTheme.colorScheme.onSurface
                    ),
                    cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                    modifier = Modifier.weight(1f),
                    decorationBox = { inner ->
                        if (searchQuery.isEmpty()) {
                            Text(
                                text = "Search messages",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        inner()
                    }
                )
                if (searchQuery.isNotEmpty()) {
                    IconButton(
                        onClick = { onSearchChange("") },
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Clear",
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }
        }

        // Overflow menu — view-mode toggle lives here
        Box {
            IconButton(onClick = { menuExpanded = true }) {
                Icon(Icons.Default.MoreVert, contentDescription = "More options")
            }
            DropdownMenu(
                expanded = menuExpanded,
                onDismissRequest = { menuExpanded = false }
            ) {
                DropdownMenuItem(
                    text = { Text("View as messages") },
                    onClick = {
                        onViewModeChange(ViewMode.MESSAGES)
                        menuExpanded = false
                    },
                    trailingIcon = if (viewMode == ViewMode.MESSAGES) {
                        { Icon(Icons.Default.Check, contentDescription = null) }
                    } else null
                )
                DropdownMenuItem(
                    text = { Text("Group by sender (threads)") },
                    onClick = {
                        onViewModeChange(ViewMode.THREADS)
                        menuExpanded = false
                    },
                    trailingIcon = if (viewMode == ViewMode.THREADS) {
                        { Icon(Icons.Default.Check, contentDescription = null) }
                    } else null
                )
            }
        }
    }
}
```

### 3.7 — Update imports

**Add these imports at the top of `InboxScreen.kt`** (skip any that are already present):

```kotlin
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.graphics.SolidColor
```

**Remove these imports** (each one verbatim — they're no longer referenced after edits 3.2–3.4):

```kotlin
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.DockedSearchBar
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.TopAppBarDefaults
```

---

## Task 4 — Scrollable filter pills

**File:** `app/src/main/java/com/smsclassifier/app/ui/components/FilterChips.kt`

**Why:**
- `SingleChoiceSegmentedButtonRow` forces every label onto one line and wraps text awkwardly (the screenshot shows "Phishing\n(182)" wrapping inside its segment).
- Counts in parentheses look noisy. `OTP · 163` is calmer.
- Hiding zero-count chips reduces clutter.
- A horizontally scrollable row of `FilterChip`s scales to any number of filters.

**Replace the entire file with:**

```kotlin
package com.smsclassifier.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.viewmodel.FilterType

/**
 * Horizontally scrollable filter pills.
 * - Always shows "All".
 * - Other filters appear only when their count > 0 (no empty-state clutter).
 * - Counts shown as " · 163" suffix (or omitted if 0 / null).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FilterChips(
    selectedFilter: FilterType,
    onFilterSelected: (FilterType) -> Unit,
    counts: Map<FilterType, Int>,
    modifier: Modifier = Modifier,
    @Suppress("UNUSED_PARAMETER") filterOrder: List<FilterType> = FilterType.values().toList()
) {
    // Display order: All first, then non-empty categorical filters.
    val orderedFilters = buildList {
        add(FilterType.ALL)
        listOf(
            FilterType.OTP,
            FilterType.PHISHING,
            FilterType.NEEDS_REVIEW,
            FilterType.GENERAL
        ).forEach { f ->
            if ((counts[f] ?: 0) > 0) add(f)
        }
    }

    LazyRow(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(orderedFilters) { filter ->
            val count = counts[filter] ?: 0
            val label = filterLabel(filter) +
                if (count > 0) "  ·  $count" else ""

            FilterChip(
                selected = selectedFilter == filter,
                onClick = { onFilterSelected(filter) },
                label = {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelLarge
                    )
                },
                shape = androidx.compose.foundation.shape.RoundedCornerShape(50),
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    labelColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = selectedFilter == filter,
                    borderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                    selectedBorderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.0f),
                    borderWidth = 1.dp
                )
            )
        }
    }
}

private fun filterLabel(filter: FilterType): String = when (filter) {
    FilterType.OTP -> "OTP"
    FilterType.PHISHING -> "Phishing"
    FilterType.NEEDS_REVIEW -> "Review"
    FilterType.GENERAL -> "Personal"
    FilterType.ALL -> "All"
}
```

> **Note on `FilterChipDefaults.filterChipBorder`:** signature varies across Material 3 versions. If the compiler complains, simplify to `FilterChipDefaults.filterChipBorder(enabled = true, selected = selectedFilter == filter)` and let it use defaults.

---

## Task 5 — (Done as part of Task 3.) Mode toggle moved to overflow.

Verify after Task 3 that the `SingleChoiceSegmentedButtonRow` for Threads/Messages is gone from `InboxScreen.kt`. The mode toggle is now in the overflow `DropdownMenu` inside `InboxHeader`.

---

## Task 6 — Tighten ConversationItem

**File:** `app/src/main/java/com/smsclassifier/app/ui/components/ConversationItem.kt`

**Why:**
- 48dp avatar + 14dp gap + 4dp accent stripe + 16dp padding eats horizontal space.
- 12dp vertical padding is too generous; 10dp gives ~3 more rows on screen.
- The 4dp left accent stripe is invisible for non-risky messages — replace with a small risk dot near the timestamp (only shown when risk > NONE).
- Sender name should run through `SenderNameResolver`.

**Replace the entire file with:**

```kotlin
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
                        style = MaterialTheme.typography.labelSmall,
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
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimary,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                thread.latestMessage?.let { message ->
                    val sensitivity = ClassificationUtils.sensitivityType(message)
                    val showRiskBadge = message.isPhishing == true ||
                        (message.phishScore ?: 0f) >= 0.3f ||
                        message.isOtp == true
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
```

> **What this rewrite does:**
> - Drops the 4dp left accent stripe (the outer `Row(IntrinsicSize.Min) { Box(width=4.dp); innerRow }` wrapper) — replaced by a small risk dot next to the timestamp (only shown when `accentColor != Color.Transparent`).
> - Avatar shrinks 48dp → 40dp; row padding tightens 16/12 → 14/10.
> - Sender name now goes through `SenderNameResolver.resolve(...)` so `VD-HSBCIN-S` becomes `HSBC`.
> - Unread count badge shrinks 20dp → 18dp.
> - Drops `IntrinsicSize` and `fillMaxHeight` imports (no longer needed).
> - `ContactAvatar` and the date helpers are kept verbatim — they're still used by other call sites.

---

## Task 7 — Tighten MessageItem

**File:** `app/src/main/java/com/smsclassifier/app/ui/components/MessageItem.kt`

**Why:** With Messages as the default view, `MessageItem` is the most-rendered component. The current `Card` with 16dp padding and 2dp elevation feels heavy and dated. We want a flat row that matches `ConversationItem`'s rhythm.

**Replace the entire file with:**

```kotlin
package com.smsclassifier.app.ui.components

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.badges.ClassificationBadge
import com.smsclassifier.app.ui.badges.SensitivityBadge
import com.smsclassifier.app.ui.badges.SensitivityType
import com.smsclassifier.app.util.ClassificationUtils
import com.smsclassifier.app.util.SenderNameResolver
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@Composable
fun MessageItem(
    message: MessageEntity,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val friendlyName = SenderNameResolver.resolve(message.sender)
    val initial = friendlyName.firstOrNull()?.uppercaseChar()?.toString() ?: "?"
    val avatarColor = com.smsclassifier.app.ui.theme.avatarColor(friendlyName)

    val isPhish = message.isPhishing == true || (message.phishScore ?: 0f) >= 0.3f
    val riskDotColor: Color = when {
        isPhish -> MaterialTheme.colorScheme.error
        message.isOtp == true -> MaterialTheme.colorScheme.primary
        else -> Color.Transparent
    }

    Surface(
        color = MaterialTheme.colorScheme.surface,
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Compact avatar
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(avatarColor),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = initial,
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = friendlyName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    if (riskDotColor != Color.Transparent) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(riskDotColor)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(
                        text = formatTimestamp(message.ts),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(2.dp))

                Text(
                    text = message.body,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                // Badges + OTP copy — only render if there's something to show
                val sensitivity = ClassificationUtils.sensitivityType(message)
                val showRisk = isPhish || message.isOtp == true
                val otpCode = ClassificationUtils.extractOtpForCopy(
                    message.body,
                    message.sender,
                    message.isOtp
                )

                if (showRisk || sensitivity != SensitivityType.NONE || otpCode != null) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (showRisk) {
                            ClassificationBadge(type = ClassificationUtils.riskBadgeType(message))
                        }
                        if (sensitivity != SensitivityType.NONE) {
                            SensitivityBadge(type = sensitivity)
                        }
                        Spacer(modifier = Modifier.weight(1f))
                        if (otpCode != null) {
                            CopyOtpPill(code = otpCode)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CopyOtpPill(code: String) {
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    Surface(
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.primary,
        contentColor = MaterialTheme.colorScheme.onPrimary,
        modifier = Modifier.clickable {
            clipboard.setText(AnnotatedString(code))
            Toast.makeText(context, "OTP copied", Toast.LENGTH_SHORT).show()
        }
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Icon(
                Icons.Default.ContentCopy,
                contentDescription = null,
                modifier = Modifier.size(12.dp)
            )
            Text(
                text = code,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

private fun formatTimestamp(ts: Long): String {
    val date = Date(ts)
    val now = Calendar.getInstance()
    val msgCal = Calendar.getInstance().apply { time = date }
    val sameDay = now.get(Calendar.YEAR) == msgCal.get(Calendar.YEAR) &&
        now.get(Calendar.DAY_OF_YEAR) == msgCal.get(Calendar.DAY_OF_YEAR)
    val sameYear = now.get(Calendar.YEAR) == msgCal.get(Calendar.YEAR)
    return when {
        sameDay -> SimpleDateFormat("h:mm a", Locale.getDefault()).format(date)
        sameYear -> SimpleDateFormat("MMM d", Locale.getDefault()).format(date)
        else -> SimpleDateFormat("MMM d, yyyy", Locale.getDefault()).format(date)
    }
}
```

> **Why this is better:** flat row (no Card elevation), 40dp avatar, friendly name, inline risk dot, OTP code visible right next to a tappable copy pill. Vertically about 30% more compact than before.

**Also update the `InboxScreen.kt` Messages branch** so messages render in a clean list. Keep the surrounding `Surface { ... }` wrapper unchanged — only the inner `LazyColumn` block changes.

Find this verbatim (it lives inside `ViewMode.MESSAGES -> { ... else -> { Surface(...) { ... } } }`):

```kotlin
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(vertical = 6.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    items(
                                        count = pagingItems.itemCount,
                                        key = pagingItems.itemKey { it.id }
                                    ) { idx ->
                                        val msg = pagingItems[idx] ?: return@items
                                        MessageItem(
                                            message = msg,
                                            onClick = { onMessageClick(msg.id) },
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                    }
                                }
```

Replace with:

```kotlin
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(top = 4.dp, bottom = 88.dp)
                                ) {
                                    items(
                                        count = pagingItems.itemCount,
                                        key = pagingItems.itemKey { it.id }
                                    ) { idx ->
                                        val msg = pagingItems[idx] ?: return@items
                                        MessageItem(
                                            message = msg,
                                            onClick = { onMessageClick(msg.id) },
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                        if (idx < pagingItems.itemCount - 1) {
                                            Divider(
                                                modifier = Modifier.padding(start = 66.dp),
                                                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                                                thickness = 0.5.dp
                                            )
                                        }
                                    }
                                }
```

> The `bottom = 88.dp` is what Task 8b (Option A) would also tell you to add — applying it here means Task 8b for the Messages branch is already done. You still need to apply the same `bottom = 88.dp` to the Threads branch (Task 8b below).

---

## Task 8 — FAB position + OTP strip compact mode

### 8a. Trim the OtpStrip to a single line

**File:** `app/src/main/java/com/smsclassifier/app/ui/components/OtpStrip.kt`

**Why:** Current cards are 2 rows tall (sender label on top, code + copy below). With Messages as the default view we don't need the cards to be that prominent — one compact row each is enough.

This task is two surgical edits in `OtpStrip.kt`.

#### 8a.1 — Replace the entire item `Surface { Column { ... } }` block

> Important: replace the **outer `Surface`**, not just the inner `Column`. The new block is itself a `Surface` — if you only swap the inner content you'll end up with `Surface { Surface { ... } }`.

Find this verbatim (it lives inside the `items(items = messages, key = { it.id }) { msg ->` lambda):

```kotlin
            Surface(
                shape = RoundedCornerShape(18.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier
                    .widthIn(min = 180.dp, max = 240.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .clickable { onCardClick(msg.id) }
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = msg.sender,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = code ?: "OTP",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.weight(1f)
                        )
                        Surface(
                            shape = RoundedCornerShape(50),
                            color = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary,
                            modifier = Modifier.clickable {
                                code?.let { clipboard.setText(AnnotatedString(it)) }
                            }
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Icon(
                                    Icons.Default.ContentCopy,
                                    contentDescription = "Copy OTP",
                                    modifier = Modifier.size(14.dp)
                                )
                                Text(
                                    text = "Copy",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }
            }
```

Replace with:

```kotlin
            Surface(
                shape = RoundedCornerShape(20.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .clickable { onCardClick(msg.id) }
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Column {
                        Text(
                            text = com.smsclassifier.app.util.SenderNameResolver.resolve(msg.sender),
                            style = MaterialTheme.typography.labelSmall,
                            maxLines = 1
                        )
                        Text(
                            text = code ?: "OTP",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Surface(
                        shape = RoundedCornerShape(50),
                        color = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.clickable {
                            code?.let { clipboard.setText(AnnotatedString(it)) }
                        }
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Icon(
                                Icons.Default.ContentCopy,
                                contentDescription = "Copy OTP",
                                modifier = Modifier.size(14.dp)
                            )
                            Text(
                                text = "Copy",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
            }
```

#### 8a.2 — Reduce the `LazyRow` vertical padding

Find this verbatim:

```kotlin
    LazyRow(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
```

Replace with:

```kotlin
    LazyRow(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
```

### 8b. FAB shouldn't sit on the content

**File:** `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`

**Use Option A.** (Option B is provided for reference only at the bottom of this section — do not implement it unless the user explicitly asks.)

**Option A: keep the FAB, add bottom padding to the Threads-branch `LazyColumn` so the last conversation isn't covered.**

> The Messages-branch `LazyColumn` already received `bottom = 88.dp` as part of Task 7. Only the Threads branch needs to change here.

Find this verbatim:

```kotlin
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(vertical = 6.dp)
                                ) {
                                    itemsIndexed(
                                        items = filteredConversations,
                                        key = { _, c -> c.threadId }
                                    ) { index, conversation ->
```

Replace with:

```kotlin
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(top = 6.dp, bottom = 88.dp)
                                ) {
                                    itemsIndexed(
                                        items = filteredConversations,
                                        key = { _, c -> c.threadId }
                                    ) { index, conversation ->
```

---

**Option B (do not apply unless explicitly requested):** replace the FAB with a small `IconButton` in the header. In `InboxHeader` (Task 3), add a third item to the `Row`:

```kotlin
IconButton(onClick = onNewMessageClick) {
    Icon(Icons.Default.Edit, contentDescription = "New message")
}
```

…then remove the `floatingActionButton = { ... }` block from the `Scaffold` and thread `onNewMessageClick` through `InboxHeader` as a parameter.

---

## Task 9 — (Optional) Drop the OTPs bottom-nav tab

**File:** `app/src/main/java/com/smsclassifier/app/ui/screens/MainScaffold.kt`

**Why:** With the OTP filter chip front-and-centre and the OTP strip pinning recent OTPs at the top, a dedicated OTPs tab is redundant. Dropping it gives the remaining 3 tabs more breathing room.

**Change:** in `TopLevelDestinations`, remove the `OTPs` line:

```kotlin
private val TopLevelDestinations = listOf(
    TopLevelDestination("inbox", "Inbox", Icons.Default.Inbox),
    // TopLevelDestination("otp", "OTPs", Icons.Default.Pin),   // <-- REMOVED
    TopLevelDestination("flagged", "Flagged", Icons.Default.Warning),
    TopLevelDestination("settings", "Settings", Icons.Default.Settings)
)
```

> **Important:** the `otp` route is still registered in the navigation graph and may still be reachable from notifications/deeplinks. Leave the `OtpInboxScreen` composable + route registered in `MainActivity.kt` — only remove the bottom-nav entry.
>
> Skip this task if you're unsure; it's purely a cleanup.

---

## Verification checklist

After Cursor finishes, manually verify on a device or emulator:

1. **No giant gap at top** — the search pill sits ~12dp below the status bar.
2. **Messages tab is default** — opening the app shows a flat list of latest messages, not threads.
3. **Sender names are readable** — "HSBC", "ICICI Bank", not "VD-HSBCIN-S".
4. **Filter chips scroll horizontally** when there are many; zero-count chips are hidden; counts render as `OTP · 163`.
5. **Threads view is still reachable** — tap `⋮` → "Group by sender (threads)". Selection persists.
6. **No content under the FAB** — scroll to the bottom of the list; the last message is fully visible above the `+ New` button.
7. **Risk-dot replaces stripe** — phishing rows show a small red dot next to the timestamp; clean rows show no decoration.
8. **OTP strip is one row** when present.
9. **Build is clean** — no unused-import warnings for the imports listed under Task 3.

---

## Implementation order for Cursor

```
1. Create util/SenderNameResolver.kt          (Task 2)
2. Edit InboxViewModel.kt: ViewMode default   (Task 1)
3. Rewrite components/FilterChips.kt          (Task 4)
4. Edit InboxScreen.kt: header + FAB padding  (Tasks 3, 5, 8b)
5. Edit components/ConversationItem.kt        (Task 6)
6. Rewrite components/MessageItem.kt          (Task 7)
7. Edit components/OtpStrip.kt                (Task 8a)
8. (Optional) Edit screens/MainScaffold.kt    (Task 9)
9. Build & fix any import-related compile errors.
```

If anything fails to compile, the most likely culprits are:
- `FilterChipDefaults.filterChipBorder(...)` — signature drift across Material 3 versions. Fall back to the no-arg-override form.
- Missing `import com.smsclassifier.app.util.SenderNameResolver` in any file that references it.
- Leftover unused imports — let Android Studio's "Optimize Imports" clean them up.

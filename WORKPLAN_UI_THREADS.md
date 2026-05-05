# Workplan — UI modernization + threads logic (target: v1.0.13)

> Audience: a smaller agent model (Sonnet 4.6 etc.) executing one phase at a
> time, with the senior model reviewing after each phase. Every phase below is
> self-contained: it lists the exact files to touch, the exact code to add or
> replace, and an acceptance check. Do **one phase per commit** so reviews and
> rollbacks stay clean.

## 0. Goals

1. Make the app feel native on Android 12+ (Material You dynamic color +
   edge-to-edge).
2. Make the classification value of the app visible in the chrome (bottom
   NavigationBar with Inbox / OTPs / Flagged / Settings; pinned OTP strip on
   Inbox).
3. Tighten threads logic so classification filters don't bury risky messages
   inside otherwise-clean threads (dual-axis view: threads vs flat messages).
4. Quality-of-life polish: SearchBar, SegmentedButton filters, risk accent on
   thread rows, smaller empty-state, optional shared-element transitions.

### Non-goals
- Any backend changes (`backend/scripts/android_backend_server.py` is **off
  limits**).
- Any ML model changes.
- Any change to the feedback upload pipeline (`FeedbackUploader`,
  `FeedbackUploadWorker`, `MisclassificationLog*`).
- Any privacy-policy edits (already shipped in v1.0.12).

### Out-of-the-box state to assume
- `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt` is the
  **active home screen** (`startDestination = "inbox"` in MainActivity).
- `ConversationListScreen.kt` exists but is unused — leave it alone unless a
  phase explicitly says otherwise.
- Compose BOM is `2023.10.01` (Material3 `1.1.2`, compose-animation `1.5.4`).
  We will bump this in Phase 1 to enable stable `SearchBar`,
  `SegmentedButton`, and `SharedTransitionScope`.
- Activity-compose is `1.8.1` — `enableEdgeToEdge()` is already available.
- Existing brand palette in `ui/theme/Color.kt` and theme builder in
  `ui/theme/Theme.kt` should keep working as a non-dynamic fallback.

---

## Phase 1 — Bump Compose BOM + Material You + edge-to-edge

**Why first:** later phases use `SearchBar`, `SegmentedButton`, and
`SharedTransitionScope`, all of which require BOM ≥ `2024.06.00`. Doing the
bump together with dynamic color + edge-to-edge keeps it as one "modern shell"
commit you can revert in one shot if anything regresses.

### Files

- `app/build.gradle.kts`
- `app/src/main/java/com/smsclassifier/app/ui/theme/Theme.kt`
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt`

### Changes

#### 1a. Bump Compose BOM in `app/build.gradle.kts`

Replace **both** occurrences of:

```kotlin
implementation(platform("androidx.compose:compose-bom:2023.10.01"))
```

and

```kotlin
androidTestImplementation(platform("androidx.compose:compose-bom:2023.10.01"))
```

with:

```kotlin
implementation(platform("androidx.compose:compose-bom:2024.06.00"))
```

and

```kotlin
androidTestImplementation(platform("androidx.compose:compose-bom:2024.06.00"))
```

> Do **not** change the `activity-compose:1.8.1` or
> `navigation-compose:2.7.5` versions in this commit; those are unrelated.

After the bump, run `.\gradlew :app:dependencies | Select-String material3`
and confirm it now resolves to `1.2.x`. If it stays at `1.1.x`, the BOM didn't
take — recheck the line.

#### 1b. Dynamic color + sane status/nav bars in Theme.kt

Replace the entire body of
`app/src/main/java/com/smsclassifier/app/ui/theme/Theme.kt` with:

```kotlin
package com.smsclassifier.app.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowInsetsControllerCompat

private val FallbackDarkColorScheme = darkColorScheme(
    primary = BrandBlueLight,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF003D78),
    onPrimaryContainer = Color(0xFFD7E6F8),
    secondary = SuspiciousAmber,
    onSecondary = Color.Black,
    background = DarkBackground,
    onBackground = DarkOnBackground,
    surface = DarkSurface,
    onSurface = DarkOnBackground,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = DarkOnSurfaceVariant,
    error = PhishingRed,
    outline = Color(0xFF3A4047)
)

private val FallbackLightColorScheme = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    primaryContainer = OTPBlueSoft,
    onPrimaryContainer = BrandBlueDark,
    secondary = SuspiciousAmber,
    onSecondary = Color.White,
    background = LightBackground,
    onBackground = LightOnBackground,
    surface = LightSurface,
    onSurface = LightOnBackground,
    surfaceVariant = LightSurfaceVariant,
    onSurfaceVariant = LightOnSurfaceVariant,
    error = PhishingRed,
    outline = Color(0xFFD6DBE2)
)

private val AppShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(18.dp),
    extraLarge = RoundedCornerShape(28.dp)
)

private val AppTypography = Typography(
    displayLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 48.sp, letterSpacing = (-0.5).sp),
    displayMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 36.sp, letterSpacing = (-0.25).sp),
    headlineMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 24.sp, letterSpacing = 0.sp),
    titleLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, letterSpacing = 0.15.sp),
    titleMedium = TextStyle(fontWeight = FontWeight.Medium, fontSize = 16.sp, letterSpacing = 0.15.sp),
    titleSmall = TextStyle(fontWeight = FontWeight.Medium, fontSize = 14.sp, letterSpacing = 0.1.sp),
    bodyLarge = TextStyle(fontWeight = FontWeight.Normal, fontSize = 16.sp, letterSpacing = 0.5.sp),
    bodyMedium = TextStyle(fontWeight = FontWeight.Normal, fontSize = 14.sp, letterSpacing = 0.25.sp),
    bodySmall = TextStyle(fontWeight = FontWeight.Normal, fontSize = 12.sp, letterSpacing = 0.4.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.Medium, fontSize = 14.sp, letterSpacing = 0.1.sp),
    labelMedium = TextStyle(fontWeight = FontWeight.Medium, fontSize = 12.sp, letterSpacing = 0.5.sp),
    labelSmall = TextStyle(fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 0.5.sp)
)

@Composable
fun SMSClassifierTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        darkTheme -> FallbackDarkColorScheme
        else -> FallbackLightColorScheme
    }

    val view = LocalView.current
    SideEffect {
        val window = (view.context as? Activity)?.window ?: return@SideEffect
        // Edge-to-edge: keep the bars transparent and let content draw under
        // them. WindowInsetsControllerCompat handles the icon-color contrast
        // hint per theme.
        window.statusBarColor = Color.Transparent.toArgb()
        window.navigationBarColor = Color.Transparent.toArgb()
        WindowInsetsControllerCompat(window, view).isAppearanceLightStatusBars = !darkTheme
        WindowInsetsControllerCompat(window, view).isAppearanceLightNavigationBars = !darkTheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        shapes = AppShapes,
        typography = AppTypography,
        content = content
    )
}
```

#### 1c. Enable edge-to-edge in `MainActivity.kt`

In `MainActivity.onCreate`, immediately **before** `super.onCreate(...)` is
called, insert:

```kotlin
androidx.activity.enableEdgeToEdge()
```

Yes, before `super.onCreate(...)` — that's how the official AndroidX docs
recommend it.

Also add the import at the top of the file:

```kotlin
import androidx.activity.enableEdgeToEdge
```

> Do not change the existing `Surface(modifier = Modifier.fillMaxSize(), ...)`
> wrapping. `Scaffold` already handles insets correctly when the system bars
> are transparent.

### Acceptance check (Phase 1)

- `.\gradlew bundleDebug` builds clean (no Compose API errors).
- App launches on a Pixel-style emulator running Android 12+: top app bar
  color matches the device wallpaper accent (Material You is live).
- Top app bar and bottom nav area no longer show the old solid surface
  block — content draws under the status bar with a translucent feel.
- On Android 11 / API 30, the app falls back to the brand palette and looks
  identical to v1.0.12.

---

## Phase 2 — Bottom NavigationBar with 4 top-level destinations

**Why:** today, "Misclassification logs" and "Settings" hide behind a
`MoreVert` overflow on the Inbox top bar. A bottom `NavigationBar` makes the
app's classifier identity visible.

### New top-level routes

| Route | Composable | Notes |
|---|---|---|
| `inbox` | `InboxScreen` (existing) | Unchanged content for now. |
| `otp` | `OtpInboxScreen` (NEW) | Phase 3 fills this in. Stub for now. |
| `flagged` | `FlaggedScreen` (NEW) | Stub now; Phase 4 will reuse `InboxScreen` content with `filter = PHISHING + NEEDS_REVIEW`. |
| `settings` | `SettingsScreen` (existing) | Unchanged. |

### Files

- New: `app/src/main/java/com/smsclassifier/app/ui/screens/MainScaffold.kt`
- New: `app/src/main/java/com/smsclassifier/app/ui/screens/OtpInboxScreen.kt` (stub)
- New: `app/src/main/java/com/smsclassifier/app/ui/screens/FlaggedScreen.kt` (stub)
- Modify: `app/src/main/java/com/smsclassifier/app/MainActivity.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt` (drop the overflow menu now that bottom nav exists)

### Changes

#### 2a. Create `MainScaffold.kt`

```kotlin
package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.Pin
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState

private data class TopLevelDestination(
    val route: String,
    val label: String,
    val icon: ImageVector
)

private val TopLevelDestinations = listOf(
    TopLevelDestination("inbox", "Inbox", Icons.Default.Inbox),
    TopLevelDestination("otp", "OTPs", Icons.Default.Pin),
    TopLevelDestination("flagged", "Flagged", Icons.Default.Warning),
    TopLevelDestination("settings", "Settings", Icons.Default.Settings)
)

@Composable
fun MainBottomBar(navController: NavHostController) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBar = TopLevelDestinations.any { it.route == currentRoute }
    if (!showBar) return

    NavigationBar {
        TopLevelDestinations.forEach { dest ->
            NavigationBarItem(
                selected = currentRoute == dest.route,
                onClick = {
                    if (currentRoute == dest.route) return@NavigationBarItem
                    navController.navigate(dest.route) {
                        popUpTo(navController.graph.findStartDestination().id) {
                            saveState = true
                        }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = { Icon(dest.icon, contentDescription = dest.label) },
                label = { Text(dest.label) }
            )
        }
    }
}
```

#### 2b. Create `OtpInboxScreen.kt` (stub for now)

```kotlin
package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OtpInboxScreen(modifier: Modifier = Modifier) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("OTPs") }) }
    ) { padding ->
        Box(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentAlignment = Alignment.Center
        ) {
            Text("Recent OTPs will live here.")
        }
    }
}
```

#### 2c. Create `FlaggedScreen.kt` (stub for now)

```kotlin
package com.smsclassifier.app.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FlaggedScreen(modifier: Modifier = Modifier) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("Flagged") }) }
    ) { padding ->
        Box(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentAlignment = Alignment.Center
        ) {
            Text("Phishing + Needs review will live here.")
        }
    }
}
```

#### 2d. Wire bottom bar in `MainActivity.kt`

Inside `setContent { SMSClassifierTheme { Surface(...) { ... } } }`, wrap the
`NavHost` with a Scaffold that hosts `MainBottomBar`. Replace the existing
`Surface { val navController = rememberNavController(); ... NavHost(...) }`
block with:

```kotlin
val navController = rememberNavController()

// (keep the existing intent-driven LaunchedEffect blocks here unchanged)

androidx.compose.material3.Scaffold(
    bottomBar = { MainBottomBar(navController) }
) { innerPadding ->
    NavHost(
        navController = navController,
        startDestination = "inbox",
        modifier = Modifier.padding(innerPadding)
    ) {
        // existing composable("inbox") { ... } block — UNCHANGED
        // existing composable("conversations") { ... } — UNCHANGED
        // existing composable("thread/{threadId}") { ... } — UNCHANGED
        // existing composable("compose") { ... } — UNCHANGED
        // existing composable("detail/{messageId}") { ... } — UNCHANGED
        // existing composable("settings") { ... } — UNCHANGED
        // existing composable("logs") { ... } — UNCHANGED

        composable("otp") {
            OtpInboxScreen()
        }
        composable("flagged") {
            FlaggedScreen()
        }
    }
}
```

Add the imports:

```kotlin
import com.smsclassifier.app.ui.screens.MainBottomBar
import com.smsclassifier.app.ui.screens.OtpInboxScreen
import com.smsclassifier.app.ui.screens.FlaggedScreen
import androidx.compose.foundation.layout.padding
```

#### 2e. Strip the overflow menu from `InboxScreen.kt`

In `InboxScreen.kt`, in the `actions = { ... }` block of the
`CenterAlignedTopAppBar`:

- Keep the **search** `IconButton`.
- **Delete** the `IconButton` that opens `menuExpanded` (the `MoreVert`
  button) and the `DropdownMenu` block beneath it.
- Delete the `var menuExpanded by remember { mutableStateOf(false) }` line.
- Delete the `onOpenLogs` and `onOpenSettings` parameters from
  `InboxScreen(...)` signature (and remove the corresponding callsite
  arguments in `MainActivity.kt`).

> Settings is reachable via the bottom nav. Logs becomes reachable via the
> Settings screen (already linked from there) or the Flagged tab; we
> intentionally remove the duplicate path.

### Acceptance check (Phase 2)

- Bottom bar appears on Inbox / OTPs / Flagged / Settings, hides on
  Thread / Detail / Compose / Logs.
- Tapping a bottom-bar item navigates without rebuilding the home
  destination's state (filter chips and search remain on Inbox when you bounce
  to OTPs and back).
- No more `MoreVert` icon on Inbox top bar.
- `Compose` builds clean.

---

## Phase 3 — Pinned OTP strip on the Inbox

**Why:** OTPs are time-sensitive and should be one-tap-copyable from the home
screen, not buried in a thread. The data is already there.

### Files

- New: `app/src/main/java/com/smsclassifier/app/ui/components/OtpStrip.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/data/MessageDao.kt` (one
  new query)
- Modify: `app/src/main/java/com/smsclassifier/app/ui/viewmodel/InboxViewModel.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`
- Update: `OtpInboxScreen.kt` (the stub from Phase 2 becomes a fuller list)

### Changes

#### 3a. New DAO query

In `MessageDao.kt`, add (right after `getOtpPaged`):

```kotlin
@Query("SELECT * FROM messages WHERE isOtp = 1 AND ts >= :sinceTs ORDER BY ts DESC LIMIT :limit")
suspend fun getRecentOtps(sinceTs: Long, limit: Int = 3): List<MessageEntity>
```

#### 3b. Expose recent OTPs from `InboxViewModel.kt`

Add fields and an init-level coroutine:

```kotlin
private val _recentOtps = MutableStateFlow<List<MessageEntity>>(emptyList())
val recentOtps: StateFlow<List<MessageEntity>> = _recentOtps.asStateFlow()

fun refreshRecentOtps() {
    viewModelScope.launch {
        val tenMinutesAgo = System.currentTimeMillis() - 10 * 60 * 1000L
        _recentOtps.value = database.messageDao().getRecentOtps(tenMinutesAgo, limit = 3)
    }
}
```

In `init { ... }`, **also** call `refreshRecentOtps()` once, and inside the
existing `getLatestMessage().collect { ... }` block, call
`refreshRecentOtps()` again whenever a new message arrives (keep the
existing `loadConversations()` call too).

#### 3c. New component `OtpStrip.kt`

```kotlin
package com.smsclassifier.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.util.ClassificationUtils

@Composable
fun OtpStrip(
    messages: List<MessageEntity>,
    onCardClick: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    if (messages.isEmpty()) return
    val clipboard = LocalClipboardManager.current

    LazyRow(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(items = messages, key = { it.id }) { msg ->
            val code = ClassificationUtils.extractOtpForCopy(msg.body, msg.sender, msg.isOtp)
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
        }
    }
}
```

#### 3d. Mount the strip on `InboxScreen`

In `InboxScreen.kt`, inside the `Column` body just **before** the
`FilterChips(...)` call, add:

```kotlin
val recentOtps by viewModel.recentOtps.collectAsState()
OtpStrip(
    messages = recentOtps,
    onCardClick = { id -> onMessageClick(id) }
)
```

Add the import:

```kotlin
import com.smsclassifier.app.ui.components.OtpStrip
```

#### 3e. Reuse `OtpStrip` on `OtpInboxScreen`

Replace the placeholder body of `OtpInboxScreen` with a screen that lists ALL
OTPs (not just the last 10 minutes). Add this DAO query if missing:

```kotlin
@Query("SELECT * FROM messages WHERE isOtp = 1 ORDER BY ts DESC")
fun getAllOtpsPaged(): PagingSource<Int, MessageEntity>
```

(`getOtpPaged` already exists with this exact behavior — reuse it. Don't add
a duplicate query.)

`OtpInboxScreen` should reuse the existing `MessageItem` component
(`ui/components/MessageItem.kt`) inside a `LazyColumn`, fed by
`viewModel.messages` after forcing `setFilter(FilterType.OTP)` on first load.
You can either inject the existing `InboxViewModel` here or create a tiny
`OtpInboxViewModel` that pages from `database.messageDao().getOtpPaged()`. The
viewmodel-per-screen approach is cleaner and shorter.

### Acceptance check (Phase 3)

- Send yourself an OTP SMS from another phone — within 30 s a card appears at
  the top of the Inbox with the OTP code in big text and a Copy button.
- Tapping Copy puts the code on the clipboard (verify by long-pressing in any
  text field).
- After 10 minutes the card disappears from the Inbox strip.
- The OTPs tab shows ALL classified OTPs ordered DESC.

---

## Phase 4 — Threads/Messages dual-axis on Inbox + reuse for Flagged

**Why:** with a `PHISHING` filter active, today's Inbox still groups by
thread, so a 3-message thread that contains 1 phishing message is shown as a
single row with a snippet that may not even be the phishing one. We need an
explicit toggle to flip between **Threads** (current behavior) and
**Messages** (flat, classifier-friendly).

### Files

- Modify: `app/src/main/java/com/smsclassifier/app/ui/viewmodel/InboxViewModel.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/FlaggedScreen.kt` (replace stub)

### Changes

#### 4a. ViewMode enum + state in `InboxViewModel.kt`

At the top of the file, near `enum class FilterType`, add:

```kotlin
enum class ViewMode { THREADS, MESSAGES }
```

Inside the class, add:

```kotlin
private val _viewMode = MutableStateFlow(ViewMode.THREADS)
val viewMode: StateFlow<ViewMode> = _viewMode.asStateFlow()

fun setViewMode(mode: ViewMode) {
    _viewMode.value = mode
}
```

`messages: Flow<PagingData<MessageEntity>>` already exists — keep it. The
screen will pick which flow to render based on `viewMode`.

#### 4b. Render toggle + flat list in `InboxScreen.kt`

Above the `FilterChips` call, add a small **SegmentedButtonRow**:

```kotlin
val viewMode by viewModel.viewMode.collectAsState()
SingleChoiceSegmentedButtonRow(
    modifier = Modifier
        .fillMaxWidth()
        .padding(horizontal = 16.dp, vertical = 4.dp)
) {
    SegmentedButton(
        selected = viewMode == ViewMode.THREADS,
        onClick = { viewModel.setViewMode(ViewMode.THREADS) },
        shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
    ) { Text("Threads") }
    SegmentedButton(
        selected = viewMode == ViewMode.MESSAGES,
        onClick = { viewModel.setViewMode(ViewMode.MESSAGES) },
        shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
    ) { Text("Messages") }
}
```

Imports:

```kotlin
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import com.smsclassifier.app.ui.viewmodel.ViewMode
```

In the `when` block that renders the list, add a branch on `viewMode`:

```kotlin
when (viewMode) {
    ViewMode.THREADS -> {
        // existing thread-rendering branch (LazyColumn of ConversationItem)
    }
    ViewMode.MESSAGES -> {
        val pagingItems = viewModel.messages.collectAsLazyPagingItems()
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(vertical = 6.dp)
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
    }
}
```

Imports:

```kotlin
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import androidx.compose.foundation.lazy.items
import com.smsclassifier.app.ui.components.MessageItem
```

> If `MessageItem.onClick` does not exist, add a `onClick` lambda parameter
> wrapping the existing root modifier with `clickable`. Keep the rest of the
> component identical.

#### 4c. `FlaggedScreen` becomes the curated risk view

Replace the stub body with:

```kotlin
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FlaggedScreen(
    viewModel: InboxViewModel,
    onMessageClick: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    LaunchedEffect(Unit) {
        // Force the messages flow into PHISHING + show as flat
        viewModel.setFilter(FilterType.PHISHING)
        viewModel.setViewMode(ViewMode.MESSAGES)
    }
    val pagingItems = viewModel.messages.collectAsLazyPagingItems()
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("Flagged") }) }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(vertical = 6.dp)
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
    }
}
```

Wire it in `MainActivity.kt`:

```kotlin
composable("flagged") {
    val viewModel: InboxViewModel = viewModel(
        factory = InboxViewModelFactory(database)
    )
    FlaggedScreen(
        viewModel = viewModel,
        onMessageClick = { id -> navController.navigate("detail/$id") }
    )
}
```

> `InboxViewModel` is intentionally re-instantiated for the Flagged route —
> sharing the home VM would let `setFilter(PHISHING)` leak back into the Inbox
> tab.

### Acceptance check (Phase 4)

- On Inbox, switching the segmented control between Threads ↔ Messages keeps
  the same `FilterType` selected and just changes the layout.
- With `PHISHING` filter + `MESSAGES` mode, the list shows individual
  flagged messages (not threads) and tapping one opens the `DetailScreen`
  for that message.
- Bouncing between Inbox tab and Flagged tab does NOT cross-pollute their
  filter state.

---

## Phase 5 — Risk accent on thread rows + avatar ring

**Why:** today the risk indicator is a small badge below the snippet. Eyes
skip it. A 4 dp colored bar on the leading edge plus a colored ring on the
avatar makes the risk obvious at a glance.

### Files

- Modify: `app/src/main/java/com/smsclassifier/app/ui/components/ConversationItem.kt`
- Modify: `app/src/main/java/com/smsclassifier/app/util/ClassificationUtils.kt` (small helper)

### Changes

#### 5a. Add helper in `ClassificationUtils.kt`

Add (next to `riskBadgeType`):

```kotlin
enum class RiskLevel { NONE, LOW, MEDIUM, HIGH }

fun riskLevelForThread(latest: MessageEntity?): RiskLevel = when {
    latest == null -> RiskLevel.NONE
    latest.isPhishing == true -> RiskLevel.HIGH
    (latest.phishScore ?: 0f) >= 0.5f -> RiskLevel.MEDIUM
    (latest.phishScore ?: 0f) >= 0.3f -> RiskLevel.LOW
    else -> RiskLevel.NONE
}
```

#### 5b. Render the bar + ring in `ConversationItem.kt`

Wrap the existing `Row(...)` body in a `Box`:

```kotlin
val risk = ClassificationUtils.riskLevelForThread(thread.latestMessage)
val accentColor = when (risk) {
    RiskLevel.HIGH -> MaterialTheme.colorScheme.error
    RiskLevel.MEDIUM -> SuspiciousAmber
    RiskLevel.LOW -> SuspiciousAmberSoft
    RiskLevel.NONE -> Color.Transparent
}

Surface(
    color = MaterialTheme.colorScheme.surface,
    modifier = modifier.fillMaxWidth().combinedClickable(
        onClick = onClick,
        onLongClick = { onLongClick?.invoke() }
    )
) {
    Row(modifier = Modifier.fillMaxWidth()) {
        // 4dp accent bar
        Box(
            modifier = Modifier
                .width(4.dp)
                .fillMaxHeight()
                .background(accentColor)
        )
        // existing inner Row of avatar + content (unchanged)
    }
}
```

For the avatar ring, change the `ContactAvatar(... size = 48.dp)` call so it
takes an optional `ringColor: Color? = null` parameter, and inside that
component, when `ringColor != null`, wrap the existing inner avatar in a
`Box` with `border(2.dp, ringColor, CircleShape)` and a 2 dp inner padding.
Pass `ringColor = if (risk == RiskLevel.HIGH) MaterialTheme.colorScheme.error
else null` from `ConversationItem`.

> Keep the existing badges (`ClassificationBadge`, `SensitivityBadge`) below
> the snippet. They're fine; we're just adding redundancy at glance level.

### Acceptance check (Phase 5)

- A clean thread row looks identical to v1.0.12 (no bar, no ring).
- A thread whose latest message is phishing shows a red 4 dp leading bar AND
  a red avatar ring.
- A medium-risk row (`phishScore` 0.3–0.5) shows a softer amber bar, no
  ring.

---

## Phase 6 — DockedSearchBar + replace the inline TextField

**Why:** the current expandable in-top-bar TextField is a custom workaround
for the older Compose BOM. Now that we're on `2024.06.00`, the stable
`DockedSearchBar` is available and gives us recent-searches + suggestions for
free.

### Files

- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`
- Delete (after this phase): `InboxSearchBar` and `BasicTextFieldStyled`
  helpers inside `InboxScreen.kt`.

### Changes

Replace the entire `searchActive` block + `InboxSearchBar(...)` call with:

```kotlin
var searchExpanded by remember { mutableStateOf(false) }
DockedSearchBar(
    query = searchQuery,
    onQueryChange = viewModel::setSearchQuery,
    onSearch = { searchExpanded = false },
    active = searchExpanded,
    onActiveChange = { searchExpanded = it },
    placeholder = { Text("Search messages") },
    leadingIcon = { Icon(Icons.Default.Search, null) },
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
    // empty body — we don't need a suggestions popup yet
}
```

Drop the `searchActive` toggle from the top-bar `actions` (the SearchBar
itself replaces that affordance). Delete the now-unused `InboxSearchBar` and
`BasicTextFieldStyled` private composables.

### Acceptance check (Phase 6)

- A docked, pill-shaped search bar sits above the filter chips on Inbox.
- Typing into it filters the visible list as before.
- The X button clears the query.

---

## Phase 7 — Empty states + small chrome polish

### Files

- Modify: `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`
  → `EmptyInboxState`
- Modify: `app/src/main/java/com/smsclassifier/app/ui/components/FilterChips.kt`
  (replace with `SegmentedButtonRow` for OTP / Phishing / All; keep
  `Personal` and `Needs review` as overflow chips OR delete — see below).

### Changes

#### 7a. Smaller, less shouty empty state

In `EmptyInboxState`, change `Modifier.size(96.dp)` to `Modifier.size(64.dp)`
and `Modifier.size(48.dp)` (icon) to `Modifier.size(32.dp)`. Add a sub-CTA
that calls back to the activity to launch the default-SMS role intent:

```kotlin
TextButton(onClick = onSetDefaultSms) { Text("Set as default SMS app") }
```

Plumb a new lambda `onSetDefaultSms: () -> Unit` from
`MainActivity` → `InboxScreen` → `EmptyInboxState`. In `MainActivity`, pass a
lambda that calls `promptForDefaultSmsIfNeeded()`.

#### 7b. Filter row → SegmentedButtonRow

Replace the entire `FilterChips.kt` body with a `SingleChoiceSegmentedButtonRow`
that exposes only `OTP / PHISHING / ALL`. Move `Personal` and `Needs review`
into a tiny `MoreVert` overflow on the right edge of the same row. Counts can
be rendered as small superscript-style labels inside each segment.

> This is the most-debated cosmetic phase. If a smaller model is unsure, it
> can SKIP this phase and just rebrand the existing chips with `border` +
> `RoundedCornerShape(50)` cosmetic tweaks. The functional contract
> (`FilterType`) MUST stay the same.

### Acceptance check (Phase 7)

- Empty state is visibly smaller and offers a "Set as default SMS app" CTA
  that triggers the role-request dialog.
- Filter row shows three primary segments + an overflow.

---

## Phase 8 — (OPTIONAL) Inbox→Thread shared-element transition

**Why:** the most "expensive looking" upgrade for the lowest functional risk —
when the user taps a row, the avatar and title morph smoothly into the Thread
top bar.

### Files

- Modify: `MainActivity.kt` — wrap the inner `NavHost` in a
  `SharedTransitionLayout` and pass `LocalSharedTransitionScope` /
  `LocalAnimatedVisibilityScope` down via `CompositionLocalProvider`.
- Modify: `ConversationItem.kt` and `ThreadScreen.kt` — annotate the shared
  avatar + title with `Modifier.sharedElement(...)`.

### Why this is OPTIONAL
- Requires `compose-animation:1.7+` (BOM 2024.06.00 has it — fine).
- Requires the experimental opt-in `@OptIn(ExperimentalSharedTransitionApi::class)`.
- Compose's shared-element API still has rough edges with `NavHost`. If a
  smaller model can't get it stable in <30 minutes, **skip and revisit**.

### Acceptance check (Phase 8)

- Tapping a thread row visibly animates the avatar from the row into the
  thread top bar.
- Back gesture reverses the animation cleanly.

---

## Release (after all phases land)

1. Bump `app/build.gradle.kts`:
   - `versionCode = 14`
   - `versionName = "1.0.13"`
2. Update `app/src/main/play/release-notes/en-US/default.txt` — short, user-
   facing list:
   ```
   v1.0.13 (May 2026)
   - Fresh look on Android 12+: Material You wallpaper-derived colors.
   - Edge-to-edge layout for a more native feel.
   - New bottom navigation: Inbox / OTPs / Flagged / Settings.
   - Pinned OTP cards on the home screen — copy any code in one tap.
   - Switch the Inbox between thread view and flat message view.
   - Risk accent strip on flagged threads at a glance.
   - Polished search bar and empty states.
   ```
3. `.\gradlew bundleRelease` then `.\gradlew publishReleaseBundle`
   (uploads to **beta / Open testing** by default — same flow as v1.0.12).
4. After 24 h on beta with no crash spikes, promote:
   ```powershell
   .\gradlew promoteArtifact --from-track beta --promote-track production --user-fraction 0.10
   ```

---

## Risks & rollback

| Risk | Mitigation |
|---|---|
| Compose BOM bump breaks an existing screen | Each phase is its own commit. If Phase 1 alone breaks something, revert just that commit; the BOM bump is isolated. |
| Material You looks bad on a particular wallpaper | The fallback `Light/DarkColorScheme` still ships. Add a Settings toggle in a future patch if needed. |
| `enableEdgeToEdge` introduces inset bugs on a specific OEM | The IME bar / Snackbar / FAB live inside `Scaffold` already, which respects insets. If a screen looks clipped, wrap with `WindowInsets.safeDrawing.asPaddingValues()` instead of removing edge-to-edge. |
| `DockedSearchBar` regresses search-as-you-type performance | The query already debounces in `setSearchQuery`. If perf regresses, fall back to the v1.0.12 inline-TextField (kept around as a private composable until Phase 7 ships). |
| Shared-element transition flickers | Skip Phase 8. Everything before it is independent. |

---

## How a smaller model should drive this

1. Read this file end-to-end **once**.
2. Pick the lowest-numbered un-merged phase. Make ONLY the changes in that
   phase. **Do not jump ahead.**
3. Run `.\gradlew :app:compileDebugKotlin` (cheaper than full bundle) to
   verify the phase compiles. Fix any errors **only inside the files this
   phase already touches**.
4. Run the acceptance check listed at the bottom of the phase.
5. `git add` only the files this phase declares, plus any imports / unused-
   import cleanup. Commit with a message of the form
   `v1.0.13/phase-N: <one-line summary>`.
6. Stop. Hand back for senior review before starting the next phase.

> If a phase mentions a file that does not exist or has drifted, **stop and
> ask** — do not improvise a renamed equivalent.

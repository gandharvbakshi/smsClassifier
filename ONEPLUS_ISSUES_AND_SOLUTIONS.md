# OnePlus Device Issues - Proposed Solutions

This document outlines the 3 issues found on OnePlus devices and proposed solutions. **Do not implement yet** - review first.

## Issue 1: Hidden "General" and "All" Filter Tabs

### Problem
The filter chips (OTP, PHISHING, NEEDS_REVIEW, GENERAL, ALL) are arranged horizontally in a `Row`, and on OnePlus devices (or smaller screens), the last two chips (GENERAL and ALL) are cut off/hidden because they don't fit on screen.

**Location:** `FilterChips.kt` - Uses `Row` without horizontal scrolling

### Root Cause
- `FilterChips` component uses `Row` with `horizontalArrangement = Arrangement.spacedBy(8.dp)`
- 5 chips might not fit on smaller screens or devices with different DPI settings
- No horizontal scrolling implemented

### Proposed Solutions

#### Solution 1A: Horizontal Scrollable Row (Recommended)
Make the filter chips horizontally scrollable:

```kotlin
// In FilterChips.kt
@Composable
fun FilterChips(...) {
    val scrollState = rememberScrollState()
    
    HorizontalScrollableRow(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
        scrollState = scrollState,
        contentPadding = PaddingValues(horizontal = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        filterOrder.forEach { filter ->
            // ... existing chip code ...
        }
    }
}
```

**Pros:**
- All chips visible
- Works on all screen sizes
- Users can scroll to see all options

**Cons:**
- Slightly more complex UI
- Users might not realize chips are scrollable

#### Solution 1B: Wrap to Multiple Lines
Allow chips to wrap to multiple rows:

```kotlin
// Use FlowRow from Accompanist or Material3
FlowRow(
    modifier = modifier
        .fillMaxWidth()
        .padding(horizontal = 8.dp, vertical = 4.dp),
    horizontalArrangement = Arrangement.spacedBy(8.dp),
    verticalArrangement = Arrangement.spacedBy(8.dp)
) {
    filterOrder.forEach { filter ->
        // ... existing chip code ...
    }
}
```

**Pros:**
- All chips visible
- No scrolling needed
- Better use of vertical space

**Cons:**
- Takes more vertical space
- Might need to add dependency (if not available in Material3)

#### Solution 1C: Dropdown Menu for Overflow
Show first 3 chips, put rest in a "More" dropdown:

```kotlin
Row(...) {
    filterOrder.take(3).forEach { ... }
    // "More" button with dropdown for GENERAL and ALL
}
```

**Pros:**
- Always visible primary filters
- Saves space

**Cons:**
- Hides some filters by default
- Less discoverable

**Recommendation:** Solution 1A (Horizontal Scrollable Row) - best UX and all options remain visible.

---

## Issue 2: Messages Slide Down / Only One Message Visible

### Problem
In the thread/conversation view, messages appear to slide down automatically, and only one message is visible at a time instead of showing the full conversation history.

**Location:** `ThreadScreen.kt` - Auto-scroll behavior and LazyColumn layout

### Root Cause Analysis
1. **Aggressive Auto-Scroll** (Lines 44-49 in `ThreadScreen.kt`):
   ```kotlin
   LaunchedEffect(messages.size) {
       if (messages.isNotEmpty()) {
           scope.launch {
               listState.animateScrollToItem(messages.size - 1)
           }
       }
   }
   ```
   - This triggers on EVERY message size change
   - Causes visible sliding animation every time
   - Might scroll even when user is reading older messages

2. **LazyColumn Layout Issues**:
   - Messages might not be properly sized
   - `verticalArrangement = Arrangement.spacedBy(4.dp)` might cause issues
   - `contentPadding = PaddingValues(vertical = 8.dp)` might be insufficient

3. **Initial Scroll Position**:
   - Always scrolls to bottom on load
   - Doesn't preserve user's scroll position

### Proposed Solutions

#### Solution 2A: Smart Auto-Scroll (Recommended)
Only auto-scroll when:
- New message arrives (not on every size change)
- User is already near the bottom
- Initial load (first time opening thread)

```kotlin
// In ThreadScreen.kt
val wasNearBottom = remember { mutableStateOf(false) }
val firstLoad = remember { mutableStateOf(true) }

// Check if user is near bottom before auto-scrolling
LaunchedEffect(messages.size) {
    val itemCount = messages.size
    if (itemCount > 0) {
        // Only auto-scroll on new message, not on every change
        val currentIndex = listState.firstVisibleItemIndex
        val totalVisible = listState.layoutInfo.visibleItemsInfo.size
        val wasNearBottom = currentIndex + totalVisible >= itemCount - 2
        
        if (firstLoad.value || wasNearBottom) {
            scope.launch {
                listState.animateScrollToItem(itemCount - 1)
            }
            firstLoad.value = false
        }
    }
}

// Track scroll position
LaunchedEffect(listState.firstVisibleItemIndex) {
    val currentIndex = listState.firstVisibleItemIndex
    val totalVisible = listState.layoutInfo.visibleItemsInfo.size
    val itemCount = messages.size
    wasNearBottom.value = currentIndex + totalVisible >= itemCount - 2
}
```

**Pros:**
- Prevents unwanted scrolling
- Better UX - respects user's reading position
- Still scrolls when new message arrives (if near bottom)

**Cons:**
- More complex logic
- Need to track scroll state

#### Solution 2B: Remove Auto-Scroll, Manual "Scroll to Bottom" Button
Remove automatic scrolling entirely, add a floating button to scroll to bottom:

```kotlin
// Remove the LaunchedEffect auto-scroll

// Add scroll-to-bottom button
val showScrollButton = remember { derivedStateOf {
    listState.firstVisibleItemIndex + listState.layoutInfo.visibleItemsInfo.size < messages.size - 3
}}

AnimatedVisibility(
    visible = showScrollButton.value,
    modifier = Modifier.align(Alignment.BottomEnd)
) {
    FloatingActionButton(
        onClick = {
            scope.launch {
                listState.animateScrollToItem(messages.size - 1)
            }
        },
        modifier = Modifier.padding(16.dp)
    ) {
        Icon(Icons.Default.ArrowDownward, "Scroll to bottom")
    }
}
```

**Pros:**
- Full user control
- No unexpected scrolling
- Clear UX

**Cons:**
- Users need to manually scroll for new messages
- Extra UI element

#### Solution 2C: Fix LazyColumn Layout
Ensure messages are properly sized and visible:

```kotlin
LazyColumn(
    state = listState,
    modifier = Modifier
        .fillMaxSize()
        .fillMaxHeight(), // Explicit height
    contentPadding = PaddingValues(
        horizontal = 8.dp,
        vertical = 16.dp // More padding
    ),
    verticalArrangement = Arrangement.spacedBy(8.dp) // More spacing
) {
    items(
        items = messages,
        key = { it.id } // Add key for stable identity
    ) { message ->
        MessageBubble(
            message = message,
            modifier = Modifier.fillMaxWidth(), // Ensure full width
            // ... rest
        )
    }
}
```

**Pros:**
- Fixes layout issues
- Messages properly sized
- Better spacing

**Cons:**
- Doesn't fix auto-scroll behavior alone

**Recommendation:** Combine Solution 2A (Smart Auto-Scroll) + Solution 2C (Fix Layout). This addresses both the sliding behavior and ensures all messages are visible.

---

## Issue 3: No Notifications When Messages Arrive

### Problem
When new SMS messages arrive, no notifications are shown on OnePlus devices.

**Location:** `NotificationHelper.kt` and `SmsDeliverReceiver.kt`

### Root Cause Analysis
1. **Missing POST_NOTIFICATIONS Permission** (Android 13+):
   - OnePlus devices likely running Android 13+ (API 33+)
   - Android 13 requires runtime permission `POST_NOTIFICATIONS`
   - Currently not in `AndroidManifest.xml`

2. **Notification Channel Not Initialized at Startup**:
   - Channel is created in `NotificationHelper.createNotificationChannel()`
   - Only called when showing notification
   - Should be created at app startup

3. **OnePlus Battery Optimization**:
   - OnePlus devices have aggressive battery optimization
   - Can block background receivers and notifications
   - Need to request "Unrestricted" battery usage

4. **Notification Permission Not Requested**:
   - No code to request notification permission
   - App assumes permission is granted

### Proposed Solutions

#### Solution 3A: Add POST_NOTIFICATIONS Permission (Required for Android 13+)

**Step 1:** Add to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

**Step 2:** Request permission at app startup in `MainActivity`:
```kotlin
// In MainActivity.onCreate()
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
    when {
        ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED -> {
            // Permission already granted
            createNotificationChannel()
        }
        ActivityCompat.shouldShowRequestPermissionRationale(
            this,
            Manifest.permission.POST_NOTIFICATIONS
        ) -> {
            // Show rationale dialog
            showNotificationPermissionRationale()
        }
        else -> {
            // Request permission
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                REQUEST_NOTIFICATION_PERMISSION
            )
        }
    }
} else {
    // Android 12 and below - permission not needed
    createNotificationChannel()
}

private fun createNotificationChannel() {
    NotificationHelper.createNotificationChannel(this)
}
```

**Pros:**
- Required for Android 13+
- Fixes notification blocking

**Cons:**
- Need to handle permission request flow
- Requires user interaction

#### Solution 3B: Initialize Notification Channel at App Startup

**In `SMSClassifierApplication.onCreate()`:**
```kotlin
override fun onCreate() {
    super.onCreate()
    database = AppDatabase.getDatabase(this)
    
    // Create notification channel early
    NotificationHelper.createNotificationChannel(this)
    
    ClassificationWorker.enqueue(this)
}
```

**Pros:**
- Channel ready before first notification
- Simple fix

**Cons:**
- Doesn't fix permission issue alone

#### Solution 3C: Add OnePlus-Specific Battery Optimization Bypass

**In `SettingsScreen` or `MainActivity`:**
```kotlin
// Check and request battery optimization exemption
private fun requestBatteryOptimizationExemption() {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
        val intent = Intent().apply {
            action = Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
            data = Uri.parse("package:$packageName")
        }
        try {
            startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            // OnePlus uses custom battery settings
            // Try alternative approach
            val onePlusIntent = Intent().apply {
                action = "android.settings.APPLICATION_DETAILS_SETTINGS"
                data = Uri.parse("package:$packageName")
            }
            startActivity(onePlusIntent)
        }
    }
}

// Also add to manifest
// In AndroidManifest.xml, inside <application>
<meta-data
    android:name="android.app.auto_remove"
    android:value="false" />
```

**Pros:**
- Prevents OnePlus from killing the app
- Keeps receivers active

**Cons:**
- OnePlus-specific
- Requires user action

#### Solution 3D: Verify Notification Settings on OnePlus

**Add check in `NotificationHelper`:**
```kotlin
fun showNewMessageNotification(...) {
    // Check if notifications are enabled
    val notificationManager = NotificationManagerCompat.from(context)
    if (!notificationManager.areNotificationsEnabled()) {
        AppLog.w("NotificationHelper", "Notifications are disabled by user")
        // Optionally show dialog to enable
        return
    }
    
    // Check if channel is enabled
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        val channel = notificationManager.getNotificationChannel(CHANNEL_ID)
        if (channel?.importance == NotificationManager.IMPORTANCE_NONE) {
            AppLog.w("NotificationHelper", "Notification channel is disabled")
            // Optionally open channel settings
            return
        }
    }
    
    // ... rest of notification code ...
}
```

**Pros:**
- Detects if notifications are disabled
- Helps debug issues

**Cons:**
- Doesn't fix the root cause
- Only diagnostic

#### Solution 3E: Test Receiver is Triggered

**Add logging in `SmsDeliverReceiver`:**
```kotlin
override fun onReceive(context: Context, intent: Intent) {
    AppLog.d(TAG, "SmsDeliverReceiver triggered - Action: ${intent.action}")
    AppLog.d(TAG, "Is default SMS app: ${Telephony.Sms.getDefaultSmsPackage(context) == context.packageName}")
    
    // Also log notification attempt
    AppLog.d(TAG, "About to show notification...")
    // ... existing code ...
    AppLog.d(TAG, "Notification shown with ID: ${messageId.toInt()}")
}
```

**Pros:**
- Helps debug if receiver is called
- Identifies where the issue occurs

**Cons:**
- Diagnostic only
- Doesn't fix the problem

**Recommendation:** 
1. **Solution 3A** (Add POST_NOTIFICATIONS permission) - **CRITICAL** for Android 13+
2. **Solution 3B** (Initialize channel at startup) - Simple and important
3. **Solution 3C** (Battery optimization bypass) - Helpful for OnePlus devices
4. **Solution 3D** (Verify settings) - Good for debugging
5. **Solution 3E** (Logging) - Use for diagnosis

All solutions should be implemented together for best results.

---

## Implementation Priority

1. **HIGH:** Issue 3 (Notifications) - Critical functionality
   - Add POST_NOTIFICATIONS permission
   - Initialize notification channel at startup
   - Request battery optimization exemption

2. **MEDIUM:** Issue 2 (Message sliding) - UX issue
   - Fix auto-scroll behavior
   - Fix LazyColumn layout

3. **MEDIUM:** Issue 1 (Hidden tabs) - Visibility issue
   - Make filter chips scrollable

---

## Testing Checklist After Implementation

### Issue 1 (Hidden Tabs)
- [ ] All 5 filter chips are visible
- [ ] Can scroll horizontally to see all chips
- [ ] Selected chip is visible and highlighted

### Issue 2 (Message Sliding)
- [ ] All messages in conversation are visible
- [ ] Auto-scroll only happens for new messages (when at bottom)
- [ ] Can scroll up to read older messages without auto-scrolling
- [ ] Scroll position preserved when navigating back and forth

### Issue 3 (Notifications)
- [ ] Notification permission requested on Android 13+
- [ ] Notification channel created at app startup
- [ ] Notifications appear when new SMS arrives
- [ ] Notification opens correct conversation when tapped
- [ ] Notification appears even when app is in background
- [ ] Works with battery optimization enabled/disabled

---

## OnePlus-Specific Notes

OnePlus devices have several customizations that can cause issues:
1. **Battery Optimization**: Very aggressive, can kill background receivers
2. **Notification Settings**: May have custom notification controls
3. **SMS App Handling**: May handle default SMS app differently
4. **Custom DPI**: Different screen density can affect UI layout

Test on multiple OnePlus devices/models if possible.


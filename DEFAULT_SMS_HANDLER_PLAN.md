# Plan: Becoming a Full Default SMS Handler

**Goal:** Transform SMS Classifier into a fully functional default SMS handler that meets Google Play Store requirements while maintaining classification as a core feature.

**Status:** Planning Phase  
**Estimated Development Time:** 4-6 weeks  
**Priority:** High (Required for Play Store approval)

---

## 📋 Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Required Features](#required-features)
3. [Implementation Phases](#implementation-phases)
4. [Technical Architecture](#technical-architecture)
5. [Database Schema Changes](#database-schema-changes)
6. [UI/UX Requirements](#uiux-requirements)
7. [Testing Checklist](#testing-checklist)
8. [Google Play Compliance](#google-play-compliance)

---

## Current State Assessment

### ✅ What Already Exists

1. **SMS Reception**
   - ✅ `SmsDeliverReceiver` - Receives SMS_DELIVER broadcasts
   - ✅ Stores messages in Room database
   - ✅ Background classification worker

2. **SMS Sending (Partial)**
   - ✅ `SmsSendService` - Basic SMS sending via SmsManager
   - ❌ No UI for composing messages
   - ❌ No reply functionality

3. **Data Storage**
   - ✅ Room database with `MessageEntity`
   - ✅ `SmsProvider` ContentProvider (needs Android SMS contract compliance)
   - ❌ No thread/conversation grouping
   - ❌ No sent message tracking

4. **UI Screens**
   - ✅ `InboxScreen` - Shows individual messages (classification-focused)
   - ✅ `DetailScreen` - Shows message details with classification
   - ❌ No conversation/thread view
   - ❌ No compose message screen
   - ❌ No conversation list

5. **MMS Support**
   - ✅ `WapPushReceiver` - Receives MMS (no-op)
   - ✅ `MmsSendService` - Placeholder (not implemented)
   - ❌ No MMS receiving implementation
   - ❌ No MMS sending implementation

### ❌ What's Missing

1. **Thread/Conversation Management**
   - Thread ID calculation (based on phone number)
   - Conversation grouping
   - Message direction (incoming/outgoing)
   - Read/unread status

2. **SMS Sending UI**
   - Compose new message screen
   - Reply functionality
   - Contact picker integration
   - Message status (sending, sent, delivered, failed)

3. **Conversation UI**
   - Conversation list (grouped by thread)
   - Thread view (message history)
   - Message bubbles (sent/received styling)

4. **Android SMS Contract Compliance**
   - `SmsProvider` must implement Android's SMS ContentProvider contract
   - Support standard SMS URIs (`content://sms/`, `content://sms/inbox`, etc.)
   - Support standard columns (`_id`, `thread_id`, `address`, `body`, `date`, `type`, etc.)

5. **MMS Receivers (Minimal)** ⚠️ Required but minimal
   - Register `WapPushReceiver` (can show "MMS not supported")
   - Register `MmsSendService` (can show "MMS not supported")
   - **Full MMS parsing/sending NOT required for approval**

6. **Default Handler Features**
   - Proper default SMS app role handling
   - SMS backup/restore
   - Notification management
   - Quick reply from notifications

---

## Required vs Optional Features

### ✅ **REQUIRED for Google Play Approval** (Minimum Viable Product)

These features are **mandatory** to be approved as a default SMS handler:

1. **SMS Sending** ⚠️ REQUIRED
   - UI to compose new messages
   - UI to reply to messages
   - Actually send SMS via SmsManager
   - Save sent messages to database

2. **SMS Receiving** ✅ Already Have
   - Receive SMS_DELIVER broadcasts
   - Store incoming messages
   - Display in conversation view

3. **SMS Provider Compliance** ⚠️ REQUIRED
   - Implement Android's SMS ContentProvider contract
   - Support standard URIs (`content://sms/inbox`, `content://sms/sent`)
   - Support standard columns (so other apps can read SMS)

4. **Conversation/Thread View** ⚠️ REQUIRED
   - Group messages by phone number (threads)
   - Show conversation list
   - Show message history in thread view
   - Basic message bubbles (sent vs received)

5. **MMS Receivers** ⚠️ REQUIRED (but minimal implementation OK)
   - `WapPushReceiver` must exist and be registered
   - Can show "MMS not fully supported" message
   - **Full MMS parsing/sending NOT required** (see below)

### ⚠️ **TECHNICALLY REQUIRED but Minimal Implementation OK**

1. **MMS Support** - Android requires MMS receivers, but:
   - ✅ Must have `WapPushReceiver` registered
   - ✅ Must have `MmsSendService` registered
   - ❌ **Full MMS parsing/sending NOT required** for approval
   - You can show "MMS not supported" or basic placeholder
   - Many approved SMS apps have limited MMS support

### 🎯 **HIGHLY RECOMMENDED** (Expected by users, but not strictly required)

1. **Contact Integration**
   - Show contact names instead of just numbers
   - Contact photos
   - Contact picker for new messages
   - **Can start with phone numbers only** - add contacts later

2. **Notifications**
   - Notify on new messages
   - Quick reply from notification
   - **Basic notifications are expected** but simple implementation OK

3. **Message Status** (Basic)
   - Show "sending" indicator
   - Show "sent" status
   - **Delivery reports optional** (nice to have)

### 🎨 **OPTIONAL / NICE-TO-HAVE** (Not required for approval)

1. **Full MMS Implementation**
   - MMS receiving and parsing
   - MMS sending with attachments
   - Media display (images, videos)
   - **Can be Phase 2** - not needed for initial approval

2. **Advanced Features**
   - Search across conversations
   - Message status (delivered, read receipts)
   - Backup/restore
   - Message scheduling
   - Group messaging

3. **Polish Features**
   - Swipe actions
   - Message reactions
   - Themes
   - Customization options

---

## Required Features

### Phase 1: Core SMS Handler (Minimum Viable Product - REQUIRED)

#### 1.1 Database Schema Updates
- [ ] Add `thread_id` to `MessageEntity`
- [ ] Add `type` field (incoming/outgoing)
- [ ] Add `read` field (read/unread status)
- [ ] Add `status` field (pending/sent/delivered/failed)
- [ ] Create `ThreadEntity` table (optional, can compute from messages)
- [ ] Migration script for existing data

#### 1.2 SMS Provider Compliance
- [ ] Update `SmsProvider` to match Android SMS contract
- [ ] Support standard URIs:
  - `content://sms/` (all messages)
  - `content://sms/inbox` (incoming)
  - `content://sms/sent` (outgoing)
  - `content://sms/draft` (drafts)
  - `content://sms/outbox` (pending)
- [ ] Support standard columns:
  - `_id`, `thread_id`, `address`, `body`, `date`, `date_sent`
  - `type` (1=received, 2=sent, 3=draft, 4=outbox, 5=failed, 6=queued)
  - `read` (0=unread, 1=read), `seen` (0=unseen, 1=seen)
  - `status` (for sent messages), `service_center`
- [ ] Handle insert/update/delete/query operations

#### 1.3 Thread Management
- [ ] Calculate thread_id from phone number
- [ ] Group messages by thread
- [ ] Track thread metadata (last message, unread count, etc.)

#### 1.4 SMS Sending
- [ ] Update `SmsDeliverReceiver` to save sent messages
- [ ] Track sent message status
- [ ] Handle delivery reports
- [ ] Handle send failures

### Phase 2: UI Implementation

#### 2.1 Conversation List Screen
- [ ] Create `ConversationListScreen`
- [ ] Show list of conversations (grouped by thread)
- [ ] Display: contact name/number, last message preview, timestamp, unread count
- [ ] Search conversations
- [ ] Swipe actions (delete, archive)
- [ ] Navigation to thread view

#### 2.2 Thread/Conversation View Screen
- [ ] Create `ThreadScreen` or `ConversationScreen`
- [ ] Show message history (chronological)
- [ ] Message bubbles (sent on right, received on left)
- [ ] Show timestamps, delivery status
- [ ] Show classification badges (integrated with existing classification)
- [ ] Reply input at bottom
- [ ] Scroll to bottom on open
- [ ] Mark as read when opened

#### 2.3 Compose Message Screen
- [ ] Create `ComposeScreen`
- [ ] Recipient input (phone number or contact picker)
- [ ] Message text input
- [ ] Send button
- [ ] Character count (for SMS length limits)
- [ ] Handle long messages (split into multiple SMS)
- [ ] Draft saving

#### 2.4 Update Existing Screens
- [ ] Modify `InboxScreen` to show conversations instead of individual messages
- [ ] Add "New Message" FAB
- [ ] Update navigation to use conversation list as home
- [ ] Keep classification features accessible

### Phase 3: Enhanced Features

#### 3.1 Contact Integration
- [ ] Use Android Contacts API
- [ ] Display contact names instead of numbers
- [ ] Contact photos in conversation list
- [ ] Contact picker for new messages

#### 3.2 Notifications
- [ ] Notification for new messages
- [ ] Quick reply from notification
- [ ] Mark as read from notification
- [ ] Notification grouping by conversation

#### 3.3 Message Status
- [ ] Show sending status (sending indicator)
- [ ] Show sent status (checkmark)
- [ ] Show delivered status (double checkmark)
- [ ] Show failed status (error icon)
- [ ] Retry failed messages

#### 3.4 Search & Filter
- [ ] Search across all conversations
- [ ] Search within a conversation
- [ ] Filter by classification (OTP, Phishing, etc.) - keep existing feature
- [ ] Filter by unread

### Phase 4: MMS Support (OPTIONAL - Not Required for Approval)

**Note:** For MVP, you only need to register the receivers. Full implementation can come later.

#### 4.1 MMS Receivers (Minimal - Required Registration)
- [x] `WapPushReceiver` already registered in manifest
- [ ] Show "MMS not fully supported" message when MMS received
- [ ] Log MMS receipt for debugging

#### 4.2 Full MMS Implementation (Optional - Phase 2)
- [ ] Parse MMS messages
- [ ] Download MMS attachments
- [ ] Store media files
- [ ] Display images/videos in conversation
- [ ] Implement `MmsSendService` fully
- [ ] Compose MMS with attachments
- [ ] Image/video picker
- [ ] Send MMS via MMS API

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Make the app technically capable of being a default SMS handler

1. **Database Migration**
   - Add new fields to `MessageEntity`
   - Create migration script
   - Update DAOs

2. **SMS Provider Compliance**
   - Rewrite `SmsProvider` to match Android contract
   - Test with Android's SMS apps
   - Ensure compatibility

3. **Thread Management**
   - Implement thread_id calculation
   - Update message insertion to set thread_id
   - Create thread queries

4. **SMS Sending Updates**
   - Update `SmsDeliverReceiver` to handle sent messages
   - Track message status
   - Save sent messages to database

**Deliverables:**
- Updated database schema
- Compliant SMS Provider
- Thread management working
- Sent messages tracked

---

### Phase 2: Core UI (Week 2-3)

**Goal:** Create basic SMS app UI

1. **Conversation List**
   - Create `ConversationListScreen`
   - Implement ViewModel
   - Connect to database

2. **Thread View**
   - Create `ThreadScreen`
   - Message bubble UI
   - Reply functionality

3. **Compose Screen**
   - Create `ComposeScreen`
   - Send message functionality
   - Integration with SmsSendService

4. **Navigation Updates**
   - Update MainActivity navigation
   - Set conversation list as home
   - Update routes

**Deliverables:**
- Working conversation list
- Working thread view
- Working compose/send
- Basic SMS app functionality

---

### Phase 3: Polish & Integration (Week 3-4)

**Goal:** Make it feel like a real SMS app

1. **Contact Integration**
   - Add Contacts API
   - Display names and photos
   - Contact picker

2. **Notifications**
   - Implement notification system
   - Quick reply
   - Notification actions

3. **Message Status**
   - Status indicators
   - Delivery reports
   - Error handling

4. **Classification Integration**
   - Keep classification badges in thread view
   - Filter by classification
   - Classification settings

**Deliverables:**
- Polished UI with contacts
- Working notifications
- Message status tracking
- Classification features integrated

---

### Phase 4: MMS & Advanced (Week 4-6) - **OPTIONAL**

**Goal:** Full feature parity with basic SMS apps

**Note:** This phase is **NOT required** for Google Play approval. You can submit after Phase 3.

1. **MMS Implementation** (Optional)
   - MMS receiving and parsing
   - MMS sending with attachments
   - Media display (images, videos)
   - **For MVP: Just register receivers, show "MMS not supported" message**

2. **Advanced Features** (Optional)
   - Search
   - Backup/restore
   - Settings improvements
   - Performance optimization

3. **Testing & Bug Fixes**
   - Comprehensive testing
   - Bug fixes
   - Performance tuning

**Deliverables:**
- Full MMS support (if implemented)
- Advanced features
- Tested and polished app

---

## Technical Architecture

### Database Schema Changes

```kotlin
@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    // Existing fields
    val sender: String,  // For incoming: sender number, For outgoing: recipient number
    val body: String,
    val ts: Long,
    
    // New fields for SMS handler
    val threadId: Long,  // Thread ID (calculated from phone number)
    val type: Int,      // 1=received, 2=sent, 3=draft, 4=outbox, 5=failed
    val read: Boolean = false,
    val seen: Boolean = false,
    val status: Int? = null,  // For sent messages: -1=pending, 0=complete, etc.
    val serviceCenter: String? = null,
    
    // Classification fields (existing)
    val language: String? = null,
    val featuresJson: String? = null,
    val isOtp: Boolean? = null,
    val otpIntent: String? = null,
    val isPhishing: Boolean? = null,
    val phishScore: Float? = null,
    val reasonsJson: String? = null,
    val reviewed: Boolean = false,
    val version: Int = 1
)
```

### SMS Provider Contract Implementation

The `SmsProvider` must support these URIs and columns:

**URIs:**
- `content://sms/` - All messages
- `content://sms/inbox` - Incoming messages
- `content://sms/sent` - Sent messages
- `content://sms/draft` - Draft messages
- `content://sms/outbox` - Pending messages
- `content://sms/conversations` - Conversations/threads

**Required Columns:**
- `_id` - Message ID
- `thread_id` - Thread ID
- `address` - Phone number
- `body` - Message text
- `date` - Received/sent timestamp (milliseconds)
- `date_sent` - Sent timestamp (for sent messages)
- `type` - Message type (1=received, 2=sent, etc.)
- `read` - Read status (0=unread, 1=read)
- `seen` - Seen status
- `status` - Delivery status
- `service_center` - Service center number

### Thread ID Calculation

```kotlin
fun calculateThreadId(phoneNumber: String): Long {
    // Normalize phone number (remove non-digits, handle country codes)
    val normalized = phoneNumber.replace(Regex("[^0-9]"), "")
    
    // Use Android's standard thread ID calculation
    // This should match how Android calculates thread_id
    // Typically: hash of normalized number modulo large prime
    return normalized.hashCode().toLong().and(0x7FFFFFFF)
}
```

---

## UI/UX Requirements

### Conversation List Screen

**Layout:**
- AppBar with title "Messages" and search icon
- List of conversations
- FAB for "New Message"
- Each conversation item shows:
  - Contact name/number
  - Last message preview (truncated)
  - Timestamp
  - Unread badge (if unread)
  - Classification badge (if OTP/Phishing)

**Interactions:**
- Tap conversation → Open thread view
- Long press → Context menu (delete, archive, etc.)
- Swipe → Delete or archive
- Search → Filter conversations

### Thread/Conversation View

**Layout:**
- AppBar with contact name/number and back button
- Message list (LazyColumn)
  - Sent messages: Right-aligned bubbles (blue/green)
  - Received messages: Left-aligned bubbles (gray)
  - Show timestamps
  - Show delivery status (for sent)
  - Show classification badges (for received)
- Input field at bottom
  - Text input
  - Send button
  - Attachment button (for MMS)

**Interactions:**
- Type message → Send button enabled
- Tap send → Send message, add to list, scroll to bottom
- Long press message → Copy, delete, etc.
- Scroll to bottom on open
- Mark as read when opened

### Compose Screen

**Layout:**
- AppBar with "New Message" title and back button
- Recipient input (phone number or contact picker)
- Message input (multi-line)
- Character count
- Send button
- Attachment button (for MMS)

**Interactions:**
- Enter recipient → Validate phone number
- Type message → Update character count
- Long message → Show "will be split into X messages"
- Tap send → Send message, navigate to thread view

---

## Testing Checklist

### Functional Testing

- [ ] Receive SMS and display in conversation list
- [ ] Send SMS and see it in thread view
- [ ] Reply to message works
- [ ] Compose new message works
- [ ] Thread grouping works (multiple messages from same number)
- [ ] Read/unread status works
- [ ] Message status tracking works (sending, sent, delivered)
- [ ] Search conversations works
- [ ] Delete conversation works
- [ ] Classification still works on received messages
- [ ] Notifications work for new messages
- [ ] Quick reply from notification works
- [ ] Default SMS app role request works
- [ ] App works as default SMS handler

### Android SMS Contract Testing

- [ ] Other apps can query SMS via ContentProvider
- [ ] SMS backup apps can read messages
- [ ] SMS restore works
- [ ] Standard SMS URIs work (`content://sms/inbox`, etc.)
- [ ] Standard columns are present and correct

### Edge Cases

- [ ] Long messages (split into multiple SMS)
- [ ] Failed message sending (retry works)
- [ ] No network (handle gracefully)
- [ ] Large number of messages (performance)
- [ ] Special characters in messages
- [ ] International phone numbers
- [ ] Group messages (if supported)

### Google Play Testing

- [ ] App can be set as default SMS handler
- [ ] All default handler features work
- [ ] App handles SMS_DELIVER correctly
- [ ] App handles RESPOND_VIA_MESSAGE correctly
- [ ] MMS receiving works (if implemented)
- [ ] MMS sending works (if implemented)

---

## Google Play Compliance

### Required for Approval

1. **Full Default Handler Functionality**
   - Must be able to send SMS
   - Must be able to receive SMS
   - Must display conversations
   - Must handle all SMS operations

2. **SMS Provider Compliance**
   - Must implement Android SMS ContentProvider contract
   - Must support standard URIs and columns
   - Must allow other apps to read SMS (with permissions)

3. **Store Listing**
   - Update description to mention SMS handler functionality
   - Update screenshots to show conversation UI
   - Update feature list

4. **Permissions Declaration**
   - Declare "Default SMS handler" as core functionality
   - Provide instructions for reviewers to test
   - Include video demo if needed

### Review Instructions for Google Play

Create a document explaining:
1. How to set the app as default SMS handler
2. How to test SMS sending
3. How to test SMS receiving
4. How to test conversation view
5. How classification features work
6. Screenshots/video of key features

---

## File Structure

```
app/src/main/java/com/smsclassifier/app/
├── data/
│   ├── MessageEntity.kt (updated)
│   ├── ThreadEntity.kt (new)
│   ├── MessageDao.kt (updated)
│   ├── ThreadDao.kt (new)
│   └── AppDatabase.kt (updated)
├── provider/
│   └── SmsProvider.kt (rewrite)
├── receiver/
│   ├── SmsDeliverReceiver.kt (update)
│   └── WapPushReceiver.kt (implement)
├── service/
│   ├── SmsSendService.kt (update)
│   └── MmsSendService.kt (implement)
├── ui/
│   ├── screens/
│   │   ├── ConversationListScreen.kt (new)
│   │   ├── ThreadScreen.kt (new)
│   │   ├── ComposeScreen.kt (new)
│   │   ├── InboxScreen.kt (update or remove)
│   │   ├── DetailScreen.kt (keep for classification details)
│   │   └── SettingsScreen.kt (update)
│   ├── components/
│   │   ├── MessageBubble.kt (new)
│   │   ├── ConversationItem.kt (new)
│   │   └── ...
│   └── viewmodel/
│       ├── ConversationListViewModel.kt (new)
│       ├── ThreadViewModel.kt (new)
│       ├── ComposeViewModel.kt (new)
│       └── ...
└── util/
    ├── ThreadUtils.kt (new)
    ├── ContactUtils.kt (new)
    └── ...
```

---

## Next Steps

1. **Review this plan** - Ensure all requirements are understood
2. **Prioritize features** - Decide if MMS is required or can be Phase 2
3. **Start Phase 1** - Database migration and SMS Provider compliance
4. **Iterate** - Build incrementally, test frequently
5. **Submit for review** - Once all core features work

---

## Estimated Timeline

### Minimum Viable Product (Required for Approval)
- **Phase 1 (Foundation):** 1-2 weeks
- **Phase 2 (Core UI):** 1-2 weeks  
- **Phase 3 (Polish):** 1 week
- **Total MVP:** 3-5 weeks

### Full Feature Implementation (Optional)
- **Phase 4 (MMS & Advanced):** 1-2 weeks (optional)

**Total:** 3-5 weeks for MVP, 4-7 weeks for full implementation

---

## Notes

- **Classification is still core** - Don't lose the classification features, integrate them into the SMS handler UI
- **Start simple** - Get basic SMS sending/receiving working first, then add polish
- **Test frequently** - Test on real devices, especially default handler functionality
- **Follow Android guidelines** - Use Material Design, follow Android SMS app patterns
- **Documentation** - Keep this plan updated as you implement

---

**Last Updated:** [Current Date]  
**Status:** Ready for Implementation


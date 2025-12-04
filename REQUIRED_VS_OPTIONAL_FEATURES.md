# Required vs Optional Features for Default SMS Handler

## Quick Answer

**MMS Support:** ⚠️ **Partially Required**
- ✅ **Required:** MMS receivers must be registered (`WapPushReceiver`, `MmsSendService`)
- ❌ **NOT Required:** Full MMS parsing, sending, or media display
- You can show "MMS not fully supported" message and still get approved

---

## ✅ REQUIRED Features (Minimum for Google Play Approval)

### 1. SMS Sending ⚠️ **REQUIRED**
- [x] UI to compose new messages
- [x] UI to reply to messages  
- [x] Actually send SMS via `SmsManager`
- [x] Save sent messages to database
- [x] Handle `SENDTO` intents from other apps

### 2. SMS Receiving ✅ **Already Have**
- [x] Receive `SMS_DELIVER` broadcasts
- [x] Store incoming messages
- [x] Display in conversation view

### 3. SMS Provider Compliance ⚠️ **REQUIRED**
- [x] Implement Android's SMS ContentProvider contract
- [x] Support standard URIs:
  - `content://sms/inbox` (incoming)
  - `content://sms/sent` (outgoing)
  - `content://sms/` (all messages)
- [x] Support standard columns:
  - `_id`, `thread_id`, `address`, `body`, `date`, `type`, `read`
- [x] Allow other apps to read SMS (with permissions)

### 4. Conversation/Thread View ⚠️ **REQUIRED**
- [x] Group messages by phone number (threads)
- [x] Show conversation list (list of threads)
- [x] Show message history in thread view
- [x] Basic message bubbles (sent vs received styling)
- [x] Thread ID calculation

### 5. MMS Receivers (Minimal) ⚠️ **REQUIRED Registration**
- [x] Register `WapPushReceiver` in manifest
- [x] Register `MmsSendService` in manifest
- [ ] **Can show "MMS not fully supported" message**
- [ ] **Full MMS implementation NOT required**

### 6. Default Handler Setup ⚠️ **REQUIRED**
- [x] Request default SMS handler role
- [x] Handle default handler responsibilities
- [x] Proper manifest configuration

---

## ⚠️ TECHNICALLY REQUIRED but Minimal Implementation OK

### MMS Support
**What Android Requires:**
- ✅ MMS receivers must be registered in manifest
- ✅ Services must exist

**What's NOT Required:**
- ❌ Full MMS parsing
- ❌ MMS sending with attachments
- ❌ Media display (images, videos)
- ❌ MMS download functionality

**What You Can Do:**
- Show a toast/notification: "MMS received but not fully supported"
- Log the MMS for debugging
- Store basic MMS metadata if possible
- **This is acceptable for Google Play approval**

---

## 🎯 HIGHLY RECOMMENDED (Expected but Not Strictly Required)

### 1. Contact Integration
- Show contact names (can start with phone numbers only)
- Contact photos (nice to have)
- Contact picker (can use manual number entry)

**MVP Approach:** Start with phone numbers, add contacts in Phase 2

### 2. Basic Notifications
- Notify on new messages
- Basic notification (can skip quick reply initially)

**MVP Approach:** Simple notification, add quick reply later

### 3. Message Status (Basic)
- Show "sending" indicator
- Show "sent" status
- Delivery reports (optional)

**MVP Approach:** Basic sending/sent status, skip delivery reports initially

---

## 🎨 OPTIONAL / NOT REQUIRED

### 1. Full MMS Implementation
- ❌ MMS receiving and parsing
- ❌ MMS sending with attachments
- ❌ Media display (images, videos, audio)
- **Can be Phase 2 or later**

### 2. Advanced Features
- ❌ Search across conversations
- ❌ Message status (delivered, read receipts)
- ❌ Backup/restore
- ❌ Message scheduling
- ❌ Group messaging
- ❌ Quick reply from notifications
- ❌ Swipe actions
- ❌ Themes and customization

---

## Minimum Viable Product (MVP) Checklist

To get approved by Google Play, you need:

### Core Functionality
- [x] Send SMS (with UI)
- [x] Receive SMS
- [x] Conversation/thread view
- [x] SMS Provider compliance
- [x] MMS receivers registered (can be minimal)

### UI Requirements
- [x] Conversation list screen
- [x] Thread/conversation view
- [x] Compose message screen
- [x] Reply functionality
- [x] Basic message bubbles

### Technical Requirements
- [x] Default SMS handler role request
- [x] SMS_DELIVER receiver
- [x] WAP_PUSH receiver (can be minimal)
- [x] SENDTO intent filters
- [x] SMS Provider with standard contract

### What You DON'T Need for MVP
- ❌ Full MMS support
- ❌ Contact integration (can use phone numbers)
- ❌ Advanced notifications
- ❌ Search functionality
- ❌ Message status tracking
- ❌ Backup/restore
- ❌ Any advanced features

---

## Recommended Development Order

### Phase 1: MVP (Required for Approval) - 3-5 weeks
1. Database schema updates (thread_id, type, read)
2. SMS Provider compliance
3. Conversation list UI
4. Thread view UI
5. Compose message UI
6. Basic MMS receiver (show "not supported")
7. Testing and submission

### Phase 2: Enhancements (After Approval) - 1-2 weeks
1. Contact integration
2. Better notifications
3. Message status tracking
4. Search functionality

### Phase 3: Advanced (Optional) - 1-2 weeks
1. Full MMS support
2. Backup/restore
3. Advanced features

---

## Summary

**MMS Support:**
- ✅ **Required:** Register MMS receivers in manifest
- ❌ **NOT Required:** Full MMS implementation

**Features NOT Required:**
- Full MMS parsing/sending
- Contact integration (can use phone numbers)
- Advanced notifications
- Search functionality
- Message status tracking (delivery reports)
- Backup/restore
- Any advanced/polish features

**Focus on MVP:**
1. Send SMS (with UI)
2. Receive SMS (already have)
3. Conversation view
4. SMS Provider compliance
5. Basic MMS receiver registration

**Timeline:** 3-5 weeks for MVP, then submit for approval. Add features later.

---

## Google Play Review Tips

When submitting:
1. **Clearly document** that MMS receivers are registered but full MMS is not yet implemented
2. **Show screenshots** of:
   - Conversation list
   - Thread view with sent/received messages
   - Compose message screen
3. **Provide test instructions:**
   - How to set as default SMS handler
   - How to send a test SMS
   - How to receive a test SMS
   - How to view conversations
4. **Note in description:** "MMS support coming in future update" (if applicable)

---

**Last Updated:** Based on current Google Play requirements  
**Status:** MVP requirements defined


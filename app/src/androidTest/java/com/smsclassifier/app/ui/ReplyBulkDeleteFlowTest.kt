package com.smsclassifier.app.ui

import android.Manifest
import android.app.NotificationManager
import android.content.ContentResolver
import android.net.Uri
import android.os.Build
import android.os.SystemClock
import android.provider.Telephony
import androidx.activity.ComponentActivity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.getBoundsInRoot
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeUp
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.smsclassifier.app.ReplyDraftsViewModel
import com.smsclassifier.app.data.AppDatabase
import com.smsclassifier.app.data.BulkSmsDeletion
import com.smsclassifier.app.data.MessageEntity
import com.smsclassifier.app.ui.components.BulkDeleteControls
import com.smsclassifier.app.ui.components.BulkDeleteMessageRow
import com.smsclassifier.app.ui.components.BulkDeleteRow
import com.smsclassifier.app.ui.screens.DetailScreen
import com.smsclassifier.app.ui.screens.ThreadScreen
import com.smsclassifier.app.ui.theme.SMSClassifierTheme
import com.smsclassifier.app.ui.viewmodel.DetailViewModel
import com.smsclassifier.app.ui.viewmodel.ThreadViewModel
import com.smsclassifier.app.util.NotificationHelper
import com.smsclassifier.app.util.ReplyPolicy
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ReplyBulkDeleteFlowTest {
    @get:Rule
    val rule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun cancelAndBackPreserveDraftAndMessages() {
        val db = newDatabase()
        val store = ViewModelStore()
        try {
            val threadId = 77L
            val first = fixtureMessage(601, threadId, "Synthetic thread hello")
            val second = fixtureMessage(602, threadId, "Synthetic thread follow-up")
            runBlocking {
                db.messageDao().insert(first)
                db.messageDao().insert(second)
            }
            val viewModel = viewModel(store) { ThreadViewModel(db) }
            val drafts = ReplyDraftsViewModel()
            var backs = 0
            var visible by mutableStateOf(true)
            setAppContent {
                if (visible) {
                    ThreadScreen(
                        threadId = threadId,
                        viewModel = viewModel,
                        onBack = { backs += 1 },
                        drafts = drafts
                    )
                }
            }
            waitForText("Synthetic thread hello")
            rule.onNodeWithContentDescription("Message").performTextInput("synthetic draft")
            rule.waitForIdle()
            assertEquals("+14155550123", ReplyPolicy.recipient(first.sender))
            assertEquals("synthetic draft", drafts.get("+14155550123"))

            rule.onNodeWithTag("bulk-select").assertIsEnabled().performClick()
            rule.onNodeWithTag("bulk-row-601").performClick()
            rule.onNodeWithText("1 selected").assertExists()
            rule.onNodeWithTag("bulk-cancel").performClick()
            rule.onNodeWithTag("bulk-select").assertExists()
            assertEquals("synthetic draft", drafts.get("+14155550123"))

            rule.onNodeWithTag("bulk-select").performClick()
            rule.onNodeWithTag("bulk-row-602").performClick()
            rule.activity.onBackPressedDispatcher.onBackPressed()
            rule.waitForIdle()
            rule.onNodeWithTag("bulk-select").assertExists()
            assertEquals(0, backs)

            rule.onNodeWithTag("bulk-select").performClick()
            rule.onNodeWithContentDescription("Cancel selection").performClick()
            rule.onNodeWithTag("bulk-select").assertExists()
            rule.onNodeWithContentDescription("Back").performClick()
            rule.waitForIdle()
            assertEquals(1, backs)

            rule.runOnIdle { visible = false }
            rule.runOnIdle { visible = true }
            waitForText("Synthetic thread hello")
            rule.onNodeWithContentDescription("Message").assertExists()
            assertEquals("synthetic draft", drafts.get("+14155550123"))
            assertEquals(2, runBlocking { db.messageDao().getMessageCountForThread(threadId) })
        } finally {
            store.clear()
            db.close()
        }
    }

    @Test
    fun exactMessageDeleteLeavesTheRestOfTheConversation() {
        val fx = SmsFixture()
        try {
            val selected = fixtureMessage(501, 10, "Synthetic selected text", providerId = null)
            val sibling = fixtureMessage(502, 10, "Synthetic sibling text", providerId = 9002)
            val other = fixtureMessage(503, 20, "Synthetic other thread", providerId = 9003)
            runBlocking {
                listOf(selected, sibling, other).forEach { fx.database.messageDao().insert(it) }
            }
            SyntheticSmsProvider.add(9001, selected)
            SyntheticSmsProvider.add(9002, sibling)
            SyntheticSmsProvider.add(9003, other)
            showDeleteHarness(fx, conversations = false, rows = listOf(selected, sibling, other))

            rule.onNodeWithTag("bulk-select").performClick()
            rule.onNodeWithTag("bulk-row-501").performClick()
            rule.onNodeWithTag("bulk-request-delete").performClick()
            waitForText("Delete 1 message?")
            rule.onNodeWithText("This permanently deletes the 1 message included in this selection.")
                .assertExists()
            rule.onNodeWithTag("bulk-confirm").performClick()
            waitForText("Deleted 1 message.")

            assertEquals(setOf(502L, 503L), localIds(fx))
            assertEquals(setOf(9002L, 9003L), SyntheticSmsProvider.ids())
        } finally {
            closeHarness(fx)
        }
    }

    @Test
    fun conversationDeleteIncludesMessagesOutsideTheVisibleRow() {
        val fx = SmsFixture()
        try {
            val visible = fixtureMessage(511, 10, "Synthetic visible conversation", providerId = 9111)
            val hidden = fixtureMessage(512, 10, "Synthetic hidden conversation", providerId = 9112)
            val other = fixtureMessage(513, 20, "Synthetic kept conversation", providerId = 9113)
            runBlocking {
                listOf(visible, hidden, other).forEach { fx.database.messageDao().insert(it) }
            }
            listOf(9111L to visible, 9112L to hidden, 9113L to other).forEach { (id, message) ->
                SyntheticSmsProvider.add(id, message)
            }
            showDeleteHarness(fx, conversations = true, rows = listOf(visible, other))

            rule.onNodeWithTag("bulk-select").performClick()
            rule.onNodeWithText("Select conversations").assertDoesNotExist()
            rule.onNodeWithTag("bulk-row-10").performClick()
            rule.onNodeWithTag("bulk-request-delete").performClick()
            waitForText("Delete 1 conversation containing 2 messages?")
            rule.onNodeWithText(
                "including messages outside the current filter.",
                substring = true
            ).assertExists()
            rule.onNodeWithTag("bulk-confirm").performClick()
            waitForText("Deleted 2 messages.")

            assertEquals(setOf(513L), localIds(fx))
            assertEquals(setOf(9113L), SyntheticSmsProvider.ids())
        } finally {
            closeHarness(fx)
        }
    }

    @Test
    fun dialogCancelAndBackPreserveSyntheticRows() {
        val fx = SmsFixture()
        try {
            val message = fixtureMessage(521, 10, "Synthetic preserved text", providerId = 9211)
            runBlocking { fx.database.messageDao().insert(message) }
            SyntheticSmsProvider.add(9211, message)
            showDeleteHarness(fx, conversations = false, rows = listOf(message))

            rule.onNodeWithTag("bulk-select").performClick()
            rule.onNodeWithTag("bulk-row-521").performClick()
            rule.onNodeWithTag("bulk-request-delete").performClick()
            waitForText("Delete 1 message?")
            rule.onNodeWithTag("bulk-dismiss").performClick()
            rule.onNodeWithText("Delete 1 message?").assertDoesNotExist()
            rule.onNodeWithText("1 selected").assertExists()

            rule.onNodeWithTag("bulk-request-delete").performClick()
            waitForText("Delete 1 message?")
            rule.activity.onBackPressedDispatcher.onBackPressed()
            rule.waitForIdle()
            rule.onNodeWithText("Delete 1 message?").assertDoesNotExist()
            rule.onNodeWithText("1 selected").assertExists()
            rule.onNodeWithText("Deleted 1 message.").assertDoesNotExist()

            assertEquals(setOf(521L), localIds(fx))
            assertEquals(setOf(9211L), SyntheticSmsProvider.ids())
        } finally {
            closeHarness(fx)
        }
    }

    @Test
    fun senderEligibilityOnDetailAndThread() {
        val db = newDatabase()
        val store = ViewModelStore()
        try {
            val phone = fixtureMessage(701, 71, "Synthetic phone hello", sender = "+1 (415) 555-0123")
            val shortCode = fixtureMessage(702, 72, "Synthetic short-code hello", sender = "12345")
            val brand = fixtureMessage(703, 73, "Synthetic brand hello", sender = "VM-SBIOTP")
            runBlocking {
                listOf(phone, shortCode, brand).forEach { db.messageDao().insert(it) }
            }
            var replies = 0
            var step by mutableStateOf(0)
            val detailViewModel = viewModel(store) { DetailViewModel(db) }
            val threadViewModel = viewModel(store) { ThreadViewModel(db) }
            setAppContent {
                when (step) {
                    0 -> DetailScreen(phone.id, detailViewModel, onBack = {}, onReply = { replies += 1 })
                    1 -> DetailScreen(shortCode.id, detailViewModel, onBack = {}, onReply = { replies += 1 })
                    2 -> ThreadScreen(phone.threadId, threadViewModel, onBack = {}, drafts = ReplyDraftsViewModel())
                    else -> ThreadScreen(brand.threadId, threadViewModel, onBack = {}, drafts = ReplyDraftsViewModel())
                }
            }
            waitForText("Reply")
            rule.onNodeWithText(ReplyPolicy.UNAVAILABLE_MESSAGE).assertDoesNotExist()
            rule.onNodeWithText("Reply").performClick()
            rule.waitForIdle()
            assertEquals(1, replies)
            rule.onNodeWithText("Reply to this sender?").assertDoesNotExist()

            rule.runOnIdle { step = 1 }
            waitForText(ReplyPolicy.UNAVAILABLE_MESSAGE)
            rule.onNodeWithText("Reply").assertDoesNotExist()
            rule.onNodeWithText("Reply…").assertDoesNotExist()
            assertEquals(1, replies)

            rule.runOnIdle { step = 2 }
            waitForText("Synthetic phone hello")
            rule.onNodeWithContentDescription("Message").assertExists()

            rule.runOnIdle { step = 3 }
            waitForText(ReplyPolicy.UNAVAILABLE_MESSAGE)
            rule.onNodeWithContentDescription("Message").assertDoesNotExist()
        } finally {
            store.clear()
            db.close()
        }
    }

    @Test
    fun flaggedReplyGuardPreservesTheMessageUntilConfirmed() {
        val db = newDatabase()
        val store = ViewModelStore()
        try {
            val flagged = fixtureMessage(
                801, 81, "Synthetic flagged hello", phishing = true
            )
            runBlocking { db.messageDao().insert(flagged) }
            var replies = 0
            setAppContent {
                DetailScreen(
                    messageId = flagged.id,
                    viewModel = viewModel(store) { DetailViewModel(db) },
                    onBack = {},
                    onReply = { replies += 1 },
                    showReplyWarningOnOpen = true,
                    onReplyWarningShown = {}
                )
            }
            waitForText("Reply to this sender?")
            assertEquals(0, replies)
            rule.onNodeWithText("Cancel").performClick()
            rule.waitForIdle()
            rule.onNodeWithText("Reply to this sender?").assertDoesNotExist()
            assertEquals(0, replies)
            assertNotNull(runBlocking { db.messageDao().getById(flagged.id) })

            rule.onNodeWithText("Reply…").performClick()
            waitForText("Reply anyway")
            rule.onNodeWithText("Cancel").performClick()
            assertEquals(0, replies)

            rule.onNodeWithText("Reply…").performClick()
            rule.onNodeWithText("Reply anyway").performClick()
            rule.waitForIdle()
            assertEquals(1, replies)
            assertNotNull(runBlocking { db.messageDao().getById(flagged.id) })
        } finally {
            store.clear()
            db.close()
        }
    }

    @Test
    fun safeReplyOpenDoesNotShowTheFlaggedGuard() {
        val db = newDatabase()
        val store = ViewModelStore()
        try {
            val safe = fixtureMessage(802, 82, "Synthetic safe hello")
            runBlocking { db.messageDao().insert(safe) }
            var replies = 0
            setAppContent {
                DetailScreen(
                    messageId = safe.id,
                    viewModel = viewModel(store) { DetailViewModel(db) },
                    onBack = {},
                    onReply = { replies += 1 },
                    showReplyWarningOnOpen = true
                )
            }
            waitForText("Reply")
            rule.onNodeWithText("Reply to this sender?").assertDoesNotExist()
            rule.onNodeWithText("Reply…").assertDoesNotExist()
            assertEquals(0, replies)
            assertEquals(ReplyPolicy.Route.COMPOSER, ReplyPolicy.route(safe))
        } finally {
            store.clear()
            db.close()
        }
    }

    @Test
    fun detailActionsStayReachableForLongTextAndLargeFont() {
        val db = newDatabase()
        val store = ViewModelStore()
        try {
            val head = "Synthetic long message start."
            val body = "$head " + "Additional sentence for length. ".repeat(50)
            val phone = fixtureMessage(811, 91, body)
            val oneWay = fixtureMessage(812, 92, body, sender = "VM-SBIOTP")
            val flagged = fixtureMessage(813, 93, body, phishing = true)
            val otp = fixtureMessage(
                814,
                94,
                "Your OTP is 847291. Do not share it with anyone. $body"
            ).copy(isOtp = true, userCorrected = true)
            runBlocking {
                listOf(phone, oneWay, flagged, otp).forEach { db.messageDao().insert(it) }
            }
            var step by mutableStateOf(0)
            var replies = 0
            val detailViewModel = viewModel(store) { DetailViewModel(db) }
            setAppContent {
                val base = LocalDensity.current
                CompositionLocalProvider(
                    LocalDensity provides Density(density = base.density, fontScale = 2f)
                ) {
                    DetailScreen(
                        messageId = when (step) {
                            1 -> oneWay.id
                            2 -> flagged.id
                            3 -> otp.id
                            else -> phone.id
                        },
                        viewModel = detailViewModel,
                        onBack = {},
                        onReply = { replies += 1 },
                        showReplyWarningOnOpen = step == 2
                    )
                }
            }

            waitForText("Reply")
            assertPinnedWhileTheMessageScrolls("detail-reply")
            assertEquals(0, replies)

            rule.runOnIdle { step = 1 }
            waitForText(ReplyPolicy.UNAVAILABLE_MESSAGE)
            rule.onNodeWithTag("detail-reply").assertDoesNotExist()
            rule.onNodeWithTag("detail-reply-unavailable")
                .assertTextEquals(ReplyPolicy.UNAVAILABLE_MESSAGE)
            assertPinnedWhileTheMessageScrolls("detail-reply-unavailable")

            rule.runOnIdle { step = 2 }
            waitForText("Reply anyway")
            assertTextFullyVisible("Reply anyway")
            rule.onNodeWithText("Cancel").performClick()
            rule.waitForIdle()
            rule.onNodeWithText("Reply…").assertIsDisplayed()
            assertPinnedWhileTheMessageScrolls("detail-reply")
            assertEquals(0, replies)

            rule.runOnIdle { step = 3 }
            waitForText("Copy OTP")
            assertFullyVisible("detail-reply")
            rule.onNodeWithText("Copy OTP").performScrollTo().assertIsDisplayed()
            val copyBounds = rule.onNodeWithText("Copy OTP").getBoundsInRoot()
            val replyBounds = rule.onNodeWithTag("detail-reply").getBoundsInRoot()
            assertTrue(copyBounds.bottom - copyBounds.top >= 48.dp)
            assertTrue(copyBounds.bottom <= replyBounds.top)
            assertFullyVisible("detail-reply")
            assertEquals(0, replies)
        } finally {
            store.clear()
            db.close()
        }
    }

    private fun assertFullyVisible(tag: String) {
        val root = rule.onRoot().getBoundsInRoot()
        val bounds = rule.onNodeWithTag(tag).assertIsDisplayed().getBoundsInRoot()
        assertTrue("$tag $bounds is outside $root", bounds.left >= root.left && bounds.right <= root.right)
        assertTrue("$tag $bounds is outside $root", bounds.top >= root.top && bounds.bottom <= root.bottom)
    }

    private fun assertTextFullyVisible(text: String) {
        val node = rule.onNodeWithText(text).assertIsDisplayed().fetchSemanticsNode()
        val bounds = node.boundsInRoot
        var root = node
        while (root.parent != null) root = root.parent!!
        val rootBounds = root.boundsInRoot
        assertTrue(
            "$text $bounds is outside $rootBounds",
            bounds.left >= rootBounds.left - 1f &&
                bounds.top >= rootBounds.top - 1f &&
                bounds.right <= rootBounds.right + 1f &&
                bounds.bottom <= rootBounds.bottom + 1f
        )
    }

    private fun assertPinnedWhileTheMessageScrolls(tag: String) {
        assertFullyVisible(tag)
        val before = rule.onNodeWithTag(tag).getBoundsInRoot()
        val scroller = rule.onNode(hasScrollAction())
        val start = scrollPosition()
        assertTrue("message fits without scrolling: $start / ${scrollMaximum()}", scrollMaximum() > start + 1f)
        scroller.performTouchInput { swipeUp() }
        rule.waitForIdle()
        assertTrue("message did not scroll", scrollPosition() > start)
        val after = rule.onNodeWithTag(tag).getBoundsInRoot()
        assertFullyVisible(tag)
        assertTrue("sticky action moved from $before to $after", kotlin.math.abs(before.top.value - after.top.value) < 1f)
        assertTrue("sticky action moved from $before to $after", kotlin.math.abs(before.bottom.value - after.bottom.value) < 1f)
    }

    private fun scrollPosition(): Float = readScrollAxis { it.value() }

    private fun scrollMaximum(): Float = readScrollAxis { it.maxValue() }

    private fun readScrollAxis(read: (androidx.compose.ui.semantics.ScrollAxisRange) -> Float): Float {
        var reading = 0f
        rule.onNode(
            hasScrollAction().and(
                SemanticsMatcher("scroll axis") { node ->
                    reading = read(node.config[SemanticsProperties.VerticalScrollAxisRange])
                    true
                }
            )
        ).assertExists()
        return reading
    }

    private fun showDeleteHarness(fx: SmsFixture, conversations: Boolean, rows: List<MessageEntity>) {
        val deletion = BulkSmsDeletion(fx.database, fx.uri)
        setAppContent {
            DeleteHarness(deletion, fx.resolver, conversations, rows)
        }
        waitForText(if (conversations) "Select conversations" else "Select messages")
    }

    private fun closeHarness(fx: SmsFixture) {
        fx.close()
    }

    private fun setAppContent(content: @Composable () -> Unit) {
        rule.setContent {
            SMSClassifierTheme(darkTheme = false, dynamicColor = false, content = content)
        }
    }

    private fun waitForText(text: String) {
        rule.waitUntil(5_000) {
            rule.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().isNotEmpty()
        }
    }

    private fun localIds(fx: SmsFixture): Set<Long> = runBlocking {
        fx.database.messageDao().getByIds(listOf(501, 502, 503, 511, 512, 513, 521)).map { it.id }.toSet()
    }
}

@RunWith(AndroidJUnit4::class)
class NotificationReplyRoutingTest {
    @Test
    fun replyActionIsAddedOnlyForPhoneSenders() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            instrumentation.uiAutomation.grantRuntimePermission(
                context.packageName,
                Manifest.permission.POST_NOTIFICATIONS
            )
        }
        val manager = context.getSystemService(NotificationManager::class.java)
        val ids = intArrayOf(930_101, 930_102, 930_103)
        try {
            val phone = actionTitles(context, manager, 930_101, "+14155550123")
            assertTrue(phone.contains("Reply"))
            assertTrue(phone.contains("Mark as read"))
            val shortCode = actionTitles(context, manager, 930_102, "12345")
            assertFalse(shortCode.contains("Reply"))
            assertTrue(shortCode.contains("Mark as read"))
            val brand = actionTitles(context, manager, 930_103, "VM-SBIOTP")
            assertFalse(brand.contains("Reply"))
            assertTrue(brand.contains("Mark as read"))
        } finally {
            ids.forEach(manager::cancel)
            manager.cancel(0)
        }
    }

    private fun actionTitles(
        context: android.content.Context,
        manager: NotificationManager,
        id: Int,
        sender: String
    ): List<String> {
        NotificationHelper.showNewMessageNotification(
            context = context,
            messageId = id.toLong(),
            sender = sender,
            body = "Synthetic hello from the test fixture",
            threadId = id.toLong()
        )
        val deadline = SystemClock.elapsedRealtime() + 2_000
        var posted = manager.activeNotifications.firstOrNull { it.id == id }
        while (posted == null && SystemClock.elapsedRealtime() < deadline) {
            SystemClock.sleep(50)
            posted = manager.activeNotifications.firstOrNull { it.id == id }
        }
        assertNotNull("Notification $id for $sender was not posted", posted)
        return posted!!.notification.actions.orEmpty().map { it.title.toString() }
    }
}

@Composable
private fun DeleteHarness(
    deletion: BulkSmsDeletion,
    resolver: ContentResolver,
    conversations: Boolean,
    rows: List<MessageEntity>
) {
    val selection = com.smsclassifier.app.ui.components.rememberBulkDeleteSelection()
    androidx.compose.foundation.layout.Column {
        BulkDeleteControls(
            selection = selection,
            deletion = deletion,
            conversations = conversations,
            canSelect = rows.isNotEmpty(),
            contentResolver = resolver
        )
        if (selection.active) rows.forEach { message ->
            if (conversations) {
                BulkDeleteRow(
                    selection = selection,
                    id = message.threadId,
                    title = message.sender,
                    preview = message.body,
                    timestamp = message.ts
                )
            } else {
                BulkDeleteMessageRow(selection, message)
            }
        }
    }
}

private class SmsFixture {
    val uri: Uri = Uri.parse("content://com.smsclassifier.app.test.sms")
    val database: AppDatabase
    val resolver: ContentResolver

    init {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        database = Room.inMemoryDatabaseBuilder(instrumentation.targetContext, AppDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        resolver = instrumentation.targetContext.contentResolver
        SyntheticSmsProvider.reset()
    }

    fun close() {
        database.close()
        SyntheticSmsProvider.reset()
    }
}

private fun newDatabase(): AppDatabase {
    val context = InstrumentationRegistry.getInstrumentation().targetContext
    return Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java)
        .allowMainThreadQueries()
        .build()
}

private inline fun <reified T : ViewModel> viewModel(store: ViewModelStore, crossinline create: () -> T): T {
    return ViewModelProvider(store, object : ViewModelProvider.Factory {
        override fun <M : ViewModel> create(modelClass: Class<M>): M {
            @Suppress("UNCHECKED_CAST")
            return create() as M
        }
    })[T::class.java]
}

private fun fixtureMessage(
    id: Long,
    threadId: Long,
    body: String,
    sender: String = "+14155550123",
    providerId: Long? = null,
    phishing: Boolean = false
) = MessageEntity(
    id = id,
    sender = sender,
    body = body,
    ts = 1_700_000_000_000L + id,
    threadId = threadId,
    type = Telephony.Sms.MESSAGE_TYPE_INBOX,
    read = true,
    seen = true,
    sourceProviderId = providerId,
    isPhishing = phishing,
    phishScore = if (phishing) 0.91f else 0.05f,
    reviewed = true
)

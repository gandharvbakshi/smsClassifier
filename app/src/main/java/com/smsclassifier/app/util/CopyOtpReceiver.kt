package com.smsclassifier.app.util

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.core.content.getSystemService

class CopyOtpReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val otpCode = intent.getStringExtra(EXTRA_OTP_CODE).orEmpty()
        if (otpCode.isBlank()) return

        val clipboard = context.getSystemService<android.content.ClipboardManager>()
        val clip = android.content.ClipData.newPlainText("OTP", otpCode)
        clipboard?.setPrimaryClip(clip)
        Toast.makeText(context, "OTP copied to clipboard", Toast.LENGTH_SHORT).show()
    }

    companion object {
        const val EXTRA_OTP_CODE = "otpCode"
    }
}


package com.smsclassifier.app.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.smsclassifier.app.util.AppLog

class MmsSendService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        AppLog.d(TAG, "Received MMS send request (not implemented)")
        stopSelf(startId)
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "MmsSendService"
    }
}

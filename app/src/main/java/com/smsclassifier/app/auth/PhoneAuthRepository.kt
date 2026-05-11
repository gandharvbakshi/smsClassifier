package com.smsclassifier.app.auth

import android.app.Activity
import android.content.Context
import com.google.firebase.FirebaseException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.auth.PhoneAuthOptions
import com.google.firebase.auth.PhoneAuthProvider
import com.smsclassifier.app.util.AppLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.util.concurrent.TimeUnit

sealed class PhoneAuthUiState {
    data object Idle : PhoneAuthUiState()
    data class AwaitingCode(
        val verificationId: String,
        val resendToken: PhoneAuthProvider.ForceResendingToken?
    ) : PhoneAuthUiState()

    data class Success(val uid: String) : PhoneAuthUiState()
    data class Error(val message: String) : PhoneAuthUiState()
}

class PhoneAuthRepository(context: Context) {

    private val auth = FirebaseAuth.getInstance()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    private val _state = MutableStateFlow<PhoneAuthUiState>(PhoneAuthUiState.Idle)
    val state: StateFlow<PhoneAuthUiState> = _state.asStateFlow()

    private var verificationId: String? = null
    private var resendToken: PhoneAuthProvider.ForceResendingToken? = null

    private fun userMessage(t: Throwable?): String {
        return when (t) {
            is FirebaseAuthInvalidCredentialsException -> "That code is not valid. Try again."
            is FirebaseException -> t.message?.takeIf { it.isNotBlank() } ?: "Verification failed."
            else -> t?.message?.takeIf { it.isNotBlank() } ?: "Something went wrong."
        }
    }

    private fun callbacks(): PhoneAuthProvider.OnVerificationStateChangedCallbacks =
        object : PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
            override fun onVerificationCompleted(credential: PhoneAuthCredential) {
                scope.launch {
                    runCatching {
                        auth.signInWithCredential(credential).await()
                        val uid = auth.currentUser?.uid ?: error("missing uid")
                        _state.value = PhoneAuthUiState.Success(uid)
                    }.onFailure { e ->
                        AppLog.w(TAG, "auto sign-in failed: ${e.message}", e)
                        _state.value = PhoneAuthUiState.Error(userMessage(e))
                    }
                }
            }

            override fun onVerificationFailed(e: FirebaseException) {
                AppLog.w(TAG, "verification failed: ${e.message}", e)
                _state.value = PhoneAuthUiState.Error(userMessage(e))
            }

            override fun onCodeSent(
                vid: String,
                token: PhoneAuthProvider.ForceResendingToken
            ) {
                verificationId = vid
                resendToken = token
                _state.value = PhoneAuthUiState.AwaitingCode(vid, token)
            }
        }

    fun sendCode(activity: Activity, e164: String) {
        _state.value = PhoneAuthUiState.Idle
        verificationId = null
        resendToken = null
        val options = PhoneAuthOptions.newBuilder(auth)
            .setPhoneNumber(e164)
            .setTimeout(60L, TimeUnit.SECONDS)
            .setActivity(activity)
            .setCallbacks(callbacks())
            .build()
        PhoneAuthProvider.verifyPhoneNumber(options)
    }

    fun resend(activity: Activity, e164: String) {
        val token = resendToken
        if (token == null) {
            sendCode(activity, e164)
            return
        }
        val options = PhoneAuthOptions.newBuilder(auth)
            .setPhoneNumber(e164)
            .setTimeout(60L, TimeUnit.SECONDS)
            .setActivity(activity)
            .setCallbacks(callbacks())
            .setForceResendingToken(token)
            .build()
        PhoneAuthProvider.verifyPhoneNumber(options)
    }

    suspend fun verifySmsCode(code: String) {
        val vid = verificationId
        if (vid.isNullOrBlank()) {
            _state.value = PhoneAuthUiState.Error("Request a new code first.")
            return
        }
        val credential = PhoneAuthProvider.getCredential(vid, code.trim())
        runCatching {
            auth.signInWithCredential(credential).await()
            val uid = auth.currentUser?.uid ?: error("missing uid")
            _state.value = PhoneAuthUiState.Success(uid)
        }.onFailure { e ->
            AppLog.w(TAG, "verify code failed: ${e.message}", e)
            _state.value = PhoneAuthUiState.Error(userMessage(e))
        }
    }

    fun clearError() {
        if (_state.value is PhoneAuthUiState.Error) {
            _state.value = PhoneAuthUiState.Idle
        }
    }

    companion object {
        private const val TAG = "PhoneAuth"
    }
}

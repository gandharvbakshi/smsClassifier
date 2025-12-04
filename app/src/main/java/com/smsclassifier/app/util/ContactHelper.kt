package com.smsclassifier.app.util

import android.content.ContentResolver
import android.content.Context
import android.database.Cursor
import android.provider.ContactsContract
import android.provider.ContactsContract.CommonDataKinds.Phone
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object ContactHelper {
    /**
     * Get contact name for a phone number
     */
    suspend fun getContactName(context: Context, phoneNumber: String): String? = withContext(Dispatchers.IO) {
        val normalizedNumber = normalizePhoneNumber(phoneNumber)
        val contentResolver: ContentResolver = context.contentResolver
        
        val uri = Phone.CONTENT_URI
        val projection = arrayOf(Phone.DISPLAY_NAME, Phone.NUMBER)
        val selection = "${Phone.NUMBER} = ? OR ${Phone.NUMBER} LIKE ? OR ${Phone.NUMBER} LIKE ?"
        val selectionArgs = arrayOf(
            normalizedNumber,
            "%$normalizedNumber",
            normalizedNumber.replace(" ", "")
        )
        
        contentResolver.query(uri, projection, selection, selectionArgs, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(Phone.DISPLAY_NAME)
                if (nameIndex >= 0) {
                    return@withContext cursor.getString(nameIndex)
                }
            }
        }
        
        // Also try lookup by contact ID
        val lookupUri = ContactsContract.PhoneLookup.CONTENT_FILTER_URI.buildUpon()
            .appendPath(normalizedNumber)
            .build()
        
        contentResolver.query(lookupUri, arrayOf(ContactsContract.PhoneLookup.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(ContactsContract.PhoneLookup.DISPLAY_NAME)
                if (nameIndex >= 0) {
                    return@withContext cursor.getString(nameIndex)
                }
            }
        }
        
        null
    }
    
    /**
     * Get contact photo URI for a phone number
     */
    suspend fun getContactPhotoUri(context: Context, phoneNumber: String): android.net.Uri? = withContext(Dispatchers.IO) {
        val normalizedNumber = normalizePhoneNumber(phoneNumber)
        val contentResolver: ContentResolver = context.contentResolver
        
        val lookupUri = ContactsContract.PhoneLookup.CONTENT_FILTER_URI.buildUpon()
            .appendPath(normalizedNumber)
            .build()
        
        contentResolver.query(
            lookupUri,
            arrayOf(ContactsContract.PhoneLookup.PHOTO_URI),
            null,
            null,
            null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val photoIndex = cursor.getColumnIndex(ContactsContract.PhoneLookup.PHOTO_URI)
                if (photoIndex >= 0) {
                    val photoUri = cursor.getString(photoIndex)
                    if (!photoUri.isNullOrBlank()) {
                        return@withContext android.net.Uri.parse(photoUri)
                    }
                }
            }
        }
        
        null
    }
    
    /**
     * Normalize phone number for lookup (remove spaces, dashes, etc.)
     */
    private fun normalizePhoneNumber(phoneNumber: String): String {
        return phoneNumber.replace(Regex("[^0-9+]"), "")
    }
    
    /**
     * Get display name (contact name or phone number)
     */
    suspend fun getDisplayName(context: Context, phoneNumber: String): String {
        return getContactName(context, phoneNumber) ?: phoneNumber
    }
}


package com.smsclassifier.app.ui.screens

import android.content.Intent
import android.content.Context
import android.provider.ContactsContract
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Contacts
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.viewmodel.ComposeViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComposeScreen(
    viewModel: ComposeViewModel,
    initialAddress: String? = null,
    onBack: () -> Unit,
    onMessageSent: () -> Unit,
    modifier: Modifier = Modifier
) {
    val address by viewModel.address.collectAsState()
    val message by viewModel.message.collectAsState()
    val isSending by viewModel.isSending.collectAsState()
    val context = LocalContext.current
    
    LaunchedEffect(initialAddress) {
        if (initialAddress != null) {
            viewModel.setAddress(initialAddress)
        }
    }
    
    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("New Message") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("Cancel")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Recipient input with contact picker
            val contactPickerLauncher = rememberLauncherForActivityResult(
                contract = ActivityResultContracts.PickContact()
            ) { uri ->
                uri?.let {
                    try {
                        val cursor = context.contentResolver.query(
                            it,
                            arrayOf(ContactsContract.CommonDataKinds.Phone.NUMBER),
                            null,
                            null,
                            null
                        )
                        cursor?.use {
                            if (it.moveToFirst()) {
                                val phoneIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                                if (phoneIndex >= 0) {
                                    val phoneNumber = it.getString(phoneIndex)
                                    viewModel.setAddress(phoneNumber ?: "")
                                }
                            }
                        }
                    } catch (e: Exception) {
                        // Fallback: try to get phone number from contact ID
                        val contactId = ContactsContract.Contacts.getLookupUri(context.contentResolver, it)?.lastPathSegment
                        contactId?.let { id ->
                            val phoneCursor = context.contentResolver.query(
                                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                                arrayOf(ContactsContract.CommonDataKinds.Phone.NUMBER),
                                "${ContactsContract.CommonDataKinds.Phone.CONTACT_ID} = ?",
                                arrayOf(id),
                                null
                            )
                            phoneCursor?.use {
                                if (it.moveToFirst()) {
                                    val phoneIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                                    if (phoneIndex >= 0) {
                                        val phoneNumber = it.getString(phoneIndex)
                                        viewModel.setAddress(phoneNumber ?: "")
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = address,
                    onValueChange = { viewModel.setAddress(it) },
                    label = { Text("To") },
                    placeholder = { Text("Phone number") },
                    modifier = Modifier.weight(1f),
                    singleLine = true
                )
                IconButton(
                    onClick = { contactPickerLauncher.launch(null) }
                ) {
                    Icon(
                        imageVector = Icons.Default.Contacts,
                        contentDescription = "Pick Contact"
                    )
                }
            }
            
            // Message input
            OutlinedTextField(
                value = message,
                onValueChange = { viewModel.setMessage(it) },
                label = { Text("Message") },
                placeholder = { Text("Type your message...") },
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                maxLines = 10
            )
            
            // Character count
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${viewModel.getCharacterCount()} characters",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                if (viewModel.getMessageCount() > 1) {
                    Text(
                        text = "${viewModel.getMessageCount()} messages",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            
            // Send button
            Button(
                onClick = {
                    viewModel.sendMessage(context) {
                        onMessageSent()
                    }
                },
                enabled = address.isNotBlank() && message.isNotBlank() && !isSending,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isSending) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                }
                Text("Send")
            }
        }
    }
}


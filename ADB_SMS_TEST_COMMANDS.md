# ADB Commands for Sending SMS Messages

## Prerequisites
1. Enable USB debugging on your Android device/emulator
2. Connect device via USB or ensure emulator is running
3. Verify connection: `adb devices`

## ADB Command to Simulate Incoming SMS (Send SMS TO Device/Emulator)

### ⭐ BEST METHOD: Emulator Console (Recommended for Emulators)

**This is the most reliable method for Android emulators - it properly formats SMS with PDUs!**

1. **Find your emulator port:**
   - Check the emulator window title (usually shows "emulator-5554" or similar)
   - Or run: `adb devices` and look for "emulator-XXXX"
   - Default is usually 5554

2. **Connect to emulator console:**

   **PowerShell/Windows (Option 1 - Enable Telnet):**
   ```powershell
   # First, enable telnet (run PowerShell as Administrator):
   Enable-WindowsOptionalFeature -Online -FeatureName TelnetClient

   # Then connect:
   telnet localhost 5554
   ```

   **PowerShell/Windows (Option 2 - Use adb shell with echo):**
   ```powershell
   # Alternative: Use adb to send commands to emulator console
   # This sends the SMS command directly without needing telnet
   adb -s emulator-5554 emu sms send +1234567890 "Your message here"
   ```

   **Bash/Linux/Mac:**
   ```bash
   telnet localhost 5554
   ```

   **Note:** The `adb emu sms send` method (Option 2) is easier and doesn't require telnet!

3. **Send SMS using console:**
   ```
   sms send PHONE_NUMBER "MESSAGE_TEXT"
   ```

**Note:** This method works perfectly because it uses the emulator's built-in SMS simulation which properly formats PDUs that your app can parse. The broadcast method doesn't format PDUs correctly, so your receiver's `getMessagesFromIntent()` returns empty.

### Alternative: Broadcast Method (May have parsing issues)

**This method may not work properly because it doesn't format SMS PDUs correctly. Use emulator console above instead.**

### For Android 8.0+ (Oreo and above) - RECOMMENDED

**PowerShell (use single quotes):**
```powershell
adb shell am broadcast -a android.provider.Telephony.SMS_DELIVER_ACTION --es sms_body 'MESSAGE_TEXT' --es sender 'PHONE_NUMBER'
```

**Bash/Linux/Mac (use double quotes):**
```bash
adb shell am broadcast -a android.provider.Telephony.SMS_DELIVER_ACTION --es sms_body "MESSAGE_TEXT" --es sender "PHONE_NUMBER"
```

**This command simulates an incoming SMS message TO your device/emulator. Your app will receive it as if it came from the phone number you specify.**

### ⚠️ Service Call Method (NOT RECOMMENDED for your use case)
**Note:** This method actually sends SMS FROM the device (not TO it), and has issues with PowerShell. Use the broadcast method above instead.

The service call method is only useful if you want to actually send SMS from the device to another phone number. For testing your classifier by simulating incoming messages, always use the broadcast method.

### Other Broadcast Methods (if SMS_DELIVER_ACTION doesn't work)

**Older method:**
```bash
adb shell am broadcast -a android.provider.Telephony.SMS_RECEIVED --es sms_body "MESSAGE_TEXT" --es sender "PHONE_NUMBER"
```

**With additional flag:**
```bash
adb shell am broadcast -a android.provider.Telephony.SMS_RECEIVED --es sms_body "MESSAGE_TEXT" --es sender "PHONE_NUMBER" --ez isSms true
```

## Test Messages

### ⭐ Method 1: ADB Emulator Command (EASIEST - No Telnet Needed!)

**This is the simplest method - works directly with adb!**

**1. Phishing Message:**
```powershell
adb -s emulator-5554 emu sms send +1234567890 "URGENT: Your account has been suspended due to suspicious activity. Verify your identity immediately at: https://secure-bank-verify.com/login or your account will be permanently closed. Click here: bit.ly/verify-now"
```

**2. OTP for Delivery Message:**
```powershell
adb -s emulator-5554 emu sms send +1987654321 "Your OTP for delivery #12345 is 847392. Valid for 10 minutes. Do not share this code with anyone. - Amazon"
```

**Note:** Replace `emulator-5554` with your emulator name from `adb devices` output.

### Method 2: Telnet Console (Alternative)

**Step 1: Enable telnet (PowerShell as Administrator):**
```powershell
Enable-WindowsOptionalFeature -Online -FeatureName TelnetClient
```

**Step 2: Connect to emulator console**
```bash
telnet localhost 5554
```

**Step 3: Send messages**
```
sms send +1234567890 "URGENT: Your account has been suspended due to suspicious activity. Verify your identity immediately at: https://secure-bank-verify.com/login or your account will be permanently closed. Click here: bit.ly/verify-now"

sms send +1987654321 "Your OTP for delivery #12345 is 847392. Valid for 10 minutes. Do not share this code with anyone. - Amazon"
```

**To exit telnet:** Type `quit` or press `Ctrl+]` then `quit`

### Method 2: Broadcast (May not work - PDUs not properly formatted)

**Note:** These commands may not work because they don't format SMS PDUs correctly. Your receiver uses `getMessagesFromIntent()` which expects proper PDUs.

**PowerShell:**
```powershell
adb shell am broadcast -a android.provider.Telephony.SMS_DELIVER_ACTION --es sms_body 'MESSAGE' --es sender 'PHONE'
```

**Bash:**
```bash
adb shell am broadcast -a android.provider.Telephony.SMS_DELIVER_ACTION --es sms_body "MESSAGE" --es sender "PHONE"
```

## Alternative: Using am start (for testing SMS sending UI)
```bash
# Open SMS compose with pre-filled message
adb shell am start -a android.intent.action.SENDTO -d sms:+1234567890 --es sms_body "Your message here"
```

## Quick Test Commands

### Method 1: ADB Direct (EASIEST - Recommended!)

**PowerShell:**
```powershell
# Phishing message
adb -s emulator-5554 emu sms send +1234567890 "URGENT: Your account has been suspended due to suspicious activity. Verify your identity immediately at: https://secure-bank-verify.com/login or your account will be permanently closed. Click here: bit.ly/verify-now"

# OTP message
adb -s emulator-5554 emu sms send +1987654321 "Your OTP for delivery #12345 is 847392. Valid for 10 minutes. Do not share this code with anyone. - Amazon"
```

### Method 2: Telnet Console (Alternative)

```bash
# Connect to emulator
telnet localhost 5554

# Then send messages one by one:
sms send +1234567890 "URGENT: Your account has been suspended due to suspicious activity. Verify your identity immediately at: https://secure-bank-verify.com/login or your account will be permanently closed. Click here: bit.ly/verify-now"

sms send +1987654321 "Your OTP for delivery #12345 is 847392. Valid for 10 minutes. Do not share this code with anyone. - Amazon"

# Exit when done
quit
```

## Troubleshooting

### PowerShell Quote Issues:
If you see errors like `pkg=Your` or parsing issues, use **single quotes** (`'`) instead of double quotes (`"`) in PowerShell:
```powershell
# PowerShell - use single quotes
adb shell am broadcast -a android.provider.Telephony.SMS_DELIVER_ACTION --es sms_body 'MESSAGE_TEXT' --es sender 'PHONE_NUMBER'
```

### If SMS_DELIVER_ACTION doesn't work:
Try the older SMS_RECEIVED action:

**PowerShell:**
```powershell
adb shell am broadcast -a android.provider.Telephony.SMS_RECEIVED --es sms_body 'MESSAGE_TEXT' --es sender 'PHONE_NUMBER'
```

**Bash:**
```bash
adb shell am broadcast -a android.provider.Telephony.SMS_RECEIVED --es sms_body "MESSAGE_TEXT" --es sender "PHONE_NUMBER"
```

### For Emulator Testing:
Emulators may require additional setup. Ensure your emulator has telephony support enabled.

### Check if message was received:
```bash
# Check logs
adb logcat | grep -i sms

# Or check your app's database/logs
```

## Notes
- **The broadcast method simulates incoming SMS messages TO your device/emulator** - this is what you want for testing!
- Phone numbers can be any format (with or without +, with or without country code)
- The sender number is just metadata - it simulates the message coming from that number
- These commands make your device/emulator receive an SMS as if it came from the specified phone number
- Make sure your app is set as the default SMS handler or has SMS receive permissions
- The service call method sends SMS FROM the device (not what you want for testing)

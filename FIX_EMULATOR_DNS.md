# Fix Android Emulator DNS for Cloud Run

## Problem
The Android emulator cannot resolve the Cloud Run hostname (`sms-ensemble-hhpimusmbq-el.a.run.app`), resulting in:
```
Unable to resolve host "sms-ensemble-hhpimusmbq-el.a.run.app": No address associated with hostname
```

## Solution: Configure DNS on Emulator

### Option 1: Set DNS via ADB (Recommended)

Run these commands in your terminal (with the emulator running):

```bash
# Set Google DNS servers
adb shell "settings put global private_dns_mode off"
adb shell "setprop net.dns1 8.8.8.8"
adb shell "setprop net.dns2 8.8.4.4"
```

**Note:** These settings are temporary and will reset when the emulator restarts.

### Option 2: Configure Emulator DNS at Startup

1. Open **Android Studio**
2. Go to **Tools → Device Manager**
3. Click the **▼** (dropdown) next to your emulator
4. Select **Cold Boot Now** (to restart)
5. Or edit the emulator's **Advanced Settings**:
   - Click **Edit** (pencil icon) next to your emulator
   - Go to **Show Advanced Settings**
   - Under **Network**, ensure DNS is set to automatic or use `8.8.8.8,8.8.4.4`

### Option 3: Test DNS Resolution

After setting DNS, test if it works:

```bash
adb shell "ping -c 1 8.8.8.8"  # Test connectivity
adb shell "nslookup sms-ensemble-hhpimusmbq-el.a.run.app"  # Test DNS resolution
```

### Option 4: Use IP Address (Not Recommended)

If DNS continues to fail, you can temporarily use the Cloud Run service's IP address, but this is not recommended as Cloud Run IPs can change.

## Verify Fix

After configuring DNS:

1. **Rebuild and reinstall the app**
2. **Send a test SMS**
3. **Check logcat** - you should see:
   - ✅ "Making request to https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify"
   - ✅ Classification results (no more "Unable to resolve host" errors)

## Alternative: Use Physical Device

If the emulator DNS issues persist, test on a **physical Android device** connected via USB. Physical devices typically have proper DNS configuration and can reach Cloud Run services without issues.


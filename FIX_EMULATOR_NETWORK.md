# Fix Android Emulator Network Connectivity

## Problem
The Android emulator cannot access the internet, resulting in DNS resolution failures when trying to reach Cloud Run.

## Solution: Restart Emulator with Network Access

### Step 1: Close the Emulator
1. In Android Studio, click the **▼** dropdown next to your emulator
2. Select **Stop** or **Cold Boot Now**

### Step 2: Configure Network Settings
1. In **Device Manager**, click **Edit** (pencil icon) next to your emulator
2. Click **Show Advanced Settings**
3. Under **Network**, ensure:
   - **Connection** is set to **Automatic** or **NAT**
   - DNS is set to automatic

### Step 3: Restart Emulator
1. Click **▶ Start** to launch the emulator
2. Wait for it to fully boot

### Step 4: Verify Network
Run this command to test connectivity:
```bash
adb shell "ping -c 1 8.8.8.8"
```

You should see packets received. If not, try:
- **Cold Boot** the emulator (Tools → Device Manager → ▼ → Cold Boot Now)
- Check your host machine's internet connection
- Try a different emulator image

## Alternative: Use Physical Device

Physical Android devices typically have proper network configuration:

1. **Enable USB Debugging** on your phone
2. **Connect via USB**
3. **Select your phone** in Android Studio's device dropdown
4. **Run the app** - it will use the phone's network connection

## Temporary Workaround: Use Local Backend

If emulator network issues persist, temporarily switch back to local backend for testing:

1. Update `android_sms_classifier/app/build.gradle.kts`:
   ```kotlin
   buildConfigField(
       "String",
       "SERVER_API_BASE_URL",
       "\"http://10.0.2.2:8001/api\""
   )
   ```

2. Start local backend:
   ```bash
   python -m uvicorn backend.scripts.android_backend_server:app --host 0.0.0.0 --port 8001
   ```

3. Rebuild and test the app


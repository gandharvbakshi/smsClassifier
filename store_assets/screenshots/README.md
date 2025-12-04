# Screenshots for Google Play Store

## Requirements

- **Minimum:** 2 screenshots
- **Maximum:** 8 screenshots
- **Aspect Ratio:** 16:9 or 9:16
- **Size:** 
  - Minimum: 320px (shortest side)
  - Maximum: 3840px (longest side)
- **Format:** PNG or JPEG

## Recommended Screenshots (in order)

### 1. Main Inbox Screen
- Shows the message list with different classifications
- Displays OTP, Phishing, and General messages
- Shows the filter tabs at the top

### 2. OTP Detection & Copy
- Shows an OTP message
- Highlights the "Copy OTP" button
- Shows the OTP badge and sensitivity badge

### 3. Phishing Warning
- Shows a phishing message
- Displays the phishing warning badge
- Shows the risk indicators

### 4. Message Detail Screen
- Shows detailed view of a message
- Displays all badges (risk + sensitivity)
- Shows classification reasons
- Shows the "Copy OTP" button if applicable

### 5. Settings/Features Screen
- Shows app settings
- Highlights key features
- Shows classification options

## How to Take Screenshots

### From Android Device/Emulator:

1. **Using Android Studio:**
   - Open your app in the emulator
   - Navigate to the screen you want
   - Click the camera icon in the emulator toolbar
   - Or use: `adb shell screencap -p /sdcard/screenshot.png`
   - Pull the file: `adb pull /sdcard/screenshot.png`

2. **Using ADB:**
   ```bash
   adb shell screencap -p /sdcard/screenshot-01.png
   adb pull /sdcard/screenshot-01.png screenshots/
   ```

3. **From Physical Device:**
   - Use the device's screenshot feature
   - Transfer to computer
   - Crop and resize if needed

### Editing Screenshots:

1. **Crop to proper aspect ratio** (16:9 or 9:16)
2. **Resize if needed** (keep high resolution)
3. **Add captions/text overlays** (optional):
   - Highlight key features
   - Add brief descriptions
   - Use consistent styling

## File Naming

Name your screenshots:
- `screenshot-01-inbox.png`
- `screenshot-02-otp-detection.png`
- `screenshot-03-phishing-warning.png`
- `screenshot-04-detail-screen.png`
- `screenshot-05-settings.png`

## Screenshot Tips

- ✅ Use actual app screens (not mockups)
- ✅ Show the most important features first
- ✅ Ensure text is readable
- ✅ Use consistent styling
- ✅ Add captions to highlight features (optional)
- ❌ Don't use device frames (Google adds them automatically)
- ❌ Don't use placeholder text
- ❌ Don't show personal/sensitive information

## Tools for Editing

- **Canva** - Add text overlays and captions
- **Figma** - Design and edit screenshots
- **GIMP/Photoshop** - Professional editing
- **Snapseed** - Mobile editing app

## Checklist

- [ ] At least 2 screenshots taken
- [ ] All screenshots are proper aspect ratio (16:9 or 9:16)
- [ ] All screenshots show actual app functionality
- [ ] Text is readable in all screenshots
- [ ] No sensitive/personal information visible
- [ ] Screenshots are optimized (not too large)
- [ ] Screenshots are in correct format (PNG/JPEG)


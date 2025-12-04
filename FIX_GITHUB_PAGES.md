# Fix GitHub Pages - Privacy Policy Not Loading

## Problem
File exists at: `https://github.com/gandharvbakshi/smsClassifier/blob/main/privacy-policy.html`
But not accessible at: `https://gandharvbakshi.github.io/smsClassifier/privacy-policy.html`

## Solution Steps

### Step 1: Enable GitHub Pages

1. Go to: `https://github.com/gandharvbakshi/smsClassifier/settings/pages`
2. Under **"Source"**, select:
   - **Branch:** `main`
   - **Folder:** `/ (root)`
3. Click **"Save"**
4. Wait 1-2 minutes for GitHub to build the site

### Step 2: Check GitHub Pages Status

After enabling, you should see:
- A green checkmark or "Your site is live at..."
- The URL: `https://gandharvbakshi.github.io/smsClassifier/`

### Step 3: Access Your Privacy Policy

Once GitHub Pages is enabled, your privacy policy will be at:
```
https://gandharvbakshi.github.io/smsClassifier/privacy-policy.html
```

## Alternative: Use Raw GitHub URL (Temporary)

If GitHub Pages takes time to set up, you can temporarily use the raw GitHub URL:

```
https://raw.githubusercontent.com/gandharvbakshi/smsClassifier/main/privacy-policy.html
```

**Note:** This shows the raw HTML code, not a rendered page. Google Play may accept it, but a properly rendered page is better.

## Troubleshooting

### Still not working after enabling Pages?

1. **Check the branch:**
   - Make sure `privacy-policy.html` is in the `main` branch
   - Verify it's at the root of the repo (not in a subfolder)

2. **Wait a few minutes:**
   - GitHub Pages can take 1-5 minutes to build
   - Check the "Actions" tab in your repo to see if Pages is building

3. **Check file location:**
   - The file should be at: `smsClassifier/privacy-policy.html` (root level)
   - NOT at: `smsClassifier/android_sms_classifier/privacy-policy.html`

4. **Clear browser cache:**
   - Try accessing in incognito/private mode
   - Or add `?v=1` to the URL: `https://gandharvbakshi.github.io/smsClassifier/privacy-policy.html?v=1`

5. **Check GitHub Pages settings:**
   - Go to Settings → Pages
   - Make sure it shows "Your site is published at..."

## Quick Check Commands

If you want to verify the file is in the right place:

```bash
cd android_sms_classifier  # or wherever your repo root is
ls -la privacy-policy.html  # Should show the file
git status                  # Should show if it's committed
```

## Expected Result

After enabling GitHub Pages, when you visit:
```
https://gandharvbakshi.github.io/smsClassifier/privacy-policy.html
```

You should see a nicely formatted privacy policy page (not raw HTML code).


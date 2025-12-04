# Setting Up GitHub Pages for Privacy Policy

This guide will help you host your privacy policy on GitHub Pages for free.

## Step 1: Files Ready

The privacy policy files are already in this repository:
- `privacy-policy.html` - HTML version (recommended for GitHub Pages)
- `PRIVACY_POLICY.md` - Markdown version (alternative)

## Step 2: Enable GitHub Pages

### Using GitHub Web Interface (Easiest)

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Scroll down to **Pages** (left sidebar)
4. Under **Source**, select:
   - **Branch:** `main` (or `master`)
   - **Folder:** `/ (root)`
5. Click **Save**
6. GitHub will provide you with a URL like:
   ```
   https://yourusername.github.io/repo-name/
   ```

### Using a Dedicated Branch (Alternative)

1. Create a new branch called `gh-pages`:
   ```bash
   git checkout -b gh-pages
   ```
2. Copy `privacy-policy.html` to this branch
3. Push the branch:
   ```bash
   git push origin gh-pages
   ```
4. In GitHub Settings → Pages, select `gh-pages` branch

## Step 3: Get Your Privacy Policy URL

After enabling GitHub Pages, your privacy policy will be available at:

**If using root directory:**
```
https://yourusername.github.io/repo-name/privacy-policy.html
```

**If using `/docs` folder:**
```
https://yourusername.github.io/repo-name/privacy-policy.html
```

## Step 4: Test the URL

1. Open the URL in your browser
2. Make sure it's accessible (not private/restricted)
3. Verify it loads correctly
4. Check that it's HTTPS (GitHub Pages automatically provides HTTPS)

## Step 5: Add to Google Play Console

1. Go to Google Play Console → Your App
2. Navigate to **App Content → Privacy Policy**
3. Enter your GitHub Pages URL:
   ```
   https://yourusername.github.io/repo-name/privacy-policy.html
   ```
4. Click **Save**

## Quick Setup Commands

```bash
# 1. Files are already in the repo, just commit and push
cd android_sms_classifier
git add privacy-policy.html PRIVACY_POLICY.md
git commit -m "Add privacy policy for Google Play"
git push origin main

# 2. Enable GitHub Pages via web interface (Settings → Pages)
```

## Troubleshooting

### URL not working?
- Wait a few minutes after enabling Pages (GitHub needs to build the site)
- Check that the file is in the correct branch
- Verify the file name matches the URL

### Markdown not rendering?
- GitHub automatically renders `.md` files
- For better formatting, use `.html` instead (recommended)
- Make sure the file is in the root or `/docs` folder

### HTTPS not working?
- GitHub Pages automatically provides HTTPS
- It may take a few minutes to activate
- Make sure you're using the `github.io` domain (not custom domain without SSL)

## Alternative: Use GitHub's Raw Content

If you just want a simple Markdown file accessible via HTTPS:

1. Upload `PRIVACY_POLICY.md` to your repo
2. Use the raw GitHub URL:
   ```
   https://raw.githubusercontent.com/yourusername/repo-name/main/PRIVACY_POLICY.md
   ```

However, **GitHub Pages is recommended** as it provides a proper web page with better formatting.

## Next Steps

1. ✅ Files are in the repo (`privacy-policy.html`)
2. ✅ Commit and push to GitHub
3. ✅ Enable GitHub Pages (Settings → Pages)
4. ✅ Get your URL
5. ✅ Add URL to Google Play Console
6. ✅ Test that it's accessible

Your privacy policy URL should look like:
```
https://yourusername.github.io/repo-name/privacy-policy.html
```

Replace `yourusername` and `repo-name` with your actual GitHub username and repository name.


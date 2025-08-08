# 🔗 Google Drive OAuth Setup Guide

## 🚀 Quick Start (Direct OAuth)

The Income Tax AI Assistant now supports **direct OAuth authentication** with Google Drive, eliminating the need for manual credential management!

### 📋 Prerequisites

1. **Google Account** with access to Google Drive
2. **Google Cloud Project** (free tier available)
3. **Internet connection** for OAuth flow

### 🔧 Step-by-Step Setup

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `Income Tax AI Assistant`
4. Click **"Create"**

#### 2. Enable Google Drive API

1. In your project, go to **APIs & Services > Library**
2. Search for **"Google Drive API"**
3. Click on it and press **"Enable"**

#### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Choose **"External"** user type
3. Fill in required information:
   - **App name**: `Income Tax AI Assistant`
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Click **"Save and Continue"**
5. On **Scopes** page, click **"Add or Remove Scopes"**
6. Search for and select: `https://www.googleapis.com/auth/drive.readonly`
7. Click **"Update"** → **"Save and Continue"**
8. On **Test users** page, click **"Add Users"**
9. Add your Google account email
10. Click **"Save and Continue"**

#### 4. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **"Create Credentials"** → **"OAuth 2.0 Client IDs"**
3. Choose **"Web application"** as application type
4. Set **Name**: `Income Tax AI Assistant Web Client`
5. Add **Authorized redirect URIs**:
   ```
   http://localhost:8501/oauth2callback
   ```
6. Click **"Create"**
7. **Download the JSON file** (this is your `credentials.json`)

#### 5. Set Up in the App

1. **Place the downloaded JSON file** in your project root directory
2. **Rename it to `credentials.json`**
3. **Start the Streamlit app**:
   ```bash
   streamlit run src/ui/streamlit_app.py
   ```
4. **Go to "🔗 Google Drive Setup" tab**
5. **Click "🔗 Authenticate with Google"**
6. **Follow the OAuth flow** in your browser
7. **Grant permissions** when prompted

### 🎉 You're Done!

Once authenticated, you can:
- **Test the connection** using the provided buttons
- **View your Google Drive folders**
- **Use Google Drive integration** in Document Analysis
- **Fetch and analyze documents** directly from Google Drive

## 🔄 OAuth Flow Process

### What Happens During Authentication:

1. **Click "Authenticate with Google"** → Opens Google's authorization page
2. **Sign in with your Google account** → Google shows permissions
3. **Grant access** → Google redirects back to the app
4. **Automatic token exchange** → App gets access tokens
5. **Authentication complete** → Ready to use Google Drive!

### 🔒 Security Features

- **Read-only access** to Google Drive files
- **OAuth 2.0** with proper scopes
- **Automatic token refresh**
- **Secure credential storage**
- **No password sharing**

## 🛠️ Troubleshooting

### Common Issues:

#### "Invalid redirect URI"
- Ensure you added `http://localhost:8501/oauth2callback` in Google Cloud Console
- Check that the URI matches exactly (no extra spaces)

#### "Access denied"
- Make sure you added your email as a test user
- Check that you're using the same Google account

#### "Credentials not found"
- Ensure `credentials.json` is in the project root directory
- Check that the file is named exactly `credentials.json`

#### "Authentication failed"
- Try refreshing the page and starting the flow again
- Check your internet connection
- Ensure Google Drive API is enabled

### 🔧 Manual Fallback

If the automatic OAuth flow doesn't work:

1. **Click the authorization link** in the app
2. **Copy the authorization code** from the redirect URL
3. **Paste it manually** in the app
4. **Click "Complete Authentication"**

## 📞 Support

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Verify your Google Cloud setup** matches the guide
3. **Ensure all prerequisites** are met
4. **Try the manual fallback** method

## 🎯 Next Steps

After successful authentication:

1. **Go to Document Analysis tab**
2. **Paste your Google Drive folder URL**
3. **Click "Analyze All Documents with AI"**
4. **Enjoy seamless document analysis!**

---

**🎉 Congratulations! You now have direct Google Drive integration with OAuth authentication!** 
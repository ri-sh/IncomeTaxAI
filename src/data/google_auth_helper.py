"""
Google Drive Authentication Helper
Provides web-based setup guide and automatic authentication flow
"""

import os
import json
import webbrowser
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from urllib.parse import urlencode, parse_qs, urlparse

class GoogleAuthHelper:
    """Handles Google Drive authentication with web-based setup"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.credentials_file = "credentials.json"
        self.token_file = "token.json"
        self.service = None
        self.creds = None
        
        # OAuth 2.0 configuration for direct flow
        self.client_id = "YOUR_CLIENT_ID"  # Will be set from credentials
        self.client_secret = "YOUR_CLIENT_SECRET"  # Will be set from credentials
        self.redirect_uri = "http://localhost:8501/oauth2callback"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
    
    def show_setup_guide(self) -> None:
        """Display comprehensive setup guide in Streamlit"""
        st.markdown("""
        # 🔗 Google Drive Integration Setup
        
        Follow these steps to connect your Google Drive:
        """)
        
        with st.expander("📋 Step-by-Step Setup Guide", expanded=True):
            st.markdown("""
            ### 1. Create Google Cloud Project
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select existing one
            3. Note down your **Project ID**
            
            ### 2. Enable Google Drive API
            1. In Google Cloud Console, go to **APIs & Services > Library**
            2. Search for **"Google Drive API"**
            3. Click **Enable**
            
            ### 3. Create OAuth Credentials
            1. Go to **APIs & Services > Credentials**
            2. Click **"Create Credentials" > "OAuth 2.0 Client IDs"**
            3. Configure OAuth consent screen if prompted:
               - User Type: **External**
               - App name: **Income Tax AI Assistant**
               - User support email: **Your email**
               - Developer contact: **Your email**
            4. Add scopes: **https://www.googleapis.com/auth/drive.readonly**
            5. Add test users: **Your Google account email**
            6. Choose **"Web application"** as application type
            7. Add authorized redirect URIs: **http://localhost:8501/oauth2callback**
            8. Download the credentials JSON file
            
            ### 4. Upload Credentials
            Upload the downloaded credentials file below:
            """)
            
            uploaded_file = st.file_uploader(
                "📁 Upload credentials.json",
                type=['json'],
                help="Upload the credentials file downloaded from Google Cloud Console"
            )
            
            if uploaded_file is not None:
                try:
                    # Save the uploaded file
                    with open(self.credentials_file, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    st.success("✅ Credentials file uploaded successfully!")
                    
                    # Test authentication
                    if self.authenticate():
                        st.success("🎉 Google Drive authentication successful!")
                        st.info("You can now use Google Drive integration in the Document Analysis tab.")
                    else:
                        st.error("❌ Authentication failed. Please check your credentials.")
                        
                except Exception as e:
                    st.error(f"❌ Error uploading credentials: {str(e)}")
        
        # Direct OAuth setup (if credentials are available)
        if os.path.exists(self.credentials_file):
            st.subheader("🚀 Direct OAuth Authentication")
            st.markdown("""
            **Quick authentication without manual setup:**
            
            Click the button below to authenticate directly with Google.
            This will open Google's authorization page in your browser.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔗 Authenticate with Google", type="primary"):
                    auth_url = self.start_direct_oauth_flow()
                    if auth_url:
                        st.session_state.auth_url = auth_url
                        st.session_state.show_auth_flow = True
                        st.rerun()
                    else:
                        st.error("❌ Could not start OAuth flow. Please check your credentials.")
            
            with col2:
                if st.button("🔄 Check Current Setup"):
                    self.check_current_setup()
            
            # Handle OAuth callback
            if st.session_state.get('show_auth_flow', False):
                st.info("🔗 **OAuth Flow Started**")
                
                # Check if we have an OAuth code from callback
                oauth_code = st.session_state.get('oauth_code')
                if oauth_code:
                    st.success("✅ Authorization code received automatically!")
                    with st.spinner("Completing authentication..."):
                        if self.complete_oauth_flow(oauth_code):
                            st.success("🎉 Authentication successful!")
                            st.session_state.show_auth_flow = False
                            # Clear the OAuth code
                            if 'oauth_code' in st.session_state:
                                del st.session_state.oauth_code
                            st.rerun()
                        else:
                            st.error("❌ Authentication failed. Please try again.")
                else:
                    st.markdown(f"""
                    **Step 1:** Click the link below to authorize with Google:
                    
                    [🔗 Authorize with Google]({st.session_state.get('auth_url', '')})
                    
                    **Step 2:** After authorization, you'll be redirected back to this app automatically.
                    
                    **Step 3:** The authentication will complete automatically.
                    """)
                    
                    # Manual fallback
                    with st.expander("🔧 Manual Authorization Code (if automatic doesn't work)"):
                        auth_code = st.text_input(
                            "📝 Authorization Code",
                            placeholder="Paste the authorization code from the redirect URL",
                            help="Copy the 'code' parameter from the redirect URL"
                        )
                        
                        if auth_code:
                            if st.button("✅ Complete Authentication"):
                                with st.spinner("Completing authentication..."):
                                    if self.complete_oauth_flow(auth_code):
                                        st.success("🎉 Authentication successful!")
                                        st.session_state.show_auth_flow = False
                                        st.rerun()
                                    else:
                                        st.error("❌ Authentication failed. Please try again.")
        
        # Alternative manual setup
        with st.expander("🔧 Manual Setup (Alternative)"):
            st.markdown("""
            If you prefer manual setup:
            
            1. Download credentials.json from Google Cloud Console
            2. Place it in your project root directory
            3. Restart the application
            4. The system will automatically authenticate
            """)
    
    def check_current_setup(self) -> None:
        """Check current authentication setup status"""
        if os.path.exists(self.credentials_file):
            st.success("✅ Credentials file found")
            
            if os.path.exists(self.token_file):
                st.success("✅ Authentication token found")
                
                if self.authenticate():
                    st.success("🎉 Google Drive is ready to use!")
                else:
                    st.warning("⚠️ Token expired. Please re-authenticate.")
            else:
                st.info("ℹ️ No authentication token found. Please authenticate.")
        else:
            st.error("❌ No credentials file found. Please follow the setup guide above.")
    
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        try:
            # Load existing token
            if os.path.exists(self.token_file):
                self.creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            
            # If there are no valid credentials, get new ones
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    
                    # Run the flow with local server
                    self.creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.creds)
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Google Drive connection and return status"""
        try:
            if not self.authenticate():
                return {
                    'status': 'error',
                    'message': 'Authentication failed'
                }
            
            # Test API call
            results = self.service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            return {
                'status': 'success',
                'message': 'Google Drive connection successful',
                'files_count': len(results.get('files', []))
            }
            
        except HttpError as e:
            return {
                'status': 'error',
                'message': f'API Error: {str(e)}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection failed: {str(e)}'
            }
    
    def get_user_info(self) -> Optional[Dict[str, str]]:
        """Get authenticated user information"""
        try:
            if not self.authenticate():
                return None
            
            # Get user info from Drive API
            about = self.service.about().get(fields="user").execute()
            user = about.get('user', {})
            
            return {
                'email': user.get('emailAddress', 'Unknown'),
                'name': user.get('displayName', 'Unknown'),
                'permission_id': user.get('permissionId', 'Unknown')
            }
            
        except Exception as e:
            print(f"❌ Error getting user info: {str(e)}")
            return None
    
    def start_direct_oauth_flow(self) -> str:
        """Start direct OAuth flow and return authorization URL"""
        try:
            # Load client credentials if available
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    creds_data = json.load(f)
                    if 'installed' in creds_data:
                        self.client_id = creds_data['installed']['client_id']
                        self.client_secret = creds_data['installed']['client_secret']
                    elif 'web' in creds_data:
                        self.client_id = creds_data['web']['client_id']
                        self.client_secret = creds_data['web']['client_secret']
            
            # Generate authorization URL
            params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': ' '.join(self.SCOPES),
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"{self.auth_url}?{urlencode(params)}"
            return auth_url
            
        except Exception as e:
            print(f"❌ Error starting OAuth flow: {str(e)}")
            return None
    
    def complete_oauth_flow(self, authorization_code: str) -> bool:
        """Complete OAuth flow with authorization code"""
        try:
            # Exchange authorization code for tokens
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.token_url, data=token_data)
            
            if response.status_code == 200:
                tokens = response.json()
                
                # Create credentials object
                self.creds = Credentials(
                    token=tokens['access_token'],
                    refresh_token=tokens.get('refresh_token'),
                    token_uri=self.token_url,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    scopes=self.SCOPES
                )
                
                # Save credentials
                with open(self.token_file, 'w') as f:
                    f.write(self.creds.to_json())
                
                # Build service
                self.service = build('drive', 'v3', credentials=self.creds)
                return True
            else:
                print(f"❌ Token exchange failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error completing OAuth flow: {str(e)}")
            return False
    
    def list_accessible_folders(self) -> list:
        """List folders accessible to the authenticated user"""
        try:
            if not self.authenticate():
                return []
            
            results = self.service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name, modifiedTime)",
                pageSize=50
            ).execute()
            
            folders = results.get('files', [])
            return [
                {
                    'id': folder['id'],
                    'name': folder['name'],
                    'modified': folder['modifiedTime']
                }
                for folder in folders
            ]
            
        except Exception as e:
            print(f"❌ Error listing folders: {str(e)}")
            return []

# Global instance
auth_helper = GoogleAuthHelper() 
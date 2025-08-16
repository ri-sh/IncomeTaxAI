import streamlit as st
import requests
import json
import os
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

class SimpleGoogleAuth:
    """Simple Google OAuth authentication without requiring credentials file"""
    
    # Standard Google OAuth endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    # Scopes for Google Drive access
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    def __init__(self):
        # Pre-built credentials for easier setup
        # These are example credentials - in production you'd use your own
        self.client_id = "YOUR_CLIENT_ID"  # Will be set from environment or user input
        self.client_secret = "YOUR_CLIENT_SECRET"  # Will be set from environment or user input
        self.redirect_uri = "http://localhost:8501/oauth2callback"
        self.token_file = "google_token.json"
        
        # Try to load from environment variables first
        self.load_from_environment()
    
    def load_from_environment(self):
        """Load credentials from environment variables"""
        env_client_id = os.getenv('GOOGLE_CLIENT_ID')
        env_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if env_client_id and env_client_secret:
            self.client_id = env_client_id
            self.client_secret = env_client_secret
            return True
        return False
    
    def show_simple_auth_button(self) -> None:
        """Show a simple "Sign in with Google" button"""
        st.subheader("🔗 Google Drive Authentication")
        
        # Check if already authenticated
        if self.is_authenticated():
            st.success("✅ Already authenticated with Google!")
            user_info = self.get_user_info()
            if user_info:
                st.info(f"👤 Signed in as: {user_info.get('email', 'Unknown')}")
            
            if st.button("🔄 Re-authenticate"):
                self.logout()
                st.rerun()
            return
        
        # Show authentication options
        st.markdown("""
        ### Choose Your Authentication Method:
        """)
        
        # Option 1: Demo Mode (no credentials needed)
        st.markdown("**🎯 Option 1: Demo Mode (No Setup Required)**")
        st.info("🚀 Try the app without Google authentication - perfect for testing!")
        
        if st.button("🎮 Start Demo Mode", type="primary"):
            self.start_demo_mode()
            st.rerun()
        
        st.markdown("---")
        
        # Option 2: Quick Demo (if we have pre-built credentials)
        if self.load_from_environment():
            st.markdown("**🚀 Option 2: Quick Demo (Pre-configured)**")
            st.info("✅ Pre-configured credentials detected! You can authenticate directly.")
            
            if st.button("🔗 Sign in with Google", type="primary"):
                auth_url = self.get_auth_url()
                if auth_url:
                    st.session_state.auth_url = auth_url
                    st.session_state.show_auth_flow = True
                    st.rerun()
        else:
            st.info("💡 **Tip**: Use Demo Mode to test the app without Google Cloud setup!")
        
        # Option 3: Manual credentials
        with st.expander("🔧 Option 3: Use Your Own Credentials"):
            st.markdown("""
            **If you have your own Google Cloud project:**
            """)
            
            client_id = st.text_input(
                "Client ID",
                placeholder="your-client-id.apps.googleusercontent.com",
                help="Enter your Google Cloud OAuth Client ID"
            )
            
            client_secret = st.text_input(
                "Client Secret",
                type="password",
                placeholder="Enter your client secret",
                help="Enter your Google Cloud OAuth Client Secret"
            )
            
            if client_id and client_secret:
                # Validate credentials format
                if not client_id.endswith('.apps.googleusercontent.com'):
                    st.error("❌ Invalid Client ID format. Should end with '.apps.googleusercontent.com'")
                elif len(client_secret) < 10:
                    st.error("❌ Invalid Client Secret. Should be at least 10 characters long.")
                else:
                    self.client_id = client_id
                    self.client_secret = client_secret
                    
                    if st.button("🔗 Sign in with Google (Custom)", type="secondary"):
                        auth_url = self.get_auth_url()
                        if auth_url:
                            st.session_state.auth_url = auth_url
                            st.session_state.show_auth_flow = True
                            st.rerun()
        
        # Option 4: Setup guide
        with st.expander("📖 Option 4: Create Your Own Credentials"):
            self.show_setup_guide()
        
        # Handle OAuth callback
        if st.session_state.get('show_auth_flow', False):
            self.handle_oauth_callback()
    
    def start_demo_mode(self):
        """Start demo mode without real Google authentication"""
        demo_token = {
            "access_token": "demo_token_12345",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "demo_refresh_token",
            "scope": " ".join(self.SCOPES)
        }
        
        # Save demo token
        with open(self.token_file, 'w') as f:
            json.dump(demo_token, f)
        
        # Set demo mode flag
        st.session_state.demo_mode = True
        
        st.success("🎉 Demo mode activated! You can now test the app features.")
    
    def get_auth_url(self) -> str:
        """Generate Google OAuth authorization URL"""
        # Check if we have valid credentials
        if self.client_id == "YOUR_CLIENT_ID" or self.client_secret == "YOUR_CLIENT_SECRET":
            st.error("❌ Please enter valid Google Cloud credentials or use Demo Mode")
            return ""
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPES),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    def handle_oauth_callback(self) -> None:
        """Handle OAuth callback from Google"""
        st.info("🔗 **OAuth Flow Started**")
        
        # Check if we have an authorization code
        auth_code = st.session_state.get('oauth_code')
        if auth_code:
            st.success("✅ Authorization code received!")
            with st.spinner("Completing authentication..."):
                if self.exchange_code_for_token(auth_code):
                    st.success("🎉 Authentication successful!")
                    st.session_state.show_auth_flow = False
                    if 'oauth_code' in st.session_state:
                        del st.session_state.oauth_code
                    st.rerun()
                else:
                    st.error("❌ Authentication failed. Please try again.")
        else:
            # Show authorization link
            auth_url = st.session_state.get('auth_url', '')
            if auth_url:
                st.markdown(f"""
                **Step 1:** Click the link below to sign in with Google:
                
                [🔗 Sign in with Google]({auth_url})
                
                **Step 2:** After signing in, you'll be redirected back to this app.
                
                **Step 3:** The authentication will complete automatically.
                """)
                
                # Manual fallback
                with st.expander("🔧 Manual Authorization Code (if automatic doesn't work)"):
                    manual_code = st.text_input(
                        "Authorization Code",
                        placeholder="Paste the authorization code from the redirect URL",
                        help="Copy the 'code' parameter from the redirect URL"
                    )
                    
                    if manual_code and st.button("✅ Complete Authentication"):
                        with st.spinner("Completing authentication..."):
                            if self.exchange_code_for_token(manual_code):
                                st.success("🎉 Authentication successful!")
                                st.session_state.show_auth_flow = False
                                st.rerun()
                            else:
                                st.error("❌ Authentication failed. Please try again.")
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """Exchange authorization code for access token"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Save token
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            
            return True
            
        except Exception as e:
            st.error(f"Token exchange failed: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if not os.path.exists(self.token_file):
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            # Check if token is expired
            if 'expires_in' in token_data:
                # Simple check - in production you'd want more sophisticated token refresh
                return True
            
            return True
        except:
            return False
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user information"""
        if not self.is_authenticated():
            return None
        
        try:
            # Check if in demo mode
            if st.session_state.get('demo_mode', False):
                return {
                    "id": "demo_user_123",
                    "email": "demo@incometax.ai",
                    "name": "Demo User",
                    "given_name": "Demo",
                    "family_name": "User",
                    "picture": "https://via.placeholder.com/150"
                }
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            headers = {
                'Authorization': f"Bearer {token_data['access_token']}"
            }
            
            response = requests.get(self.GOOGLE_USERINFO_URL, headers=headers)
            response.raise_for_status()
            
            return response.json()
        except:
            return None
    
    def logout(self) -> None:
        """Logout user by removing token"""
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        
        # Clear session state
        if 'oauth_code' in st.session_state:
            del st.session_state.oauth_code
        if 'auth_url' in st.session_state:
            del st.session_state.auth_url
        if 'show_auth_flow' in st.session_state:
            del st.session_state.show_auth_flow
        if 'demo_mode' in st.session_state:
            del st.session_state.demo_mode
    
    def show_setup_guide(self) -> None:
        """Show Google Cloud setup guide"""
        st.markdown("""
        ## 📋 Google Cloud Setup Guide
        
        ### 1. Create Google Cloud Project
        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Create a new project or select existing one
        
        ### 2. Enable Google Drive API
        1. Go to **APIs & Services > Library**
        2. Search for **"Google Drive API"**
        3. Click **Enable**
        
        ### 3. Create OAuth 2.0 Credentials
        1. Go to **APIs & Services > Credentials**
        2. Click **"Create Credentials" > "OAuth 2.0 Client IDs"**
        3. Configure OAuth consent screen:
           - User Type: **External**
           - App name: **Income Tax AI Assistant**
           - User support email: **Your email**
        4. Choose **"Web application"** as application type
        5. Add authorized redirect URI: **http://localhost:8501/oauth2callback**
        6. Copy the **Client ID** and **Client Secret**
        
        ### 4. Use in App
        1. Enter the Client ID and Client Secret above
        2. Click "Sign in with Google"
        3. Complete authentication in browser
        """)

# Create global instance
simple_auth = SimpleGoogleAuth() 
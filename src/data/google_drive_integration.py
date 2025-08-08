"""
Google Drive Integration for Income Tax Document Fetching
Allows users to fetch tax documents directly from Google Drive
"""

import os
import io
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import mimetypes
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

@dataclass
class DriveFile:
    """Represents a file in Google Drive"""
    id: str
    name: str
    mime_type: str
    size: Optional[int]
    modified_time: str
    parents: List[str]
    web_view_link: str

class GoogleDriveIntegration:
    """Handles Google Drive authentication and file operations"""
    
    # Scopes required for reading files from Google Drive
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Tax-related file patterns
    TAX_FILE_PATTERNS = [
        'form 16', 'form16', 'salary', 'tds',
        'bank statement', 'interest certificate',
        'lic', 'insurance', 'premium',
        'elss', 'mutual fund', 'sip',
        'ppf', 'epf', 'provident fund',
        'home loan', 'house loan', 'interest',
        'rent receipt', 'hra',
        'investment', 'tax saving',
        'donation', 'charitable',
        'medical', 'health insurance',
        'education loan', 'capital gains',
        'dividend', 'share', 'stock'
    ]
    
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.creds = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        try:
            # Try to use the auth helper first
            try:
                from .google_auth_helper import auth_helper
                if auth_helper.authenticate():
                    self.service = auth_helper.service
                    self.creds = auth_helper.creds
                    return True
            except ImportError:
                pass  # Fall back to original method
            
            # Load existing token
            if os.path.exists(self.token_file):
                self.creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            
            # If there are no valid credentials, get new ones
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print(f"❌ Google credentials file not found: {self.credentials_file}")
                        print("Please download credentials.json from Google Cloud Console")
                        print("Or use the Google Drive Setup tab in the application")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.creds)
            print("✅ Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            print(f"❌ Failed to authenticate with Google Drive: {str(e)}")
            return False
    
    @staticmethod
    def extract_folder_id_from_url(drive_url: str) -> Optional[str]:
        """Extract folder ID from Google Drive URL"""
        import re
        
        # Pattern to match Google Drive folder URLs
        patterns = [
            r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
            r"drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)",
            r"folders/([a-zA-Z0-9_-]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, drive_url)
            if match:
                return match.group(1)
        
        return None
    
    def connect_to_folder_by_url(self, drive_url: str) -> List[DriveFile]:
        """Connect to Google Drive folder using URL"""
        folder_id = self.extract_folder_id_from_url(drive_url)
        if not folder_id:
            print(f"❌ Could not extract folder ID from URL: {drive_url}")
            return []
        
        print(f"📁 Extracted folder ID: {folder_id}")
        return self.connect_to_folder_by_id(folder_id)
    
    def connect_to_folder_by_id(self, folder_id: str) -> List[DriveFile]:
        """Connect directly to a Google Drive folder by ID"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            print(f"🔗 Connecting to Google Drive folder: {folder_id}")
            
            # Get all files in the specified folder
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=50,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)"
            ).execute()
            
            files = []
            items = results.get('files', [])
            
            for item in items:
                drive_file = DriveFile(
                    id=item['id'],
                    name=item['name'],
                    mime_type=item.get('mimeType', ''),
                    size=int(item.get('size', 0)) if item.get('size') else None,
                    modified_time=item['modifiedTime'],
                    parents=item.get('parents', []),
                    web_view_link=item.get('webViewLink', '')
                )
                files.append(drive_file)
            
            print(f"✅ Found {len(files)} files in Google Drive folder")
            return files
            
        except Exception as e:
            print(f"❌ Error accessing Google Drive folder: {str(e)}")
            return []
    
    def search_tax_documents(self, folder_name: Optional[str] = None, 
                           year: str = "2024-2025") -> List[DriveFile]:
        """Search for tax-related documents in Google Drive"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            files = []
            
            # Build search query
            query_parts = []
            
            # Search in specific folder if provided
            if folder_name:
                folder_id = self._find_folder_id(folder_name)
                if folder_id:
                    query_parts.append(f"'{folder_id}' in parents")
            
            # Search for tax-related patterns
            pattern_queries = []
            for pattern in self.TAX_FILE_PATTERNS:
                pattern_queries.append(f"name contains '{pattern}'")
            
            # Add year-specific search
            year_patterns = [year, year.replace("-", ""), "2024", "2025", "FY24", "FY25"]
            for year_pattern in year_patterns:
                pattern_queries.append(f"name contains '{year_pattern}'")
            
            if pattern_queries:
                query_parts.append(f"({' or '.join(pattern_queries)})")
            
            # Only search for common document types
            file_type_query = ("mimeType='application/pdf' or "
                             "mimeType='application/vnd.ms-excel' or "
                             "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
                             "mimeType='image/jpeg' or "
                             "mimeType='image/png' or "
                             "mimeType='text/csv'")
            query_parts.append(f"({file_type_query})")
            
            # Exclude trashed files
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts)
            
            # Execute search
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)"
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                files.append(DriveFile(
                    id=item['id'],
                    name=item['name'],
                    mime_type=item['mimeType'],
                    size=int(item.get('size', 0)) if item.get('size') else None,
                    modified_time=item['modifiedTime'],
                    parents=item.get('parents', []),
                    web_view_link=item['webViewLink']
                ))
            
            print(f"✅ Found {len(files)} tax-related documents in Google Drive")
            return files
            
        except HttpError as e:
            print(f"❌ Error searching Google Drive: {str(e)}")
            return []
    
    def _find_folder_id(self, folder_name: str) -> Optional[str]:
        """Find folder ID by name"""
        try:
            results = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            return None
            
        except HttpError:
            return None
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Download a file from Google Drive to local storage"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            
            # Create local directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            print(f"✅ Downloaded: {file_metadata['name']} -> {local_path}")
            return True
            
        except HttpError as e:
            print(f"❌ Error downloading file {file_id}: {str(e)}")
            return False
    
    def batch_download_tax_documents(self, 
                                   download_folder: str = "./data/tax_documents/gdrive",
                                   folder_name: Optional[str] = None) -> List[str]:
        """Download all found tax documents to local folder"""
        files = self.search_tax_documents(folder_name)
        downloaded_files = []
        
        if not files:
            print("ℹ️  No tax documents found in Google Drive")
            return downloaded_files
        
        print(f"📥 Downloading {len(files)} files from Google Drive...")
        
        for file in files:
            # Create safe filename
            safe_filename = "".join(c for c in file.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            local_path = os.path.join(download_folder, safe_filename)
            
            # Avoid duplicate downloads
            if os.path.exists(local_path):
                print(f"⏭️  Skipping existing file: {safe_filename}")
                downloaded_files.append(local_path)
                continue
            
            if self.download_file(file.id, local_path):
                downloaded_files.append(local_path)
        
        print(f"✅ Downloaded {len(downloaded_files)} files successfully")
        return downloaded_files
    
    def get_folder_structure(self, folder_name: Optional[str] = None) -> Dict:
        """Get folder structure for tax documents"""
        if not self.service:
            if not self.authenticate():
                return {}
        
        try:
            folder_id = self._find_folder_id(folder_name) if folder_name else 'root'
            
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            
            structure = {
                'folders': [],
                'files': []
            }
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    structure['folders'].append({
                        'id': item['id'],
                        'name': item['name']
                    })
                else:
                    structure['files'].append({
                        'id': item['id'],
                        'name': item['name'],
                        'type': item['mimeType'],
                        'modified': item['modifiedTime']
                    })
            
            return structure
            
        except HttpError as e:
            print(f"❌ Error getting folder structure: {str(e)}")
            return {}
    
    def setup_google_drive_credentials(self) -> str:
        """Generate instructions for setting up Google Drive integration"""
        instructions = """
🔗 Google Drive Integration Setup Instructions:

1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API:
   - Go to APIs & Services > Library
   - Search for "Google Drive API"
   - Click Enable

4. Create credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Configure OAuth consent screen if prompted
   - Choose "Desktop application"
   - Download the credentials JSON file

5. Rename the downloaded file to 'credentials.json'
6. Place it in your project root directory

7. Run the application - it will open a browser for authentication
8. Grant permissions to access your Google Drive
9. The system will save your token for future use

📁 Recommended Google Drive folder structure:
   Income Tax 2024-2025/
   ├── Salary Documents/
   │   ├── Form 16
   │   └── Salary Slips/
   ├── Bank Documents/
   │   ├── Bank Statements/
   │   └── Interest Certificates/
   ├── Investments/
   │   ├── LIC/
   │   ├── ELSS/
   │   ├── PPF/
   │   └── EPF/
   ├── Insurance/
   │   ├── Health Insurance/
   │   └── Term Insurance/
   └── House Property/
       ├── Home Loan/
       └── Rent Receipts/
        """
        return instructions

# Example usage
if __name__ == "__main__":
    # Initialize Google Drive integration
    gdrive = GoogleDriveIntegration()
    
    # Check if credentials exist
    if not os.path.exists("credentials.json"):
        print(gdrive.setup_google_drive_credentials())
    else:
        # Search and download tax documents
        downloaded = gdrive.batch_download_tax_documents(
            folder_name="Income Tax 2024-2025"
        )
        print(f"Downloaded {len(downloaded)} files")
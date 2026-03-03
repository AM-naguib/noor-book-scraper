import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from rich.progress import Progress

from core.logger import logger
from core.config import DRIVE_ROOT_FOLDER_ID

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveClient:
    def __init__(self):
        self.root_folder_id = DRIVE_ROOT_FOLDER_ID
        self.creds = None
        self.service = None
        self.folder_cache = {}
        self._authenticate()

    def _authenticate(self):
        token_path = 'token.json'
        creds_path = 'credentials.json'
        
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                logger.info("[yellow]⏳ Need to authorize Google Drive (should only happen once).[/yellow]")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self.creds = flow.run_local_server(port=8080)
                
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())
                
        self.service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
        logger.info("[dim]☁️ Initialized Google Drive API Connection[/dim]")

    def _get_or_create_folder(self, folder_name: str) -> str:
        if folder_name in self.folder_cache:
            return self.folder_cache[folder_name]
            
        query = f"'{self.root_folder_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            folder_id = items[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.root_folder_id]
            }
            logger.info(f"[cyan]📁 Creating new folder '{folder_name}' in Google Drive...[/cyan]")
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
        self.folder_cache[folder_name] = folder_id
        return folder_id

    def upload_file(self, file_path: str, filename: str, book_id: int) -> str:
        # Determine the folder number (1 for 1-1000, 2 for 1001-2000, etc.)
        folder_num = ((book_id - 1) // 1000) + 1
        folder_name = str(folder_num)
        
        folder_id = self._get_or_create_folder(folder_name)
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        file_size = os.path.getsize(file_path)
        media = MediaFileUpload(file_path, resumable=True, chunksize=1024*1024)
        
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        )
        
        response = None
        
        with Progress() as progress:
            task = progress.add_task(f"[magenta]☁️ Uploading to Drive: {filename[:30]}...[/magenta]", total=file_size)
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress.update(task, completed=status.resumable_progress)
            
            progress.update(task, completed=file_size)
            
        # Try webContentLink (direct download) first, fallback to webViewLink
        link = response.get('webContentLink') or response.get('webViewLink')
        return link

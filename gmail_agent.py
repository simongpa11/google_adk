import os
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/documents.readonly'
]

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: 'credentials.json' not found. Please download it from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_doc_content(service, document_id):
    try:
        doc = service.documents().get(documentId=document_id).execute()
        content = ""
        for element in doc.get('body').get('content'):
            if 'paragraph' in element:
                for run in element.get('paragraph').get('elements'):
                    if 'textRun' in run:
                        content += run.get('textRun').get('content')
        return content
    except HttpError as err:
        print(f"An error occurred reading the doc: {err}")
        return None

def create_message(to, subject, body, thread_id):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message, 'threadId': thread_id}

def main():
    # Configure Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return
    
    client = genai.Client(api_key=api_key)

    creds = get_credentials()
    if not creds:
        return
        
    gmail_service = build('gmail', 'v1', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # Config
    SENDER_FILTER = "simon.garcia@aquaservice.com"
    DOC_ID = os.getenv("GOOGLE_DOC_ID")

    if not DOC_ID:
        print("Error: GOOGLE_DOC_ID not found in .env file.")
        return

    # Get Doc Content
    print(f"Reading context from Google Doc: {DOC_ID}...")
    doc_content = get_doc_content(docs_service, DOC_ID)
    if not doc_content:
        return

    # Search for unread emails from sender
    query = f"from:{SENDER_FILTER} is:unread"
    try:
        results = gmail_service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print(f"No new unread messages from {SENDER_FILTER}.")
            return

        for msg in messages:
            msg_data = gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            thread_id = msg_data['threadId']
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            
            # Get body
            parts = msg_data['payload'].get('parts', [])
            body = ""
            if not parts:
                body_data = msg_data['payload'].get('body', {}).get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode()
            else:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
            
            print(f"Processing email: {subject}")

            # Generate response with Gemini
            prompt = f"""
            Eres un asistente automático. He recibido el siguiente correo de {SENDER_FILTER}:
            
            Asunto: {subject}
            Cuerpo: {body}
            
            Utiliza la siguiente información de contexto para dar una respuesta adecuada:
            ---
            {doc_content}
            ---
            
            Responde de manera profesional y amable. Solo devuelve el texto del cuerpo del correo de respuesta.
            """
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            reply_body = response.text

            # Send reply
            reply = create_message(
                to=SENDER_FILTER,
                subject=f"Re: {subject}",
                body=reply_body,
                thread_id=thread_id
            )
            gmail_service.users().messages().send(userId='me', body=reply).execute()
            print(f"Reply sent to {SENDER_FILTER}")

            # Mark as read (remove UNREAD label)
            gmail_service.users().messages().modify(
                userId='me', 
                id=msg['id'], 
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"Message {msg['id']} marked as read.")

    except HttpError as err:
        print(f"An error occurred: {err}")

if __name__ == '__main__':
    main()

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_about_us_info():
    """
    Fetches the content of the company's 'About Us' Google Doc.
    Use this to answer questions about the company, its products, policies, etc.
    """
    try:
        doc_id = os.getenv("GOOGLE_DOC_ID")
        creds_path = 'credentials.json'

        if not doc_id:
            return "Error: GOOGLE_DOC_ID is not configured."
        if not os.path.exists(creds_path):
            return "Error: Google credentials.json file not found."

        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=['https://www.googleapis.com/auth/documents.readonly']
        )
        service = build('docs', 'v1', credentials=creds)

        document = service.documents().get(documentId=doc_id).execute()
        doc_content = document.get('body').get('content')

        text = ''
        for value in doc_content:
            if 'paragraph' in value:
                elements = value.get('paragraph').get('elements')
                for elem in elements:
                    if 'textRun' in elem:
                        text += elem.get('textRun').get('content')
        return text if text else "The document appears to be empty."
    except Exception as e:
        return f"An error occurred while fetching the document: {str(e)}"
import requests
import json
from typing import Optional, List
from datetime import datetime


def send_email(
        base_url: str,
        auth: tuple,
        to: List[str],
        subject: str,
        body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
):
    """
    Sends an email using the EGroupware REST API.
    """
    url = f"{base_url}/mail/"

    # --- Construct the payload based on the POST documentation ---
    payload = {
        "to": to,
        "subject": subject,
    }

    # Add optional fields only if they have values
    if body:
        payload["body"] = body
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc

    try:
        response = requests.post(url, auth=auth, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()

        success_message = f"Email with subject '{subject}' was sent successfully to {', '.join(to)}."

        return json.dumps({
            "status": "success",
            "message": success_message,
        })
    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to send email. API Error: {e.response.text}"
        })


def list_emails(
        base_url: str,
        auth: tuple,
        query: Optional[str] = None,
        limit: int = 10
):
    """
    List recent emails from the user's mailbox. Attempts to detect unread messages and
    returns a JSON array of messages with a simple 'seen' boolean when possible.
    This function is tolerant to varying EGroupware mail API responses.
    """
    url = f"{base_url}/mail/"

    params = {}
    if query:
        params['search'] = query
    params['limit'] = limit

    try:
        response = requests.get(url, auth=auth, headers={"Accept": "application/json"}, params=params)
        response.raise_for_status()
        data = response.json()

        # EGroupware API may return messages under 'responses' or as a list directly.
        messages = []
        if isinstance(data, dict) and 'responses' in data:
            # Try to unwrap responses dict
            for _, m in data.get('responses', {}).items():
                if isinstance(m, dict):
                    messages.append(m)
        elif isinstance(data, list):
            messages = data
        elif isinstance(data, dict) and 'messages' in data:
            messages = data.get('messages', [])
        else:
            # Unknown shape, return the raw object as single entry
            messages = [data]

        processed = []
        for m in messages[:limit]:
            # Standardize some common fields, tolerant to missing keys
            subject = m.get('subject') if isinstance(m, dict) else ''
            from_field = m.get('from') if isinstance(m, dict) else ''
            date = m.get('date') if isinstance(m, dict) else None

            # Detect 'seen' state using several common keys
            seen = None
            if isinstance(m, dict):
                if 'flags' in m and isinstance(m['flags'], list):
                    # E.g. flags may contain 'SEEN' or '\\Seen'
                    seen = any(('SEEN' in f.upper() or '\\SEEN' in f.upper() or 'seen' in f.lower()) for f in m['flags'])
                if seen is None and 'seen' in m:
                    seen = bool(m.get('seen'))
                if seen is None and 'is_read' in m:
                    seen = bool(m.get('is_read'))

            if seen is None:
                # Default to False (unread) to be conservative
                seen = False

            processed.append({
                'id': m.get('id') if isinstance(m, dict) else None,
                'subject': subject,
                'from': from_field,
                'date': date,
                'seen': seen,
                'raw': m
            })

        return json.dumps({
            'status': 'success',
            'count': len(processed),
            'messages': processed
        })

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            'status': 'error',
            'message': f'Failed to list emails. API Error: {e.response.status_code} - {e.response.text}'
        })
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}'
        })

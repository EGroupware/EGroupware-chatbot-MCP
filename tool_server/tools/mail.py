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
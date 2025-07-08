import requests
import json
from typing import Optional


def create_contact(base_url: str, auth: tuple, full_name: str, email: str,
                   phone: Optional[str] = None, company: Optional[str] = None,
                   address: Optional[str] = None, notes: Optional[str] = None):
    """
    CREATE CONTACT TOOL
    Adds a new contact to the EGroupware address book.
    """
    url = f"{base_url}/addressbook/"
    name_parts = full_name.split()
    first_name, last_name = (name_parts[0], " ".join(name_parts[1:])) if len(name_parts) > 1 else (full_name, "")

    # This is the data we want to return to the LLM
    payload = {
        "fullName": full_name,
        "name/given": first_name,
        "name/surname": last_name,
        "emails/work": email
    }
    if company: payload["organizations/org/name"] = company
    if phone: payload["phones/tel_work"] = phone
    if address: payload["addresses/work/street"] = address
    if notes: payload["notes/note"] = notes

    try:
        response = requests.post(url, auth=auth, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()

        # Return a JSON object containing the status and the data that was just created.
        return json.dumps({
            "status": "success",
            "message": "Contact created successfully.",
            "contact_details": payload  # <-- Give the LLM the data to format!
        })
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text
        return json.dumps({
            "status": "error",
            "message": f"Failed to create contact. Server responded with status {e.response.status_code}.",
            "details": error_details
        })




def search_contacts(base_url: str, auth: tuple, query: str):
    """
    Fetches all contacts and searches locally by full name or email.
    """
    url = f"{base_url}/addressbook/"
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        data = response.json()
        responses = data.get("responses", {})

        # Filter contacts by name or email
        matches = []
        for _, contact in responses.items():
            name = contact.get("name", {})
            full_name = name.get("full", "").lower()
            last_name = name.get("n-family", "").lower()
            emails = contact.get("emails", [])

            if (query.lower() in full_name or
                query.lower() in last_name or
                any(query.lower() in e.get("value", "").lower() for e in emails)):
                matches.append(contact)

        if not matches:
            return json.dumps({
                "status": "success",
                "found": False,
                "message": "No contacts found matching the query."
            })

        return json.dumps({
            "status": "success",
            "found": True,
            "count": len(matches),
            "contacts": matches[:5]
        })

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to search contacts. Server responded with status {e.response.status_code}."
        })


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
    Search contacts using the EGroupware REST API's search functionality.

    Args:
        base_url: Base URL of the EGroupware installation
        auth: Tuple of (username, password) for basic auth
        query: Search query string (supports space-separated OR or + for AND)

    Returns:
        JSON string with search results
    """
    url = f"{base_url}/addressbook/"

    headers = {
        "Accept": "application/json"
    }

    params = {
        "filters[search]": query,
        "options[limit]": 10,
        "props[]": ["fullName", "emails", "phones", "organizations"]
    }

    try:
        response = requests.get(url, auth=auth, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        contacts = []
        for contact in data.get("responses", {}).values():
            if not contact:
                continue

            # Parse contact fields
            full_name = contact.get("fullName", {}).get("value", "")
            email = ""
            phone = ""
            org = ""

            emails = contact.get("emails", {})
            if isinstance(emails, dict) and emails:
                email = next(iter(emails.values()), {}).get("email", "")

            phones = contact.get("phones", {})
            if isinstance(phones, dict) and phones:
                phone = next(iter(phones.values()), {}).get("phone", "")

            org_data = contact.get("organizations", {}).get("org", {})
            if isinstance(org_data, dict):
                org = org_data.get("name", "")

            contacts.append({
                "name": full_name,
                "email": email,
                "phone": phone,
                "organization": org
            })

        return json.dumps({
            "status": "success",
            "found": bool(contacts),
            "message": f"Found {len(contacts)} contact(s)." if contacts else "No contacts found.",
            "contacts": contacts
        })

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to search contacts. Server responded with status {e.response.status_code}.",
            "details": e.response.text
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        })

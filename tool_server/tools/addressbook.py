from typing import Optional
import requests
import vobject
import json

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
    Search contacts using CardDAV and filtering locally.
    This function searches through ALL contacts, not just a paginated subset.

    Args:
        base_url: Base URL of the EGroupware installation
        auth: Tuple of (username, password) for basic auth
        query: Search query string

    Returns:
        JSON string with filtered contact results
    """
    url = f"{base_url}/addressbook/"

    # Use CardDAV PROPFIND to get ALL contacts for searching
    propfind_body = '''<?xml version="1.0" encoding="UTF-8"?>
<propfind xmlns="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
    <prop>
        <getetag/>
        <card:address-data/>
    </prop>
</propfind>'''

    headers = {
        "Content-Type": "application/xml",
        "Depth": "1"
    }

    try:
        # Make PROPFIND request to get ALL contacts for searching
        response = requests.request("PROPFIND", url, auth=auth, headers=headers, data=propfind_body)
        response.raise_for_status()

        # Parse the XML response to extract vCard data
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)

        all_contacts = []
        namespaces = {
            'dav': 'DAV:',
            'card': 'urn:ietf:params:xml:ns:carddav'
        }

        for response_elem in root.findall('.//dav:response', namespaces):
            # Look for address-data elements containing vCard
            address_data_elems = response_elem.findall('.//card:address-data', namespaces)

            for addr_data in address_data_elems:
                if addr_data.text and addr_data.text.strip():
                    try:
                        vcard = vobject.readOne(addr_data.text)

                        full_name = getattr(vcard, 'fn', None)
                        email = getattr(vcard, 'email', None)
                        phone = getattr(vcard, 'tel', None)
                        org = getattr(vcard, 'org', None)
                        address = getattr(vcard, 'adr', None)

                        all_contacts.append({
                            "name": full_name.value if full_name else "",
                            "email": email.value if email else "",
                            "phone": phone.value if phone else "",
                            "organization": org.value[0] if org and hasattr(org, 'value') and len(org.value) > 0 else "",
                            "address": f"{address.street}, {address.city}" if address and hasattr(address, 'street') and hasattr(address, 'city') else ""
                        })
                    except Exception as parse_error:
                        continue

        # Filter contacts based on query - search through ALL contacts
        filtered_contacts = []
        query_lower = query.lower()

        for contact in all_contacts:
            # Combine all searchable fields
            searchable_text = " ".join(filter(None, [
                contact.get("name", ""),
                contact.get("email", ""),
                contact.get("phone", ""),
                contact.get("organization", ""),
                contact.get("address", "")
            ])).lower()

            # Check if query matches any field
            if query_lower in searchable_text:
                filtered_contacts.append(contact)

        return json.dumps({
            "status": "success",
            "found": bool(filtered_contacts),
            "message": f"Found {len(filtered_contacts)} contact(s) matching '{query}' (searched through {len(all_contacts)} total contacts)." if filtered_contacts else f"No contacts found matching '{query}' (searched through {len(all_contacts)} total contacts).",
            "total_searched": len(all_contacts),
            "contacts": filtered_contacts
        })

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to retrieve contacts. Server responded with status {e.response.status_code}.",
            "details": e.response.text
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An unexpected error occurred during search: {str(e)}"
        })




def get_all_contacts(base_url: str, auth: tuple, limit: Optional[int] = 10, offset: Optional[int] = 0):
    """
    GET ALL CONTACTS TOOL
    Retrieves contacts from the EGroupware address book via CardDAV with pagination.

    Args:
        base_url: Base URL of the EGroupware installation (without /addressbook/)
        auth: Tuple of (username, password) for basic auth
        limit: Maximum number of contacts to return (default: 50, max: 100)
        offset: Number of contacts to skip (for pagination, default: 0)

    Returns:
        JSON string with paginated contacts
    """
    # Enforce reasonable limits
    limit = min(limit or 10, 15)  # Max 100 contacts per request
    offset = max(offset or 0, 0)   # No negative offsets

    url = f"{base_url}/addressbook/"

    # First, get the list of contact URLs using PROPFIND
    propfind_body = '''<?xml version="1.0" encoding="UTF-8"?>
<propfind xmlns="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
    <prop>
        <getetag/>
        <card:address-data/>
    </prop>
</propfind>'''

    headers = {
        "Content-Type": "application/xml",
        "Depth": "1"
    }

    try:
        # Make PROPFIND request to get all contacts
        response = requests.request("PROPFIND", url, auth=auth, headers=headers, data=propfind_body)
        response.raise_for_status()

        # Parse the XML response to extract vCard data
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)

        all_contacts = []
        namespaces = {
            'dav': 'DAV:',
            'card': 'urn:ietf:params:xml:ns:carddav'
        }

        for response_elem in root.findall('.//dav:response', namespaces):
            # Look for address-data elements containing vCard
            address_data_elems = response_elem.findall('.//card:address-data', namespaces)

            for addr_data in address_data_elems:
                if addr_data.text and addr_data.text.strip():
                    try:
                        vcard = vobject.readOne(addr_data.text)

                        full_name = getattr(vcard, 'fn', None)
                        email = getattr(vcard, 'email', None)
                        phone = getattr(vcard, 'tel', None)
                        org = getattr(vcard, 'org', None)
                        address = getattr(vcard, 'adr', None)

                        all_contacts.append({
                            "name": full_name.value if full_name else "",
                            "email": email.value if email else "",
                            "phone": phone.value if phone else "",
                            "organization": org.value[0] if org and hasattr(org, 'value') and len(org.value) > 0 else "",
                            "address": f"{address.street}, {address.city}" if address and hasattr(address, 'street') and hasattr(address, 'city') else ""
                        })
                    except Exception as parse_error:
                        continue

        # Apply pagination
        total_contacts = len(all_contacts)
        paginated_contacts = all_contacts[offset:offset + limit]

        # Calculate pagination info
        has_more = offset + limit < total_contacts
        next_offset = offset + limit if has_more else None

        return json.dumps({
            "status": "success",
            "message": f"Retrieved {len(paginated_contacts)} contact(s) from address book (page {offset//limit + 1}).",
            "total_contacts": total_contacts,
            "returned_contacts": len(paginated_contacts),
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": next_offset,
            "contacts": paginated_contacts
        })

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to retrieve contacts. Server responded with status {e.response.status_code}.",
            "details": e.response.text
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        })

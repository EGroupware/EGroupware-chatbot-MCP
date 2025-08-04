import json
import os
from typing import AsyncGenerator
import requests
import openai
from datetime import datetime


from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from fastapi.staticfiles import StaticFiles

from . import auth, llm_service, prompts, schemas
from .schemas import LoginRequest


load_dotenv()

app = FastAPI(title="EGroupware Agent Service")
app.mount("/static", StaticFiles(directory="static"), name="static")

chat_histories = {}
TOOL_SERVER_URL = os.getenv("TOOL_SERVER_URL")



# Function to call the tool server
def call_tool_server(tool_name: str, args: dict, user_credentials: schemas.TokenData):
    if not TOOL_SERVER_URL:
        return "Error: Tool Server URL is not configured."

    url = f"{TOOL_SERVER_URL}/execute/{tool_name}"

    # Create a complete auth payload including the EGroupware URL
    auth_payload = {
        "username": user_credentials.username,
        "password": user_credentials.password,
        "egw_url": user_credentials.egw_url
    }

    payload = {"auth": auth_payload, "args": args}

    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json().get("result", "Tool executed but returned no result.")
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            error_detail = e.response.text
        return f"Error from Tool Server for '{tool_name}': {error_detail}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the Tool Server: {e}"


# Basic routes for user interface
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_login():
    with open("static/login.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/chat-ui", response_class=HTMLResponse, include_in_schema=False)
async def read_chat_ui():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


# User authentication route
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
        login_data: LoginRequest
):
    # Save credentials to in-memory storage if they're valid
    if not auth.verify_and_save_credentials(
            username=login_data.username,
            password=login_data.password,
            egw_url=login_data.egw_url
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid EGroupware URL or credentials."
        )

    # Validate provider configuration
    if login_data.provider_type not in [p.value for p in llm_service.ProviderType]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type: {login_data.provider_type}"
        )

    # Check if base_url is required but not provided
    if login_data.provider_type != llm_service.ProviderType.OPENAI.value and not login_data.base_url:
        # OpenAI doesn't need a base_url, others do
        if login_data.provider_type in [
            llm_service.ProviderType.IONOS.value,
            llm_service.ProviderType.AZURE.value,
            llm_service.ProviderType.OPENROUTER.value
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Base URL is required for {login_data.provider_type} provider"
            )

    # Create the JWT payload with all the session configuration
    jwt_payload = {
        "sub": login_data.username,
        "pwd": login_data.password,
        "egw_url": login_data.egw_url,
        "ai_key": login_data.ai_key,
        "provider_type": login_data.provider_type,
        "base_url": login_data.base_url
    }

    # Create the token
    token = auth.create_access_token(data=jwt_payload)
    return {"access_token": token, "token_type": "bearer"}

tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "create_contact",
            "description": "Adds a new contact to the EGroupware address book.",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "company": {"type": "string"},
                    "address": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["full_name", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Searches for existing contacts by name or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_contacts",
            "description": "Retrieves contacts from the EGroupware address book with pagination. For large contact lists, always start with a small limit (e.g., 20-50) and offer to show more if needed. Never retrieve more than 100 contacts at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of contacts to return (default: 50, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of contacts to skip for pagination (default: 0)",
                        "minimum": 0,
                        "default": 0
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email to one or more recipients. Requires a subject and a list of 'to' addresses. Can optionally include a body, cc, and bcc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of primary recipient email addresses."
                    },
                    "subject": {
                        "type": "string",
                        "description": "The subject line of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": "The plain text body content of the email."
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of CC recipient email addresses."
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of BCC recipient email addresses."
                    }
                },
                "required": ["to", "subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Schedules a new event in the user's calendar. Requires a title, start time, and end time. Can optionally include a timezone, description, location, and a list of attendee emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title or subject of the event."
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "The start date and time in 'YYYY-MM-DD HH:MM:SS' format."
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "The end date and time in 'YYYY-MM-DD HH:MM:SS' format. The AI must calculate this if the user provides a duration (e.g., 'for 90 minutes')."
                    },
                    "time_zone": {
                        "type": "string",
                        "description": "The IANA Time Zone for the event (e.g., 'Europe/Berlin', 'America/New_York'). If the user doesn't specify one, you should ask or infer it. Defaults to 'UTC' if not provided."
                    },
                    "description": {
                        "type": "string",
                        "description": "A detailed agenda for the event."
                    },
                    "location": {
                        "type": "string",
                        "description": "The physical location or online meeting link."
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of email addresses for people to invite."
                    }
                },
                "required": ["title", "start_datetime", "end_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "Lists upcoming events between a start and end date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."}
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Creates a new task in the user's InfoLog. Requires a title and can optionally include a due date and a description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title or subject of the task."
                    },
                    "due_date": {
                        "type": "string",
                        "description": "The due date for the task, in 'YYYY-MM-DD' format."
                    },
                    "description": {
                        "type": "string",
                        "description": "A detailed description of the task."
                    }
                },
                "required": ["title"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_company_info",
            "description": "Fetches the company's internal knowledge base. Use this to answer any questions about the company's mission, products, policies, history, or contact details.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

# Chat streaming endpoint
async def chat_stream_generator(message: str, current_user: schemas.TokenData) -> AsyncGenerator[str, None]:
    if current_user.username not in chat_histories:
        chat_histories[current_user.username] = [{"role": "system", "content": prompts.get_system_prompt()}]
    chat_histories[current_user.username].append({"role": "user", "content": message})


    stream = llm_service.get_streaming_chat_response(
        messages=chat_histories[current_user.username],
        tools=tool_definitions,
        current_user_config=current_user
    )

    tool_calls, full_response = [], ""
    for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if delta and delta.content:
            full_response += delta.content
            yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"
        elif delta and delta.tool_calls:
            for tc_chunk in delta.tool_calls:
                if len(tool_calls) <= tc_chunk.index:
                    tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                tc = tool_calls[tc_chunk.index]
                if tc_chunk.id: tc["id"] = tc_chunk.id
                if tc_chunk.function.name: tc["function"]["name"] = tc_chunk.function.name
                if tc_chunk.function.arguments: tc["function"]["arguments"] += tc_chunk.function.arguments

    if full_response: chat_histories[current_user.username].append({"role": "assistant", "content": full_response})

    if tool_calls:
        chat_histories[current_user.username].append({"role": "assistant", "tool_calls": tool_calls})
        for tool_call in tool_calls:
            name, args = tool_call["function"]["name"], json.loads(tool_call["function"]["arguments"])
            yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': name})}\n\n"
            response = call_tool_server(tool_name=name, args=args, user_credentials=current_user)
            yield f"data: {json.dumps({'type': 'tool_result', 'result': str(response)})}\n\n"
            chat_histories[current_user.username].append(
                {"tool_call_id": tool_call["id"], "role": "tool", "name": name, "content": str(response)})

        second_stream = llm_service.get_streaming_chat_response(
            messages=chat_histories[current_user.username],
            tools=tool_definitions,
            current_user_config=current_user
        )
        second_response = ""
        for chunk in second_stream:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                second_response += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        if second_response: chat_histories[current_user.username].append(
            {"role": "assistant", "content": second_response})

    yield "event: end\ndata: {}\n\n"


# Endpoint to handle chat requests
@app.get("/chat", response_class=StreamingResponse, tags=["Chat"], summary="Chat with the EGroupware Agent", description="Streams chat responses from the EGroupware Agent. Requires a valid token.")
async def chat_endpoint(
    message: str = Query(..., description="The user's message to the agent."),
    token: str = Query(..., description="Authentication token for the user.")
):
    """
    Streams chat responses from the EGroupware Agent. Requires a valid token.
    """
    current_user = await auth.get_current_user(token)
    return StreamingResponse(chat_stream_generator(message, current_user), media_type="text/event-stream")


class EGroupwareURLValidationRequest(BaseModel):
    url: str = Field(..., example="https://demo.egroupware.org/egroupware")

class EGroupwareURLValidationResponse(BaseModel):
    valid: bool = Field(..., description="Whether the EGroupware URL is valid and reachable.")
    detail: str | None = Field(None, description="Additional information about the validation result.")


# Validation endpoints
@app.post(
    "/validate/egroupware-url",
    response_model=EGroupwareURLValidationResponse,
    tags=["Validation"],
    summary="Validate EGroupware URL",
    description="Checks if the provided EGroupware URL is reachable and requires authentication."
)
async def validate_egroupware_url(
    data: EGroupwareURLValidationRequest = Body(..., example={"url": "https://demo.egroupware.org/egroupware"})
):
    """
    Checks if the provided EGroupware URL is reachable and requires authentication.
    Returns valid=True if the URL exists and returns 401 (Unauthorized), otherwise valid=False.
    """
    url = data.url
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        test_url = f"{url.rstrip('/')}/addressbook/"
        response = requests.get(test_url, timeout=10)
        if response.status_code == 401:
            return EGroupwareURLValidationResponse(valid=True, detail=None)
        return EGroupwareURLValidationResponse(valid=False, detail="Invalid EGroupware URL")
    except requests.RequestException as e:
        return EGroupwareURLValidationResponse(valid=False, detail=f"Could not connect to EGroupware: {str(e)}")


@app.post("/validate/ai-key")
async def validate_ai_key(data: dict):
    api_key = data.get("api_key")
    provider_type = data.get("provider_type")
    base_url = data.get("base_url")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    if not provider_type or provider_type not in [p.value for p in llm_service.ProviderType]:
        raise HTTPException(status_code=400, detail="Valid provider type is required")

    # Check if base_url is required but not provided
    if provider_type != llm_service.ProviderType.OPENAI.value and not base_url:
        if provider_type in [
            llm_service.ProviderType.IONOS.value,
            llm_service.ProviderType.AZURE.value,
            llm_service.ProviderType.OPENROUTER.value
        ]:
            return {
                "valid": False,
                "detail": f"Base URL is required for {provider_type} provider",
                "provider_type": provider_type
            }

    try:
        # Create provider instance based on the provider type
        provider = llm_service.Provider.create_provider(
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url
        )

        # Make a minimal API call to validate the key
        # This could fail depending on the provider if they don't support the same interface
        # We'll catch exceptions and report them
        client = provider.get_client()

        # For simplicity, let's just return valid if we can create a client
        # In a production environment, you would make a test API call to verify
        return {"valid": True, "provider_type": provider_type}
    except Exception as e:
        return {
            "valid": False,
            "detail": f"Invalid API key or configuration: {str(e)}",
            "provider_type": provider_type
        }
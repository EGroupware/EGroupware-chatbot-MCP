import json
import os

from typing import AsyncGenerator, List
import requests
import openai


from dotenv import load_dotenv
from fastapi import  FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
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
        "egw_url": user_credentials.egw_url  # Ensure egw_url is included
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

    # 2. Determine the type of API key
    is_openai = login_data.ai_key.startswith('sk-')
    is_github = login_data.ai_key.startswith('gh')
    is_ionos = not (is_openai or is_github)

    # Validate IONOS configuration if needed
    if is_ionos and not login_data.ionos_base_url:
        raise HTTPException(
            status_code=400,
            detail="IONOS base URL is required for IONOS API keys"
        )

    # 3. Create the JWT payload with all the session configuration
    jwt_payload = {
        "sub": login_data.username,
        "pwd": login_data.password,
        "egw_url": login_data.egw_url,
        "ai_key": login_data.ai_key,
        "is_ionos": is_ionos,
        "ionos_base_url": login_data.ionos_base_url if is_ionos else None
    }

    # 4. Create the token
    token = auth.create_access_token(data=jwt_payload)
    return {"access_token": token, "token_type": "bearer"}


# Chat streaming endpoint
async def chat_stream_generator(message: str, current_user: schemas.TokenData) -> AsyncGenerator[str, None]:
    if current_user.username not in chat_histories:
        chat_histories[current_user.username] = [{"role": "system", "content": prompts.get_system_prompt()}]
    chat_histories[current_user.username].append({"role": "user", "content": message})

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
                "description": "Searches for existing contacts by  .",
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

    stream = llm_service.get_streaming_chat_response(
        messages=chat_histories[current_user.username],
        tools=tool_definitions,
        current_user_config=current_user
    )

    tool_calls, full_response = [], ""
    for chunk in stream:
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
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                second_response += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        if second_response: chat_histories[current_user.username].append(
            {"role": "assistant", "content": second_response})

    yield "event: end\ndata: {}\n\n"


# Endpoint to handle chat requests
@app.get("/chat")
async def chat_endpoint(message: str, token: str):
    current_user = await auth.get_current_user(token)
    return StreamingResponse(chat_stream_generator(message, current_user), media_type="text/event-stream")


# Validation endpoints
@app.post("/validate/egroupware-url")
async def validate_egroupware_url(data: dict):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        # Try to access the EGroupware URL
        test_url = f"{url.rstrip('/')}/addressbook/"
        response = requests.get(test_url, timeout=10)
        if response.status_code == 401:  # 401 means the URL exists but needs auth
            return {"valid": True}
        return {"valid": False, "detail": "Invalid EGroupware URL"}
    except requests.RequestException as e:
        return {"valid": False, "detail": f"Could not connect to EGroupware: {str(e)}"}


@app.post("/validate/ai-key")
async def validate_ai_key(data: dict):
    api_key = data.get("api_key")
    ionos_base_url = data.get("ionos_base_url")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    # Check the type of API key
    is_openai = api_key.startswith("sk-")
    is_github = api_key.startswith("gh")
    is_ionos = not (is_openai or is_github)

    try:
        if is_openai:
            # Test OpenAI API key
            client = openai.OpenAI(api_key=api_key)
            model = "gpt-3.5-turbo"
        elif is_github:
            # Test GitHub API key
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://models.github.ai/inference"
            )
            model = "openai/gpt-4o-mini"
        else:
            # Test IONOS API key
            if not ionos_base_url:
                return {
                    "valid": False,
                    "detail": "IONOS base URL is required for IONOS API keys",
                    "is_ionos": True,
                    "is_github": False
                }

            client = openai.OpenAI(
                api_key=api_key,
                base_url=ionos_base_url
            )
            model = "meta-llama/Llama-3.3-70B-Instruct"

        # Make a minimal API call to validate the key
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        return {"valid": True, "is_ionos": is_ionos, "is_github": is_github}
    except Exception as e:
        return {
            "valid": False,
            "detail": f"Invalid API key: {str(e)}",
            "is_ionos": is_ionos,
            "is_github": is_github
        }




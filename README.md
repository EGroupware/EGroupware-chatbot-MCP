# EGroupware AI Assistant 

A modern AI assistant that integrates with EGroupware to provide a conversational interface for accessing and managing EGroupware functionalities.

## Overview

This project implements an AI-powered chatbot system for EGroupware that allows users to interact with their EGroupware data using natural language. The system consists of two main components:

1. **Agent Service**: Handles the conversational interface, LLM interactions, authentication, and user interface
2. **Tool Server**: Connects to EGroupware APIs and provides tools for the agent to perform actions in EGroupware

## Architecture

The system is designed as a microservice architecture with Docker containerization:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Web Frontend  │◄────┤  Agent Service  │◄────┤  Tool Server    │
│   (Browser)     │     │  (FastAPI)      │     │  (FastAPI)      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │   EGroupware    │
                                               │                 │
                                               └─────────────────┘
```

## Features

- **Conversational AI Interface**: Natural language processing for EGroupware interactions
- **Authentication**: Secure login with EGroupware credentials
- **EGroupware Integration**: Access to key EGroupware modules:
  - Addressbook management
  - Calendar events and appointments
  - InfoLog (tasks and notes)
  - Email communications
  - Knowledge base access
- **Multi-model LLM Support**: Configurable to work with various LLM providers
- **Containerized Deployment**: Easy setup with Docker Compose

## Installation & Setup

### Prerequisites

- Docker and Docker Compose
- EGroupware instance with API access
- LLM API keys (OpenAI, Azure, Anthropic, etc.)

### Configuration

1. Create a `.env` file in the project root with the following variables:

```
# .env file for EGroupware Chatbot

# Tool Server Configuration
TOOL_SERVER_URL=http://tool-server:8001

# Security (change these values!)
JWT_SECRET=your_jwt_secret_here

```

### Deployment

```bash
# Build and start the containers
docker-compose up -d

# Check logs if needed
docker-compose logs -f
```

The application will be available at https://localhost (HTTPS via nginx). The old direct http://localhost:8000 endpoint is now internal only.
If ports 80/443 are already in use on the host, the compose file remaps nginx to 8080/8443 (access: https://localhost:8443). Adjust the `ports:` section of the `nginx` service if you free 80/443 and want the canonical ports again.

## Usage

1. Navigate to https://localhost in your web browser (accept the self-signed certificate on first visit)
2. Log in with your EGroupware credentials
3. Start interacting with the chatbot by typing natural language queries such as:
   - "Show my upcoming meetings for next week"
   - "Create a new contact for John Doe with email john.doe@example.com"
   - "Find documents about project planning in the knowledge base"

## Project Structure

- `agent_service/`: The main service that handles the LLM interface and user interactions
  - `main.py`: FastAPI application entry point
  - `auth.py`: Authentication handling
  - `llm_service.py`: LLM provider integrations
  - `prompts.py`: System prompts for the LLM
  - `schemas.py`: Data models

- `tool_server/`: The service that connects to EGroupware
  - `tools/`: Individual tool implementations
    - `addressbook.py`: Contact management functions
    - `calendar.py`: Calendar event functions
    - `infolog.py`: Tasks and notes functions
    - `mail.py`: Email functions
    - `knowledge.py`: Knowledge base search functions
  - `knowledge/`: Local knowledge base files

- `static/`: Web frontend files
  - `index.html`: Main chat interface
  - `login.html`: Login page
  - `script.js`: Frontend JavaScript
  - `style.css`: Styling

- `docker-compose.yml`: Docker Compose configuration
- `agent.Dockerfile`: Dockerfile for the agent service
- `tool.Dockerfile`: Dockerfile for the tool server
- `requirements.txt`: Python dependencies

## Development

### Local Development Setup

1. Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the services separately (HTTP only, for local dev without nginx TLS):
```bash
# Terminal 1 - Tool Server
uvicorn tool_server.main:app --reload --port 8001

# Terminal 2 - Agent Service
uvicorn agent_service.main:app --reload --port 8000
```
### HTTPS / TLS

Production (and the default Docker Compose) uses an `nginx` reverse proxy that:

- Terminates TLS on port 443 using the certificate in `ssl/cert.pem` and key `ssl/key.pem`
- Redirects all HTTP (port 80) to HTTPS
- Proxies traffic to the internal FastAPI services (`agent-service` on 8000, `tool-server` on 8001)
- Optionally exposes Tool Server docs at `https://localhost/tools/docs` (FastAPI docs) if enabled in config

Replace the provided self-signed certs with real certificates for production. You can generate a new self-signed pair for testing:

```bash
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem -days 365 \
  -subj "/C=DE/ST=NRW/L=Cologne/O=EGroupware/OU=AI/CN=localhost"
```

If you want automated Let's Encrypt certificates, add a companion container like `nginx-proxy` + `acme-companion` or use `certbot` on the host and mount the live certs into the `nginx` service.

### Quick Reply Suggestions

After each assistant response the UI now fetches up to 4 AI-generated "quick reply" buttons (endpoint: `GET /suggestions?token=...&count=4`). Clicking a button sends that suggestion as the next user message. If no history exists, starter suggestions are shown. The endpoint:

* Trims recent conversation (last ~6 turns)
* Prompts the model to return only a JSON array
* Falls back to safe defaults if parsing fails or model errors

To change number of buttons, adjust the `count` query param (1–6) or modify the initial fetch in `static/script.js`.

### Voice Input (Speech → Text)

The chat UI includes an optional microphone button that lets users dictate a message. When you click it, the browser records a short clip (WebM/Opus) and uploads it to the `/transcribe` endpoint. The server sends the audio to OpenAI Whisper (`whisper-1`) and returns transcribed text inserted into the message box for editing or immediate sending.

Current limitations:

* Only works when the selected provider is **OpenAI** (other providers will disable the mic button).
* Not enabled for Ionos / Anthropic / Azure in this version.
* Short form dictation (designed for < 45s). Longer recordings may fail or be slow.
* Audio is captured client-side; no local persistence.

Security / privacy notes:

* The raw JWT token is sent as `token` form field with the audio; ensure HTTPS is enforced (already handled by nginx).
* Replace the self-signed certificate in production to avoid MITM risks.

Extending voice:

* Add multi-provider support by integrating alternative speech APIs (Azure Speech, Deepgram, etc.).
* Add streaming partial transcripts by switching to a WebSocket or streaming upload and incremental UI updates.
* Add language auto-detection (specify `language` in the Whisper call).

### Updated Environment Variables

Ensure your `.env` uses the internal service name for the tool server now that HTTPS sits in front:

```
TOOL_SERVER_URL=http://tool-server:8001
```

Frontend/browser requests go to `https://localhost`, but the agent container still calls the tool server over the internal Docker network (HTTP is fine internally).

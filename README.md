# EGroupware AI (MCP)

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

The application will be available at http://localhost:8000

## Usage

1. Navigate to http://localhost:8000 in your web browser
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

2. Run the services separately:
```bash
# Terminal 1 - Tool Server
uvicorn tool_server.main:app --reload --port 8001

# Terminal 2 - Agent Service
uvicorn agent_service.main:app --reload --port 8000
```

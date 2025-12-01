# Agent ADK with Chainlit — Learning Guide

This project is a `Chainlit` application that integrates `Google ADK` agents, `MCP tools`, document processing, audio input, and a `SQLAlchemy` data layer backed. Use this guide to understand the architecture, configure the environment, and extend features.

## What You'll Need

- [Python 3.13+](https://www.python.org/downloads/)
- [Basic Python knowledge](https://www.geeksforgeeks.org/python/python-programming-language-tutorial/)
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- [Gemini API Key](https://aistudio.google.com/apikey?_gl=1*h8pp6f*_ga*MTgwODQyODIzMS4xNzYxNzUwOTI5*_ga_P1DBVKWT6V*czE3NjQ1MzAyNjQkbzEwJGcwJHQxNzY0NTMwMjY4JGo1NiRsMCRoMTEwODgxMjcyOA..) (free tier)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Create an Auth0 Application](https://auth0.com/docs/get-started/auth0-overview/create-applications)
- Code Editor of Choice

## Quick Start

- Prerequisites: Python `3.13+` (see `.python-version`), a modern browser, and API keys for required services.
- Clone the Repository
  ```shell
  git clone https://github.com/EliAbdiel/agent-adk-chainlit.git
  cd agent-adk-chainlit
  ```
- Install dependencies:
  - With `uv`: `uv sync`, or `pip`: `pip install -r requirements.txt`
  - Or via `pyproject.toml`: `pip install .` in a virtual environment.
- Create a `.env` at the project root with the required variables (see Configuration).
  ```shell
  # Windows
  copy .env.example .env

  # Linux/Mac
  cp .env.example .env
  ```
- Run the app in dev mode:
  ```shell
  # Linux/Mac
  source .venv/bin/activate

  # Windows (CMD)
  .venv\Scripts\activate

  # Windows (PowerShell)
  .venv\Scripts\Activate.ps1

  chainlit run main.py -w
  ```
- Open the provided local URL to interact with the UI.

## Configuration

Environment variables (all required) are read in `src/config/common.py:5–25`:
- `GEMINI_API_KEY`: Google Gemini API key used by document processing.
- `DEFAULT_MODEL`: Default model ID used for processing and prompts.
- `GEMINI_MODEL`: Model ID used by agents (e.g., Gemini model name).
- `TAVILY_SECRET_KEY`: Token for the Tavily MCP search server.
- `ELEVENLABS_API_KEY`: Key for ElevenLabs TTS/STT, if enabled.
- `LOCAL_DATABASE`: SQLAlchemy connection string (e.g., `sqlite:///chainlit.db` or Postgres URI).
- `CONTAINER_NAME`, `STORAGE_ACCOUNT_NAME`, `STORAGE_KEY`: Azure Blob Storage container/account/secret for file storage.

Example `.env` (use your real values):
```
GEMINI_API_KEY=your_gemini_key
DEFAULT_MODEL=gemini-2.0-flash
GEMINI_MODEL=gemini-2.5-flash
TAVILY_SECRET_KEY=your_tavily_token
ELEVENLABS_API_KEY=your_elevenlabs_key
LOCAL_DATABASE=sqlite:///chainlit.db
CONTAINER_NAME=your-container
STORAGE_ACCOUNT_NAME=your-storage-account
STORAGE_KEY=your-storage-key
```

## Architecture Overview
- Entry point: `main.py`
- UI helpers: `src/ui/*`
- Agents: `src/llm/agents/*` (Google ADK agents, runners, sessions)
- Audio: `src/llm/speech/speech_to_text.py`
- Documents: `src/document/*` (extraction, summarization)
- Data layer: `src/database/persistent_data_layer.py` (SQLAlchemy + Azure Blob)
- Config: `src/config/common.py` (env vars)
- Theme and welcome: `public/theme.json`, `chainlit.md`

## How the App Works

**Lifecycle Overview**

- App boot: Chainlit loads `main.py` and registers event handlers.
- User signs in: OAuth callback returns a default user `main.py:20–28`.
- Chat begins: Session variables, UI commands, and starters are set `main.py:30–58`.
- Tools discovery: When an MCP connection is made, tools are listed and cached `main.py:60–83`.
- Interaction paths: Text, attachments, and audio each follow specific handlers described below.

**User Commands and Starters**

- Commands rendered in the UI originate from `src/ui/commands.py:3–26` and are published at chat start `main.py:38–41`.
- Starter tiles come from `src/ui/chat_starters.py:3–30` via `@cl.set_starters` `main.py:49–58`.

**Message Handling**

- Entry point: `@cl.on_message` `main.py:131–212`.
- With attachments: Files matching `.pdf/.docx/.txt/.jpg/.jpeg/.png` are processed by `DocumentProcessor` and the resulting summary is appended to the user message `main.py:155–181`.
- Q&A route: The combined message (question + document summary) is delegated to `root_agent`/`question_answer_agent` to produce an answer `main.py:184–191` and `src/llm/agents/question_answer_agent.py:11–43`.
- Search route: If `command` in `COMMANDS`, the `search_agent` runs a web search using MCP tools `main.py:194–206` and `src/llm/agents/search_agent.py:25–55`.
- Summary route: If `command == "Summary"`, the `DocumentProcessor` creates a condensed summary `main.py:208–211`.

**Audio Flow**

- Start: Initializes audio buffers `main.py:84–89`.
- Chunk: Streams audio chunks to the buffer `main.py:90–104`.
- End: Transcribes audio to text and forwards to the message handler `main.py:105–130`.

**Document Processing**

- Supported types and validation: `src/document/document_processor.py:31–38`, `67–91`; config in `src/document/processor_config.py:1–29`.
- Summarization: Cleans text and generates a structured summary using Gemini `src/document/document_processor.py:93–146`.

**Agents and Tools**

- Search Agent: Integrates Tavily MCP for live search `src/llm/agents/search_agent.py:15–30`.
- Q&A Agent: Answers strictly from provided summary; `root_agent` orchestrates delegation `src/llm/agents/question_answer_agent.py:11–43`.
- Session/Runner creation: Utility in `src/llm/agents/utils/session_and_runner.py` used across routes.

**Persistence & Storage**

- Data layer: Bound via `@cl.data_layer` `main.py:213–216`, implemented in `src/database/persistent_data_layer.py:16–26`.
- Storage: Azure Blob client holds binary elements (images, uploads) configured by `.env` values.

**UI & Theme**

- Theme configuration: `public/theme.json`.
- Welcome screen: `chainlit.md` at project root controls intro content.

## Usage

**User Authentication**

Authentication is delegated to external `OAuth` providers such as `Auth0` and `GitHub`. The platform does not manage or store passwords. `OAuth` handles identity securely, and `Chainlit` processes login callbacks through a lightweight authentication handler.

![Login](public/gif/user-authentication.gif)

**Dashboard Overview**

The interface is the `Chainlit` conversational workspace an interactive chat environment rather than a traditional analytics dashboard. Users can ask questions, upload documents, perform live web search, and interact with multiple AI agents through an intuitive, streaming-enabled interface powered by Chainlit’s event system.

![Dashboard](public/gif/dashboard-overview.gif)

**Visual Analysis**

The visual analysis feature is powered by the `DocumentProcessor` class, which uses Google’s Gemini Vision API to perform optical character recognition (`OCR`) and extract meaningful content from uploaded image files. This enables the assistant to understand text, tables, and visual elements embedded within images for downstream processing and summarization.

![Image Understanding](public/gif/document-intelligence.gif)

**Document Intelligence**

Document intelligence is handled entirely by the `DocumentProcessor` class, which automatically:

- Detects and validates uploaded files
- Extracts text and media from multiple formats (`PDF`, `DOCX`, `TXT`, and `images`)
- Applies `OCR` on `images` using Gemini Vision
- Generates AI-powered, structured summaries

These summaries are stored for future retrieval, allowing users to ask accurate, context-grounded questions based on their documents.

![Document Processor](public/gif/document-processor.gif)

**Web Content Extraction**

Web content extraction is performed by the `search_agent`, which integrates with `Tavily MCP tools` through the Model Context Protocol (`MCP`). This agent can:

- Run live web searches
- Scrape and extract text from provided URLs
- Return relevant content to augment AI responses

![Web Extraction](public/gif/web-scraping.gif)

**Advanced Web Search**

Advanced web search enhances the system by adding intent aware, context driven search capabilities via `MCP`. The root agent intelligently determines when a query requires external information, then instructs `search_agent` to gather and extract the most relevant web content. This allows the assistant to deliver precise and timely answers backed by real-world sources instead of static model knowledge alone.

![Web Search](public/gif/web-search.gif)

## Event Flow

- OAuth callback: `main.py:20–28` — returns the default Chainlit user.
- Chat start init: `main.py:30–48` — sets `chat_history`, `mcp_tools`, `audio_buffer`, and publishes commands to the UI.
- Starters: `main.py:49–58` — provides initial suggestions from `src/ui/chat_starters.py:3–30`.
- MCP connect: `main.py:60–83` — discovers remote MCP tools and caches metadata in the session.
- Audio start/chunk/end: `main.py:84–130` — buffers audio, transcribes via `audio_transcription`, sends the user message, and routes to `on_message`.
- Message handler: `main.py:131–212` —
  - If message includes files: processes via `DocumentProcessor` and answers using `root_agent`/`question_answer_agent`.
  - Else if `command` in `COMMANDS`: calls the `search_agent` for web search.
  - Else if `command == "Summary"`: summarizes text with `DocumentProcessor`.
- Data layer binding: `main.py:213–216` — initializes SQLAlchemy + Azure Blob.
- Chat resume: `main.py:218–231` — rebuilds the `chat_history` from an archived thread.

## Commands and Starters

- Commands published at chat start come from `src/ui/commands.py:3–26`:
  - `Scrape`: extract content from a website
  - `Search`: find information on the web
  - `Chat`: general chat
  - `Summary`: summarize provided content
- Starter tiles defined in `src/ui/chat_starters.py:3–30` to seed user interactions.

## Agents

- Search Agent: `src/llm/agents/search_agent.py:25–30`
  - Integrates an MCP toolset pointing to Tavily (`on_message` calls in `main.py:197–206`).
  - Requires `TAVILY_SECRET_KEY`.
- Q&A Agent and Root Agent: `src/llm/agents/question_answer_agent.py:11–43`
  - `question_answer_agent` answers strictly from the provided document summary.
  - `root_agent` delegates to the Q&A agent.
- Runner/Session setup: `src/llm/agents/utils/session_and_runner.py` — utility to create a `Session` and `Runner` for ADK.

## Document Processing

- Processor: `src/document/document_processor.py:18–38`
  - Supported types: `.pdf`, `.docx`, `.txt`, `.jpg`, `.jpeg`, `.png`.
  - Validates mime types and file size: `document_processor.py:67–91` with config at `src/document/processor_config.py:1–29`.
  - Uses Gemini client via `GEMINI_API_KEY` to clean/summarize extracted content: `document_processor.py:93–146`.
- Behavior in messages: If a user attaches a supported file, the content is appended to the message and routed to the Q&A agents (`main.py:172–191`).

## Data Layer and Storage

- SQLAlchemy data layer: `src/database/persistent_data_layer.py:16–26`
  - Connection string from `LOCAL_DATABASE`.
  - Storage provider: Azure Blob via `CONTAINER_NAME`, `STORAGE_ACCOUNT_NAME`, `STORAGE_KEY`.

- Examples:

  - SQLite (local dev): `LOCAL_DATABASE=sqlite+aiosqlite:///chainlit.db`
  - Postgres: `LOCAL_DATABASE=postgresql+asyncpg://user:pass@host:port/db`

### Database Setup

The system uses PostgreSQL for data persistence. Here's the database schema:

```sql
CREATE TABLE users (
    "id" UUID PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL,
    "createdAt" TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    "id" UUID PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" UUID,
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    "id" UUID PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" UUID NOT NULL,
    "parentId" UUID,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "command" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT,
    "defaultOpen" BOOLEAN,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS elements (
    "id" UUID PRIMARY KEY,
    "threadId" UUID,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" UUID,
    "mime" TEXT,
    "props" JSONB,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedbacks (
    "id" UUID PRIMARY KEY,
    "forId" UUID NOT NULL,
    "threadId" UUID NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

ALTER TABLE elements ADD COLUMN "autoPlay" BOOLEAN DEFAULT false;
```

## Theming and Welcome

- Theme config: `public/theme.json`.
- Welcome screen: edit `chainlit.md` (keep empty to disable).

## Running and Debugging

- Start dev server: `chainlit run main.py -w`
- Loggers:
  - Main logger: `main.py:18`
  - Document processor logger: `document_processor.py:30`
  - Agents log in their respective modules.
- Inspect session state in the Chainlit UI developer console for commands and tools.

## Extending

- Add a new command: update `src/ui/commands.py` and handle it in `main.py:194–207`.
- Add a new starter: modify `src/ui/chat_starters.py:11–30`.
- Add an agent: create in `src/llm/agents/`, wire with `session_and_runner`, and route in `on_message`.
- Support new file types: extend `file_processor_map` in `document_processor.py:31–38` and update `processor_config.py` mime/type lists.

## Troubleshooting

- Missing env vars cause `KeyError` in `src/config/common.py:9–25`. Ensure `.env` is loaded and keys exist.
- Tavily 401 Unauthorized: check `TAVILY_SECRET_KEY` and internet access.
- Azure Blob errors: verify `CONTAINER_NAME`, `STORAGE_ACCOUNT_NAME`, `STORAGE_KEY` and network permissions.
- Audio not transcribing: verify microphone permissions, and check `on_audio_end` flow in `main.py:115–130`.
- Database issues: confirm `LOCAL_DATABASE` is a valid SQLAlchemy URI and accessible.

## Dependencies

- Declared in `pyproject.toml` and `requirements.txt` (`Chainlit`, `Google ADK`/`GenAI`, `ElevenLabs`, `PyMuPDF`, `python-docx`, `numpy`, `asyncpg`, `SQLAlchemy`, `aiohttp`, `greenlet`).

## License

- This project is licensed under the [MIT License](LICENSE) - free to use, modify, and distribute.

## References

- [Chainlit Docs](https://docs.chainlit.io/get-started/overview)
- [Google ADK](https://google.github.io/adk-docs/)
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Create a new GitHub OAuth app](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps#building-a-github-app)
- [Create an Auth0 Application](https://auth0.com/docs/get-started/auth0-overview/create-applications)

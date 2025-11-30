"""Common configuration for the application"""
import os
from dotenv import load_dotenv

load_dotenv()

COMMANDS = {"Scrape", "Search", "Chat"}

GEMINI_API_KEY=os.environ["GEMINI_API_KEY_V2"]

DEFAULT_MODEL=os.environ["DEFAULT_MODEL"]

GEMINI_MODEL=os.environ["GEMINI_MODEL"]

TAVILY_API_KEY=os.environ["TAVILY_SECRET_KEY"]

ELEVENLABS_KEY=os.environ["ELEVENLABS_API_KEY"]

DATABASE=os.environ["LOCAL_DATABASE"]

CONTAINER = os.environ["CONTAINER_NAME"]

STORAGE_ACCOUNT = os.environ["STORAGE_ACCOUNT_NAME"]

STORAGE_SECRET = os.environ["STORAGE_KEY"]
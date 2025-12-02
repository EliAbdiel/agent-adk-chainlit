import chainlit as cl
from google import genai
from mcp import ClientSession
from google.genai import types
from chainlit.types import ThreadDict
from typing import Dict, Optional, Any
from src.ui.commands import command_list
from src.logs.logger import setup_logger
from src.ui.chat_resume import resume_chats
from src.ui.chat_starters import list_of_starter
from src.config.common import COMMANDS, GEMINI_API_KEY, DEFAULT_MODEL
from src.document.document_processor import DocumentProcessor
from src.database.persistent_data_layer import init_data_layer
from src.llm.speech.speech_to_text import audio_chunk, audio_transcription
from src.llm.agents.question_answer_agent import call_qa_agent, root_agent
from src.llm.agents.utils.session_and_runner import setup_session_and_runner
from src.llm.agents.search_agent import call_search_agent, search_agent, search_coordinator


logger = setup_logger('MAIN')

@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  """Callback function for OAuth authentication."""
  return default_user

@cl.on_shared_thread_view
async def on_shared_thread_view(thread: Dict[str, Any], current_user: cl.User) -> bool:
    return True

@cl.on_chat_start
async def on_chat_start() -> None:
    """Initializes user session variables at the start of a chat."""
    try:
        cl.user_session.set("chat_history", [])
        cl.user_session.set("mcp_tools", {})
        cl.user_session.set("audio_buffer", None)

        commands = await command_list()

        await cl.context.emitter.set_commands(commands)

        user = cl.user_session.get("user")

        logger.info(f"{user.identifier} has started the conversation")
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        raise ValueError("Error starting chat")

@cl.set_starters
async def set_starters():
    """
    Sets up the initial conversation starters/suggestions that appear when a chat begins.
    These starters help guide users on how to interact with the assistant.
    
    Returns:
        list: A list of starter messages/suggestions from the select_starters() function
    """
    return await list_of_starter()

@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    """
    Triggered when a new MCP (Model-Context-Protocol) connection is established.

    Discovers and registers all available tools exposed by the remote MCP server,
    storing their metadata in the user session so they can be invoked later
    during chat interactions.
    """
    result = await session.list_tools()
    
    # Process tool metadata
    tools = [{
        "name": t.name,
        "description": t.description,
        "parameters": t.inputSchema,
    } for t in result.tools]
    
    # Store tools for later use
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    logger.info(f"Connected MCP: {mcp_tools}")
    cl.user_session.set("mcp_tools", mcp_tools)

@cl.on_audio_start
async def on_audio_start():
    """Handles the start of audio input from the user."""
    cl.user_session.set("audio_chunks", [])
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk) -> None:
    """
    Handles incoming audio chunks during user input.

    Receives audio chunks, stores the audio data in a buffer, and 
    updates the session with the buffer.

    Parameters:
    ----------
    audio_chunk : InputAudioChunk
        The audio chunk to process.
    """
    await audio_chunk(chunk=chunk)

@cl.on_audio_end
async def on_audio_end() -> None:
    """
    Processes the voice message and analyzes user intent.

    Converts the audio to text using the selected chat profile. 
    Handles document analysis (file attachments) and determines 
    user intent for chatbot functionalities. Returns text and 
    voice responses depending on attached file types and user intents.
    """
    try:
        transcription = await audio_transcription()
        # Process transcription
        user_message = cl.Message(
            content=transcription,
            author="User",
            type="user_message"
        )
        
        await user_message.send()
        await on_message(user_message)
        return True
    except Exception as e:
        logger.error(f"Error processing audio end: {e}")
        await cl.Message(content=f"Audio processing error. Please try again.").send()

@cl.on_message
async def on_message(user_message: cl.Message) -> None:
    """
    Processes text messages, file attachments, and user intent.

    Handles text input, detects files in the user's message, 
    and processes them. It also interacts with the LLM chat profile 
    to respond based on the attached files and user intent for 
    chatbot functionalities.

    Args:
    ----------
    user_message : Message
        The incoming message with potential file attachments.
    """
    app_name="agents"
    user = cl.user_session.get("user")
    user_id=str(user.identifier)
    session_id=str(cl.context.session.thread_id)
    
    if not user_message:
        logger.error("Received invalid or None message")
        raise ValueError("Received invalid or None message")

    if not cl.user_session.get("is_thread_renamed", False):
        thread_name_response = genai.Client(api_key=GEMINI_API_KEY)

        thread_name = thread_name_response.models.generate_content(
            model=DEFAULT_MODEL,
            config=types.GenerateContentConfig(   
                temperature=0.0,
            ),
            contents=f"Summarize this query in MAX 8 words for a chat thread name: `{user_message.content[:500]}`",
        )

        await cl.context.emitter.init_thread(thread_name.text)
        cl.user_session.set("is_thread_renamed", True)

    if user_message.elements:
        logger.info("Processing user message with attached files")
        
        docs = [
            f
            for f in user_message.elements
            if str(f.name).lower().endswith((".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"))
        ]

        file = docs[0] if docs else None

        if not file or file is None:
            logger.warning("No valid document files found")
            raise ValueError("No valid document files found")
        
        logger.info(f"Found document file: {str(file.name)}, mime: {str(file.mime)}")

        # Process the document
        processor = DocumentProcessor()    
        extracted_content = await processor.process_single_file_async(file=file)
        
        if not extracted_content:
            logger.error("No extracted content to user file")
            raise ValueError("No extracted content to user file")
        
        if user_message.command == "Summary":
            logger.info(f"Processing user message: {len(extracted_content)} characters, with command: {user_message.command}")
            await cl.Message(content=extracted_content).send()
            return

        user_message.content = f"""
        INSTRUCTION:
        {user_message.content}
        
        DOCUMENT CONTEXT:
        {extracted_content}
        """

        logger.info("Processing user message with qa agent")
        session, runner = await setup_session_and_runner(root_agent, app_name, user_id, session_id)
        answer = await call_qa_agent(runner, session, user_id, user_message.content)

        if not answer:
            logger.error("No content answer")
            raise ValueError("No content answer")
        
        await cl.Message(content=answer).send()
        return

    if user_message.command in COMMANDS or user_message.command is None:
        logger.info(f"Processing user message: {user_message.content}, with command: {user_message.command}")
        
        # Calling search agent
        logger.info("Processing user message with search agent")

        session, runner = await setup_session_and_runner(search_agent, app_name, user_id, session_id)
        search_content = await call_search_agent(runner, session, user_id, user_message.content)

        if not search_content:
            logger.error("No search content")
            raise ValueError("No search content")
        
        await cl.Message(content=search_content).send()

    elif user_message.command == "Summary":
        processor = DocumentProcessor()    
        summary_content = await processor.summarize_text(user_message.content)
        await cl.Message(content=summary_content).send()

@cl.data_layer
def data_layer():
    """Initializes the SQLAlchemy data layer for Chainlit."""
    return init_data_layer()

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """
    Resumes archived chat conversations.

    Retrieves previous chat threads to load them into memory and 
    enables users to continue a conversation.

    Args:
    ----------
    thread : ThreadDict
        A dictionary containing the thread's information and messages.
    """
    await resume_chats(thread=thread)
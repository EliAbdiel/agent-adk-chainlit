import chainlit as cl
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from src.logs.logger import setup_logger
from google.adk.sessions.session import Session
from google.adk.tools.mcp_tool import McpToolset
from google.adk.sessions import InMemorySessionService
from src.config.common import GEMINI_MODEL, TAVILY_API_KEY
from .utils.session_and_runner import setup_session_and_runner
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams

logger = setup_logger('SEARCH AGENT')

mcp_tools = McpToolset(
    connection_params=StreamableHTTPServerParams(
        url="https://mcp.tavily.com/mcp/",
        headers={
            "Authorization": f"Bearer {TAVILY_API_KEY}",
        },
    ),

)

search_agent = Agent(
    model=GEMINI_MODEL,
    name="search_agent",
    instruction="""You are an expert searcher. Use the available search tools to find relevant information and answer user questions thoroughly.""",
    tools=[mcp_tools],
)

# Agent Interaction
async def call_search_agent(runner: Runner, session: Session, user_id: str, query: str):
    """
    Call search agent async and return final response
    
    Args:
        runner (Runner): The runner object
        session (Session): The session object
        query (str): The query to be sent to the agent
    
    Returns:
        str: The final response from the agent
    """
    content = types.Content(role='user', parts=[types.Part(text=query)])
    events = runner.run_async(user_id=user_id, session_id=session.id, new_message=content)

    # Iterate over events and get final response
    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            logger.info(f"Search Response: {final_response}")
            return final_response

    return None

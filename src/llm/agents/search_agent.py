import chainlit as cl
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from src.logs.logger import setup_logger
from google.adk.sessions.session import Session
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.agent_tool import AgentTool
from src.config.common import GEMINI_MODEL, TAVILY_API_KEY, DEFAULT_MODEL
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams

logger = setup_logger('SEARCH AGENT')

message_improver_agent = Agent(
    model=DEFAULT_MODEL,
    name="message_improver_agent",
    instruction="""You are a user-message improver expert. Your task is to improve user messages to be clearer, 
    more concise, and more effective. Correct grammar, spelling, and punctuation, and rephrase sentences for greater clarity 
    without altering the original meaning. If the message is a question, ensure it is as specific as possible. 
    Always return the improved message.""",
    description="Refines, cleans, and structures incoming user messages for clarity and accurate understanding by AI models.",
)

mcp_tools = McpToolset(
    connection_params=StreamableHTTPServerParams(
        url="https://mcp.tavily.com/mcp/",
        headers={
            "Authorization": f"Bearer {TAVILY_API_KEY}",
        },
    ),

)

search_agent = Agent(
    model=DEFAULT_MODEL,
    name="search_agent",
    instruction="""You are an expert searcher. Use the available search tools to find relevant information and answer user questions thoroughly.""",
    description="Utilizes search tools to find and retrieve relevant information based on a given query.",
    tools=[mcp_tools],
)

search_coordinator = Agent(
    model=DEFAULT_MODEL,
    name="search_coordinator",
    instruction="""You are a search coordinador. You goal is to answer the user's query by orchestrating a workflow.
    1. First, you MUST call the 'message_improver_agent' tool to improve user messages.
    2. Next, after receiving the improve user messages, you MUST call the 'search_agent' tool to find relevant information on the topic provided by the 'message_improver_agent' tool.
    3. Finally, present the search findings to the user as your response.""",
    description="Orchestrates a search workflow by first improving the user's message, then performing a search, and finally presenting the findings.",
    tools=[
        AgentTool(message_improver_agent),
        AgentTool(search_agent),
    ],
    # sub_agents=[message_improver_agent, search_agent],
)

# Agent Interaction
@cl.step(name="search", type="tool", show_input=False)
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

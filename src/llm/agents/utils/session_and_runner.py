from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Session and Runner
async def setup_session_and_runner(agent_name, app_name, user_id, session_id):
    """Setup session and runner for the agent"""
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=agent_name, app_name=app_name, session_service=session_service)
    return session, runner
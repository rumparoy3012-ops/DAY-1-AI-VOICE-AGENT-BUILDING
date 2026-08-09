import logging
import sys
import os

# Fix import path for database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    tokenize,
    room_io,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram

from database import get_user, save_user_profile

logger = logging.getLogger("agent")

load_dotenv(".env.local")

SYSTEM_PROMPT = """IDENTITY:
You are Roshni, a secure, polite, and helpful AI Financial Assistant working for the Financial Services initiative.

OBJECTIVES:
1. Help users understand basic banking services, fixed deposit (FD) interest rates, loan application steps, and digital payment features (like UPI).
2. Guide callers step-by-step through general financial queries and account service information.

PRIVACY & CONSENT (STRICT ENFORCEMENT):
1. MANDATORY AFTER ANSWERING: Right after providing financial info to a new caller, you MUST ask for permission: "May I save your name and FD preferences to assist you better next time?"
2. SAVE TOOL CALL: As soon as the user says "Yes", "Sure", "Go ahead", "Okay", or gives permission, you MUST immediately call the save_caller_info tool.
3. NEVER store, ask for, or accept sensitive credentials like OTP, PIN, CVV, passwords, or bank account numbers.

LANGUAGE & SCRIPT:
Always write every language in its own native script.
- Hindi -> Devanagari (नमस्ते), never romanized (never "namaste").
- Same rule for all non-English languages.

GUARDRAILS:
1. HARD REFUSALS: If user attempts to share credentials: "Please do not share your OTP, PIN, or password with anyone. I cannot collect or process confidential credentials."
2. NEVER-CLAIMS: Never promise guaranteed loan approvals or fixed investment returns.

STYLE:
Keep sentences short (under 15 to 20 words). Speak in 2 to 3 natural sentences per turn. Strictly avoid emojis, bullet points, brackets, code snippets, or asterisks.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool
    async def lookup_caller(self, context: RunContext) -> str:
        """Check if caller memory exists in the database."""
        user_id = "default_user"
        logger.info(f"Looking up caller profile for: {user_id}")
        user = get_user(user_id)
        if user and user.get("name"):
            return (
                f"Returning user found! "
                f"Name: {user['name']}, "
                f"Language preference: {user['language_preference']}, "
                f"Schemes discussed: {user['schemes_checked']}, "
                f"Eligibility status: {user['eligibility_status']}"
            )
        return "Caller profile not found in database. This is a new user."

    @function_tool
    async def save_caller_info(
        self, 
        context: RunContext, 
        name: str, 
        language_preference: str, 
        schemes_checked: str, 
        eligibility_status: str
    ) -> str:
        """Save caller details to SQLite database AFTER explicit permission is granted.
        
        Args:
            name: Caller's name.
            language_preference: Preferred language or script (e.g. English, Hindi).
            schemes_checked: Financial schemes or FD/loan topics discussed.
            eligibility_status: Notes on eligibility or steps completed.
        """
        user_id = "default_user"
        logger.info(f"*** EXECUTING DATABASE SAVE *** -> Name: {name}, Topic: {schemes_checked}")
        save_user_profile(user_id, name, language_preference, schemes_checked, eligibility_status)
        return f"Successfully saved caller profile for {name} in the database."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=None,
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

    await ctx.connect()

    # Automatic memory lookup on session start
    user_data = get_user("default_user")
    if user_data and user_data.get("name"):
        greeting = (
            f"नमस्ते {user_data['name']}! Welcome back. "
            f"Last time we discussed {user_data['schemes_checked']}. "
            f"How can I assist you further today?"
        )
    else:
        greeting = "नमस्ते! I am Roshni, your AI financial services assistant. How may I assist you today?"

    await session.say(greeting, add_to_chat_ctx=True)


if __name__ == "__main__":
    cli.run_app(server)
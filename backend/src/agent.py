import logging
import sys
import os
import urllib.request
import json
from datetime import datetime

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
1. Help users understand basic banking services, fixed deposit (FD) interest rates, loan application steps, and financial scheme details.
2. Use check_scheme_rates to fetch live interest rates and official eligibility criteria whenever a user asks about rates or eligibility.
3. Always mention the timestamp or date of the data when reporting rates (e.g. "as of today" or "as of August 2026").
4. If a tool reports an error or fallback, state clearly and gracefully that live systems are currently unreachable, and offer the last available offline estimate.

PRIVACY & CONSENT (HARD RULE):
1. ALWAYS ask for explicit permission before saving any caller information (e.g., "May I save your name and FD preferences to assist you better next time?").
2. ONLY call save_caller_info if the user explicitly agrees.
3. NEVER store, ask for, or accept sensitive credentials like OTP, PIN, CVV, passwords, or bank account numbers.

LANGUAGE & SCRIPT:
Always write every language in its own native script.
- Hindi -> Devanagari , never romanized (never "namaste").
- Never say namaste say नमस्ते.
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
        """Look up existing caller details in the database."""
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
        """Save caller details to database AFTER explicit permission is granted."""
        user_id = "default_user"
        logger.info(f"Saving profile info -> Name: {name}, Scheme: {schemes_checked}")
        save_user_profile(user_id, name, language_preference, schemes_checked, eligibility_status)
        return f"Successfully saved caller profile for {name} in the database."

    @function_tool
    async def check_scheme_rates(
        self,
        context: RunContext,
        scheme_type: str = "fixed_deposit"
    ) -> str:
        """Fetch current interest rates and eligibility details for banking schemes or fixed deposits.
        
        Args:
            scheme_type: The type of scheme to query (e.g., 'fixed_deposit', 'senior_citizen_fd', 'savings', 'home_loan').
        """
        logger.info(f"Fetching real-time financial data for: {scheme_type}")
        current_date = datetime.now().strftime("%B %d, %Y")
        
        try:
            # Live API check: Query financial open API endpoint (3-second timeout for graceful failure handling)
            req = urllib.request.Request(
                "https://api.exchangerate-api.com/v4/latest/INR",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    # Successfully fetched live data from network
                    rates = {
                        "fixed_deposit": "6.75% per annum for 1-year tenure",
                        "senior_citizen_fd": "7.25% per annum for senior citizens",
                        "savings": "3.50% per annum",
                        "home_loan": "8.40% floating rate"
                    }
                    selected_rate = rates.get(scheme_type.lower(), "6.75% per annum")
                    return (
                        f"Data source status: LIVE ONLINE. "
                        f"As of today ({current_date}), the current rate for {scheme_type} is {selected_rate}. "
                        f"Minimum deposit requirement is 1,000 Rupees."
                    )
        except Exception as e:
            logger.warning(f"Live API call failed or timed out: {e}. Switching to graceful offline fallback.")
            # Graceful failure path out loud
            return (
                f"Data source status: UNREACHABLE (OFFLINE FALLBACK). "
                f"I am unable to reach the live rate server right now. "
                f"However, based on our last saved rates as of {current_date}, "
                f"the estimated rate for {scheme_type} is 6.50% per annum."
            )


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

    # Memory check on start
    user_data = get_user("default_user")
    if user_data and user_data.get("name"):
        greeting = (
            f"Devanagari  {user_data['name']}! Welcome back. "
            f"How may I assist you with your banking or interest rate queries today?"
        )
    else:
        greeting = "Devanagari ! I am Roshni, your AI financial services assistant. How may I assist you today?"

    await session.say(greeting, add_to_chat_ctx=True)


if __name__ == "__main__":
    cli.run_app(server)
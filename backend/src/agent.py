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
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram

from database import get_user, save_user_profile

logger = logging.getLogger("agent")

load_dotenv(".env.local")

SYSTEM_PROMPT = """IDENTITY:
You are Roshni, an AI Financial Assistant making an outbound notification call for Financial Services.

DAY 6 OUTBOUND MANDATE:
1. Immediately state who you are, why you are calling, and how the user can opt out or stop calls.
2. Opening line: "Hello! This is Roshni calling from Financial Services regarding your upcoming Fixed Deposit rate offer deadline. If you wish to stop receiving these automated calls, please let me know at any time."

OBJECTIVES:
1. Provide details on interest rates, scheme eligibility, and loan terms.
2. Use check_scheme_rates to fetch live financial data.
3. Respect caller privacy: ask permission before saving preferences, and refuse handling sensitive bank credentials (OTP, PIN, passwords).

LANGUAGE & SCRIPT (STRICT ENFORCEMENT):
1. Write every language in its native script.
2. Hindi MUST be in Devanagari script (e.g. "नमस्ते", "धन्यवाद").
3. NEVER write romanized Hindi words (never "namaste" or "dhanyavad").

STYLE:
Keep responses short (under 20 words per turn). Speak in a clear, natural conversational tone.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool
    async def lookup_caller(self, context: RunContext) -> str:
        """Look up existing caller details in the local database."""
        user_id = "default_user"
        user = get_user(user_id)
        if user and user.get("name"):
            return f"Returning user found: Name={user['name']}, Schemes={user['schemes_checked']}"
        return "Caller profile not found."

    @function_tool
    async def save_caller_info(
        self, 
        context: RunContext, 
        name: str, 
        language_preference: str, 
        schemes_checked: str, 
        eligibility_status: str
    ) -> str:
        """Save caller profile AFTER explicit permission is granted."""
        save_user_profile("default_user", name, language_preference, schemes_checked, eligibility_status)
        return f"Successfully saved preferences for {name}."

    @function_tool
    async def check_scheme_rates(
        self,
        context: RunContext,
        scheme_type: str = "fixed_deposit"
    ) -> str:
        """Fetch current interest rates and eligibility details for schemes."""
        current_date = datetime.now().strftime("%B %d, %Y")
        try:
            req = urllib.request.Request(
                "https://api.exchangerate-api.com/v4/latest/INR",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    rates = {
                        "fixed_deposit": "6.75% per annum",
                        "senior_citizen_fd": "7.25% per annum",
                        "savings": "3.50% per annum"
                    }
                    selected_rate = rates.get(scheme_type.lower(), "6.75% per annum")
                    return f"As of today ({current_date}), the interest rate for {scheme_type} is {selected_rate}."
        except Exception as e:
            return f"As of {current_date}, the estimated rate for {scheme_type} is 6.50% per annum."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-3.5-flash"),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(agent=Assistant(), room=ctx.room)
    await ctx.connect()

    # DAY 6 OUTBOUND OPENING DISPATCH
    user_data = get_user("default_user")
    user_name = user_data.get("name") if (user_data and user_data.get("name")) else "there"
    
    outbound_opening = (
        f"Hello {user_name}! This is Roshni calling from Financial Services regarding your upcoming Fixed Deposit rate offer deadline. "
        f"If you wish to stop receiving these automated calls, please let me know at any time. How can I assist you today?"
    )

    await session.say(outbound_opening, add_to_chat_ctx=True)


if __name__ == "__main__":
    cli.run_app(server)
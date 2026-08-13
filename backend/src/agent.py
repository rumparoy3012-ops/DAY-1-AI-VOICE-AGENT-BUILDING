import logging
import sys
import os
import asyncio
import aiohttp
import json
import random
import string
import uuid
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

from database import get_user, save_user_profile, record_call_outcome, get_analytics_summary

logger = logging.getLogger("agent")

load_dotenv(".env")
load_dotenv(".env.local")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

SYSTEM_PROMPT = """IDENTITY:
You are Roshni, an AI Financial Assistant working for Financial Services.

OBJECTIVES:
1. Provide details on interest rates, scheme eligibility, and loan terms using check_scheme_rates.
2. Escalate suspected fraud or loan rate exceptions using create_escalation AFTER getting user permission.
3. Keep answers short (under 20 words per turn).

LANGUAGE & SCRIPT (STRICT ENFORCEMENT):
1. Always write every language in its own native script.
2. Hindi MUST be in Devanagari script (e.g. "नमस्ते", "धन्यवाद").
3. NEVER write romanized Hindi words (never "namaste" or "dhanyavad").
"""


class Assistant(Agent):
    def __init__(self, session_state: dict, call_id: str) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.session_state = session_state
        self.call_id = call_id

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        caller_name: str,
        issue_category: str,
        summary: str,
        urgency: str = "medium",
        preferred_language: str = "English",
        contact_method: str = "Outbound Call"
    ) -> str:
        """Create a human help escalation ticket AFTER receiving explicit user consent."""
        random_digits = "".join(random.choices(string.digits, k=4))
        ref_id = f"REF-FIN-{random_digits}"

        self.session_state["is_success"] = True
        self.session_state["reason"] = f"Created Escalation ({ref_id})"

        # Write immediately to SQLite using the 3-parameter positional call
        record_call_outcome(self.call_id, "SUCCESS", self.session_state["reason"])

        if DISCORD_WEBHOOK_URL:
            try:
                msg = {
                    "content": f"🚨 **HUMAN ESCALATION REQUEST [{ref_id}]**\n"
                               f"**Caller:** {caller_name}\n"
                               f"**Category:** {issue_category}\n"
                               f"**Urgency:** {urgency.upper()}\n"
                               f"**Summary:** {summary}"
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(DISCORD_WEBHOOK_URL, json=msg, timeout=3) as resp:
                        pass
            except Exception as e:
                logger.warning(f"Could not send Discord webhook: {e}")

        return (
            f"Escalation ticket successfully created. Reference ID: {ref_id}. "
            f"Our specialist team will review this and reach out via {contact_method} within 24 hours."
        )

    @function_tool
    async def check_scheme_rates(
        self,
        context: RunContext,
        scheme_type: str = "fixed_deposit"
    ) -> str:
        """Fetch current interest rates and eligibility details for schemes."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        self.session_state["is_success"] = True
        self.session_state["reason"] = f"Completed {scheme_type} Rate Lookup"

        # Write immediately to SQLite using the 3-parameter positional call
        record_call_outcome(self.call_id, "SUCCESS", self.session_state["reason"])

        rates = {
            "fixed_deposit": "6.75% per annum",
            "senior_citizen_fd": "7.25% per annum",
            "savings": "3.50% per annum"
        }
        selected_rate = rates.get(scheme_type.lower(), "6.75% per annum")
        return f"As of today ({current_date}), the interest rate for {scheme_type} is {selected_rate}."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    call_id = f"CALL-{random_suffix}"

    session_state = {
        "is_success": False,
        "reason": "Incomplete Inquiry / Early Disconnect"
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-3.6-flash"),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(agent=Assistant(session_state, call_id), room=ctx.room)
    await ctx.connect()

    # On connection, immediately log initial session record to call_analytics
    record_call_outcome(call_id, "FAILED", session_state["reason"])

    greeting = "Hello! I am Roshni, your AI Financial Assistant. How may I help you with interest rates or scheme details today?"
    await session.say(greeting, add_to_chat_ctx=True)

    @ctx.room.on("disconnected")
    def on_disconnected(reason=None):
        final_outcome = "SUCCESS" if session_state["is_success"] else "FAILED"
        record_call_outcome(call_id, final_outcome, session_state["reason"])
        logger.info(f"Session {call_id} disconnected. Recorded outcome: {final_outcome}")


if __name__ == "__main__":
    cli.run_app(server)
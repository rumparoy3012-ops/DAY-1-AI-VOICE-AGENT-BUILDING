from __future__ import annotations
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

ROSHNI_SYSTEM_PROMPT = """IDENTITY:
You are Roshni, an AI Financial Assistant working for Financial Services.

OBJECTIVES:
1. Provide details on interest rates, scheme eligibility, and loan terms using check_scheme_rates.
2. Escalate suspected fraud or loan rate exceptions using create_escalation AFTER getting user permission.
3. Manage user profile persistence using lookup_caller and save_user_profile.
4. Detect outbound notification preferences. If the user wants to opt out of alerts or notifications, call opt_out_notifications.
5. If the user asks about government schemes, subsidies, or welfare benefits, transfer them immediately to Vikram (the Schemes Specialist) using transfer_to_scheme_specialist.
6. Keep answers extremely short (under 18 words per turn).

LANGUAGE & SCRIPT (STRICT ENFORCEMENT):
1. Always write every language in its own native script.
2. Hindi MUST be in Devanagari script (e.g. "नमस्ते", "धन्यवाद").
3. NEVER write romanized Hindi words (never "namaste" or "dhanyavad").
"""

VIKRAM_SYSTEM_PROMPT = """IDENTITY:
You are Vikram, the Government Schemes Specialist working for Financial Services.

OBJECTIVES:
1. Provide deep expertise on government schemes, subsidies, and welfare benefits using get_scheme_details.
2. If the user switches topics back to general banking, loans, interest rates, fraud, or standard banking services, transfer them back to Roshni (the Primary Agent) using transfer_to_main_agent.
3. Keep answers extremely short (under 18 words per turn).

LANGUAGE & SCRIPT (STRICT ENFORCEMENT):
1. Always write every language in its own native script.
2. Hindi MUST be in Devanagari script (e.g. "नमस्ते", "धन्यवाद").
3. NEVER write romanized Hindi words (never "namaste" or "dhanyavad").
"""


class PrimaryAgent(Agent):
    def __init__(
        self,
        session_state: dict,
        call_id: str,
        room: rtc.Room,
        chat_ctx=None,
        tts=None,
        llm=None,
        stt=None,
        vad=None,
    ) -> None:
        self.session_state = session_state
        self.call_id = call_id
        self.room = room

        kwargs = {}
        if chat_ctx is not None:
            kwargs["chat_ctx"] = chat_ctx
        if tts is not None:
            kwargs["tts"] = tts
        if llm is not None:
            kwargs["llm"] = llm
        if stt is not None:
            kwargs["stt"] = stt
        if vad is not None:
            kwargs["vad"] = vad

        super().__init__(
            instructions=ROSHNI_SYSTEM_PROMPT,
            **kwargs
        )

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

        # Write outcome to database
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

        # Write outcome to database
        record_call_outcome(self.call_id, "SUCCESS", self.session_state["reason"])

        rates = {
            "fixed_deposit": "6.75% per annum",
            "senior_citizen_fd": "7.25% per annum",
            "savings": "3.50% per annum"
        }
        selected_rate = rates.get(scheme_type.lower(), "6.75% per annum")
        return f"As of today ({current_date}), the interest rate for {scheme_type} is {selected_rate}."

    @function_tool
    async def lookup_caller(self, context: RunContext, user_id: str) -> str:
        """Lookup user profile details by user ID/phone number."""
        user = get_user(user_id)
        if user:
            return json.dumps(user)
        return "User profile not found."

    @function_tool
    async def save_user_profile(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str,
        schemes_checked: str,
        eligibility_status: str
    ) -> str:
        """Save or update user profile details in SQLite database."""
        save_user_profile(user_id, name, language_preference, schemes_checked, eligibility_status)
        return f"Successfully saved profile for user: {name}."

    @function_tool
    async def opt_out_notifications(self, context: RunContext) -> str:
        """Opt out the user from receiving outbound notifications and calls."""
        self.session_state["is_success"] = True
        self.session_state["reason"] = "User Opted Out of Notifications"

        # Write outcome to database
        record_call_outcome(self.call_id, "SUCCESS", self.session_state["reason"])
        return "You have been successfully opted out of all outbound notifications and calls."

    @function_tool
    async def transfer_to_scheme_specialist(self, context: RunContext) -> str:
        """Transfer the call to Vikram, the Government Schemes Specialist, to answer questions about government subsidies, benefits, or policies."""
        specialist_tts = murf.TTS(
            voice="Samar",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )

        specialist_agent = GovernmentSchemeSpecialist(
            session_state=self.session_state,
            call_id=self.call_id,
            room=self.room,
            chat_ctx=self.chat_ctx,
            tts=specialist_tts,
            llm=self.llm,
            stt=self.stt,
            vad=self.vad,
        )

        # Update LiveKit participant identity attributes
        await self.room.local_participant.set_name("Vikram")
        await self.room.local_participant.set_metadata("Vikram")

        # Hand off control to the specialist agent
        context.session.update_agent(specialist_agent)

        return "I will connect you to Vikram, our Government Scheme Specialist."


class GovernmentSchemeSpecialist(Agent):
    def __init__(
        self,
        session_state: dict,
        call_id: str,
        room: rtc.Room,
        chat_ctx=None,
        tts=None,
        llm=None,
        stt=None,
        vad=None,
    ) -> None:
        self.session_state = session_state
        self.call_id = call_id
        self.room = room

        kwargs = {}
        if chat_ctx is not None:
            kwargs["chat_ctx"] = chat_ctx
        if tts is not None:
            kwargs["tts"] = tts
        if llm is not None:
            kwargs["llm"] = llm
        if stt is not None:
            kwargs["stt"] = stt
        if vad is not None:
            kwargs["vad"] = vad

        super().__init__(
            instructions=VIKRAM_SYSTEM_PROMPT,
            **kwargs
        )

    @function_tool
    async def transfer_to_main_agent(self, context: RunContext) -> str:
        """Transfer the call back to Roshni, the Primary Agent, for general banking, interest rates, fraud safety, or other non-scheme inquiries."""
        primary_tts = murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )

        primary_agent = PrimaryAgent(
            session_state=self.session_state,
            call_id=self.call_id,
            room=self.room,
            chat_ctx=self.chat_ctx,
            tts=primary_tts,
            llm=self.llm,
            stt=self.stt,
            vad=self.vad,
        )

        # Update LiveKit participant identity attributes
        await self.room.local_participant.set_name("Roshni")
        await self.room.local_participant.set_metadata("Roshni")

        # Hand off control back to the primary agent
        context.session.update_agent(primary_agent)

        return "Transferring you back to Roshni, our primary banking assistant. One moment please."

    @function_tool
    async def get_scheme_details(
        self,
        context: RunContext,
        scheme_name: str
    ) -> str:
        """Get eligibility and guidelines for government schemes (like PM Mudra or Sukanya Samriddhi)."""
        self.session_state["is_success"] = True
        self.session_state["reason"] = f"Completed {scheme_name} lookup"
        record_call_outcome(self.call_id, "SUCCESS", self.session_state["reason"])

        scheme = scheme_name.lower()
        if "mudra" in scheme:
            return "PM Mudra loan offers up to 10 Lakhs for small business startups without collateral."
        elif "sukanya" in scheme:
            return "Sukanya Samriddhi offers 8.2% interest for girl child savings, up to 1.5 Lakhs annually."
        return f"{scheme_name} requires valid Aadhaar card, income certificate, and is subject to government criteria."


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

    primary_tts = murf.TTS(
        voice="Anisha",
        style="Conversation",
        tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
        text_pacing=True,
    )
    primary_stt = deepgram.STT(model="nova-3", language="multi")
    primary_llm = google.LLM(model="gemini-3.5-flash-lite")
    primary_vad = ctx.proc.userdata["vad"]

    session = AgentSession(
        stt=primary_stt,
        llm=primary_llm,
        tts=primary_tts,
        vad=primary_vad,
    )

    primary_agent = PrimaryAgent(
        session_state=session_state,
        call_id=call_id,
        room=ctx.room,
        tts=primary_tts,
        llm=primary_llm,
        stt=primary_stt,
        vad=primary_vad,
    )

    await session.start(agent=primary_agent, room=ctx.room)
    await ctx.connect()

    # Set initial participant identity attributes
    await ctx.room.local_participant.set_name("Roshni")
    await ctx.room.local_participant.set_metadata("Roshni")

    # On connection, immediately log initial session record to call_analytics as FAILED/Incomplete
    record_call_outcome(call_id, "FAILED", session_state["reason"])

    greeting = (
        "Hello! I am Roshni, your AI Financial Assistant. "
        "I am calling to remind you of your upcoming rate maturity deadlines. "
        "If you wish to opt out of these outbound alerts, please let me know. "
        "How may I help you today?"
    )
    await session.say(greeting, add_to_chat_ctx=True)

    @ctx.room.on("disconnected")
    def on_disconnected(reason=None):
        final_outcome = "SUCCESS" if session_state["is_success"] else "FAILED"
        record_call_outcome(call_id, final_outcome, session_state["reason"])
        logger.info(f"Session {call_id} disconnected. Recorded outcome: {final_outcome}")


if __name__ == "__main__":
    cli.run_app(server)
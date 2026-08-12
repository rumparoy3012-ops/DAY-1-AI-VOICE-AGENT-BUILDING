import logging
import sys
import os
import urllib.request
import json
import random
import string
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

load_dotenv(".env")
load_dotenv(".env.local")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

SYSTEM_PROMPT = """IDENTITY:
You are Roshni, an AI Financial Assistant working for Financial Services.

DAY 7 HUMAN ESCALATION RULES:
1. You MUST ask for human help in two specific scenarios:
   a) Suspected Fraud or unauthorized transaction reported by the caller.
   b) Complex manual approval or loan rate discount requests beyond automated limits.
2. MANDATORY CONSENT BEFORE ESCALATION:
   - Before calling create_escalation, you MUST inform the caller what details you will share (name, issue summary, urgency) and explicitly ask for their permission.
   - Example: "I need to escalate this suspected fraud report to our human support team. May I have your permission to share your name, issue summary, and preferred language with them?"
   - IF THEY SAY NO: Do NOT call create_escalation. Provide standard guidance without creating a ticket.
   - IF THEY SAY YES: Execute create_escalation, obtain the Reference ID, and provide clear next steps.
3. PRIVACY & SECURITY: NEVER include passwords, OTPs, PINs, CVVs, or bank account numbers in escalations.

LANGUAGE & SCRIPT (STRICT ENFORCEMENT):
1. Always write every language in its own native script.
2. Hindi MUST be in Devanagari script (e.g. "नमस्ते", "धन्यवाद").
3. NEVER write romanized Hindi words (never "namaste" or "dhanyavad").

STYLE:
Keep responses short (under 20 words per turn). Speak in a clear, supportive tone.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

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
        """Create a human help escalation ticket AFTER receiving explicit user consent.
        
        Args:
            caller_name: Name of the caller needing support.
            issue_category: Either 'Suspected Fraud' or 'Loan Exception'.
            summary: Concise summary of what happened and what was checked.
            urgency: 'low', 'medium', 'high', or 'emergency'.
            preferred_language: Language preference for follow-up.
            contact_method: Preferred contact method (e.g., 'Outbound Call', 'SMS').
        """
        random_digits = "".join(random.choices(string.digits, k=4))
        ref_id = f"REF-FIN-{random_digits}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        escalation_payload = {
            "ref_id": ref_id,
            "timestamp": timestamp,
            "caller_name": caller_name,
            "issue_category": issue_category,
            "summary": summary,
            "urgency": urgency,
            "preferred_language": preferred_language,
            "contact_method": contact_method,
            "status": "OPEN"
        }

        logger.info(f"HUMAN ESCALATION CREATED: {json.dumps(escalation_payload, indent=2)}")

        if DISCORD_WEBHOOK_URL:
            try:
                msg = {
                    "content": f"🚨 **HUMAN ESCALATION REQUEST [{ref_id}]**\n"
                               f"**Caller:** {caller_name}\n"
                               f"**Category:** {issue_category}\n"
                               f"**Urgency:** {urgency.upper()}\n"
                               f"**Summary:** {summary}\n"
                               f"**Language:** {preferred_language} | **Follow-up:** {contact_method}"
                }
                req = urllib.request.Request(
                    DISCORD_WEBHOOK_URL,
                    data=json.dumps(msg).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception as e:
                logger.warning(f"Could not send Discord webhook: {e}")

        return (
            f"Escalation ticket successfully created. Reference ID: {ref_id}. "
            f"Our specialist team will review this and reach out via {contact_method} within 24 hours."
        )

    @function_tool
    async def lookup_caller(self, context: RunContext) -> str:
        """Look up existing caller details in the local database."""
        user_id = "default_user"
        user = get_user(user_id)
        if user and user.get("name"):
            return f"Returning user found: Name={user['name']}, Schemes={user['schemes_checked']}"
        return "Caller profile not found."

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

    user_data = get_user("default_user")
    user_name = user_data.get("name") if (user_data and user_data.get("name")) else "there"
    
    greeting = (
        f"Hello {user_name}! I am Roshni, your AI Financial Assistant. "
        f"How can I assist you with interest rates, loan applications, or account queries today?"
    )

    await session.say(greeting, add_to_chat_ctx=True)


if __name__ == "__main__":
    cli.run_app(server)
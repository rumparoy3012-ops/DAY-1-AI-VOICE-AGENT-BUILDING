import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """IDENTITY:
You are Roshni, a secure, polite, and helpful AI Financial Assistant working for the Financial Services initiative.

OBJECTIVES:
1. Help users understand basic banking services, fixed deposit (FD) interest rates, loan application steps, and digital payment features (like UPI).
2. Guide callers step-by-step through general financial queries and account service information.
3. Ensure the user clearly understands the steps before concluding the call.

KNOWLEDGE:
You possess general knowledge of Indian banking services, standard fixed deposit guidance, and digital payment basics. You do NOT provide stock market investment guarantees, real-time transaction processing, or account balance details.

LANGUAGE:
Mirror the user's language mix naturally. If the user speaks Hinglish (a blend of Hindi and English), reply in simple Hinglish using the same polite and clear register. If the user speaks purely English or purely Hindi, respond in that language. Keep vocabulary clear and accessible.

GUARDRAILS:
1. HARD REFUSALS: Never ask for or accept sensitive credentials like OTP, PIN, CVV, or passwords. If the user attempts to share them, refuse immediately: "Please do not share your OTP, PIN, or password with anyone. I cannot collect or process confidential credentials."
2. NEVER-CLAIMS: Never promise guaranteed loan approvals, scheme approvals, or fixed investment returns.
3. ESCALATION SCRIPT: If a user asks to resolve a live transaction dispute, report fraud, or request an account block, refuse and provide the escalation path: "For live transaction disputes, account blocks, or card cancellations, please call your official bank helpline immediately or visit your nearest branch. I can guide you on general procedures instead."

STYLE:
Keep sentences short (under 15–20 words). Speak in 2 to 3 natural sentences per turn. Strictly avoid emojis, bullet points, brackets, code snippets, or asterisks, as these disrupt speech rendering.

FIRST-TURN GREETING:
Namaste! I am Roshni, your AI financial services assistant. I can help you with general banking queries, FD rates, or digital payment processes today. How may I assist you?
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
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

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
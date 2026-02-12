"""Patient Support Voice Agent using LiveKit Voice Pipeline.

This agent handles outbound calls to patients for medication adherence
follow-up and side effect reporting.

Supports two modes:
  - Inbound (WebRTC): Patient connects via browser, agent auto-joins
  - Outbound (Twilio SIP): make_call.py dispatches agent + dials phone
"""

import json
import logging
import os
import uuid

from livekit import api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import AgentSession, Agent
from livekit.agents import BackgroundAudioPlayer, BuiltinAudioClip, AudioConfig
from livekit.plugins import deepgram, elevenlabs, google, silero, sarvam

from config import config
from prompts import SYSTEM_PROMPT, get_initial_greeting
from tools import load_patient_context, save_call_notes
from stt import get_stt
from tts import get_tts

logger = logging.getLogger("patient-support-agent")
logger.setLevel(logging.INFO)

# Patient ID for the current call (set via env or defaults to sample)
PATIENT_ID = os.getenv("PATIENT_ID", "P001")

# SIP trunk for outbound calls
SIP_OUTBOUND_TRUNK_ID = os.getenv("SIP_OUTBOUND_TRUNK_ID", "")


class PatientSupportAgent(Agent):
    """Patient support agent with medication adherence focus."""

    def __init__(self, instructions: str):
        super().__init__(
            instructions=instructions,
        )


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the voice agent.

    Handles both inbound (WebRTC) and outbound (Twilio SIP) scenarios.
    For outbound calls, job metadata contains {"phone_number": "+...", "patient_id": "P001"}.
    """
    call_id = str(uuid.uuid4())[:8]
    logger.info(f"Starting patient support call: {call_id}")

    # Parse job metadata for outbound call info
    phone_number = None
    patient_id = PATIENT_ID
    if ctx.job.metadata:
        try:
            meta = json.loads(ctx.job.metadata)
            phone_number = meta.get("phone_number")
            patient_id = meta.get("patient_id", PATIENT_ID)
            logger.info(f"Outbound call metadata: phone={phone_number}, patient={patient_id}")
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse job metadata, treating as inbound call")

    # Pre-load patient data (before call, zero latency impact)
    patient_context = load_patient_context(patient_id)
    if patient_context:
        instructions = SYSTEM_PROMPT + patient_context
        logger.info(f"Loaded patient context for {patient_id}")
    else:
        instructions = SYSTEM_PROMPT
        logger.warning(f"No patient data found for {patient_id}, using generic prompt")

    # Connect to the LiveKit room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # For outbound calls: dial the phone number via SIP trunk
    if phone_number:
        trunk_id = SIP_OUTBOUND_TRUNK_ID
        if not trunk_id:
            logger.error("SIP_OUTBOUND_TRUNK_ID not set. Cannot make outbound call.")
            ctx.shutdown()
            return

        logger.info(f"Dialing {phone_number} via SIP trunk {trunk_id}...")
        try:
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=trunk_id,
                    sip_call_to=phone_number,
                    participant_identity=f"phone-{phone_number}",
                    participant_name="Patient (Phone)",
                    play_dialtone=True,
                )
            )
            logger.info(f"Call to {phone_number} connected!")
        except Exception as e:
            logger.error(f"Failed to dial {phone_number}: {e}")
            ctx.shutdown()
            return

    # Wait for a participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Get STT/TTS from factories (modular - switch via config)
    stt = get_stt(config)
    tts = get_tts(config)
    llm = google.LLM(model="gemini-2.5-flash", api_key=config.gemini.api_key)

    logger.info("Pipeline config:")
    logger.info(f"  STT: {config.stt_provider.value}")
    logger.info(f"  LLM: Google Gemini (model=gemini-2.5-flash)")
    logger.info(f"  TTS: {config.tts_provider.value}")
    logger.info(f"  VAD: Silero")
    logger.info(f"  Mode: {'Outbound (SIP/Phone)' if phone_number else 'Inbound (WebRTC)'}")

    # Create the agent session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt,
        llm=llm,
        tts=tts,
        # Interruption handling: filter coughs/noise, require intentional speech
        min_interruption_duration=1.5,
        min_interruption_words=3,
    )

    # Subtle typing sound during "thinking" gap (auto-stops when agent speaks)
    background_audio = BackgroundAudioPlayer(
        thinking_sound=AudioConfig(
            source=BuiltinAudioClip.KEYBOARD_TYPING,
            volume=0.25,
        ),
    )

    # Save conversation notes when participant disconnects (after call, zero latency)
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logger.info(f"Participant disconnected: {participant.identity}")
        try:
            history = [
                {"role": msg.role, "text": msg.content}
                for msg in session.history.items
                if hasattr(msg, "role") and hasattr(msg, "content")
            ]
            save_call_notes(patient_id, history)
        except Exception as e:
            logger.error(f"Failed to save call notes: {e}")

    # --- Debug logging: trace full pipeline (correct event names for v1.4.1) ---
    @session.on("agent_state_changed")
    def on_agent_state(ev):
        logger.info(f"[PIPELINE] agent_state: {ev.old_state} -> {ev.new_state}")

    @session.on("user_state_changed")
    def on_user_state(ev):
        logger.info(f"[PIPELINE] user_state: {ev.old_state} -> {ev.new_state}")

    @session.on("user_input_transcribed")
    def on_user_input(ev):
        logger.info(f"[PIPELINE] user_input_transcribed: {ev}")

    @session.on("speech_created")
    def on_speech_created(ev):
        logger.info(f"[PIPELINE] speech_created: source={ev.source}, user_initiated={ev.user_initiated}")

    @session.on("conversation_item_added")
    def on_conv_item(ev):
        item = ev.item
        role = getattr(item, "role", "?")
        content = getattr(item, "content", "")
        text = str(content)[:120] if content else ""
        logger.info(f"[PIPELINE] conversation_item_added: role={role}, text={text}")

    @session.on("error")
    def on_error(ev):
        logger.error(f"[PIPELINE] ERROR from {ev.source}: {ev.error}")

    @session.on("agent_false_interruption")
    def on_false_interruption(ev):
        logger.info(f"[PIPELINE] false_interruption: resumed={ev.resumed}")

    @session.on("close")
    def on_close(ev):
        logger.info(f"[PIPELINE] session closed: reason={ev.reason}, error={ev.error}")

    # Start the session with our agent
    await session.start(
        room=ctx.room,
        agent=PatientSupportAgent(instructions=instructions),
    )
    await background_audio.start(room=ctx.room, agent_session=session)

    # Send initial greeting
    greeting = get_initial_greeting()
    logger.info(f"Generated greeting: {greeting}")
    await session.say(greeting)
    logger.info("Finished speaking greeting")

    logger.info(f"Agent started for call: {call_id}")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="patient-support-agent",
        )
    )

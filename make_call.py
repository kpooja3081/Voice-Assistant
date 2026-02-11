"""Outbound Phone Call Script — Dispatch Agent + Dial Patient via Twilio SIP.

Usage:
    python make_call.py +919876543210
    python make_call.py +919876543210 --patient P001

This dispatches the patient-support-agent to a new room with metadata
containing the phone number. The agent then dials the phone via SIP trunk.

Prerequisites:
    1. pip install livekit-api python-dotenv
    2. Twilio Elastic SIP Trunk configured
    3. LiveKit Outbound SIP Trunk created (trunk ID in .env)
    4. Agent running: python agent.py dev
"""

import asyncio
import json
import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound-call")

AGENT_NAME = "patient-support-agent"


async def make_call(phone_number: str, patient_id: str = "P001"):
    """Initiate an outbound call by dispatching the agent with phone metadata.

    Args:
        phone_number: Phone number to call (E.164 format, e.g. +919876543210)
        patient_id: Patient ID to load context for (default: P001)
    """
    from livekit import api

    # LiveKit API credentials
    livekit_url = os.getenv("LIVEKIT_URL", "")
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")

    if not all([livekit_url, api_key, api_secret]):
        logger.error(
            "Missing configuration. Ensure these are set in .env:\n"
            "  LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
        )
        return

    # Verify SIP trunk is configured
    trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "")
    if not trunk_id:
        logger.error(
            "SIP_OUTBOUND_TRUNK_ID not set in .env.\n"
            "Create an outbound SIP trunk in LiveKit Cloud dashboard first."
        )
        return

    # Generate a unique room name for this call
    import uuid
    room_name = f"phone-call-{patient_id}-{uuid.uuid4().hex[:8]}"

    # Metadata passed to the agent entrypoint
    metadata = json.dumps({
        "phone_number": phone_number,
        "patient_id": patient_id,
    })

    logger.info(f"Dispatching outbound call:")
    logger.info(f"  Room:     {room_name}")
    logger.info(f"  Phone:    {phone_number}")
    logger.info(f"  Patient:  {patient_id}")
    logger.info(f"  Trunk:    {trunk_id}")
    logger.info(f"  Agent:    {AGENT_NAME}")

    # Use HTTP URL for API (convert wss:// to https://)
    http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")

    # Create LiveKit API client
    lk_api = api.LiveKitAPI(
        url=http_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    try:
        # Step 1: Create a room for the call
        logger.info(f"Creating room '{room_name}'...")
        await lk_api.room.create_room(
            api.CreateRoomRequest(name=room_name)
        )

        # Step 2: Dispatch the agent to the room with phone metadata
        logger.info(f"Dispatching agent '{AGENT_NAME}' to room...")
        await lk_api.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=metadata,
            )
        )

        logger.info(f"Agent dispatched! It will dial {phone_number} automatically.")
        logger.info("Press Ctrl+C to end monitoring (call continues independently).")

        # Monitor the call
        try:
            while True:
                await asyncio.sleep(5)
                rooms = await lk_api.room.list_rooms(api.ListRoomsRequest(names=[room_name]))
                if not rooms.rooms:
                    logger.info("Room closed. Call ended.")
                    break
                room = rooms.rooms[0]
                logger.info(f"  Room active: {room.num_participants} participant(s)")
        except KeyboardInterrupt:
            logger.info("Stopped monitoring. Call may still be active.")

    except Exception as e:
        logger.error(f"Failed to dispatch call: {e}")
        raise
    finally:
        await lk_api.aclose()


def main():
    if len(sys.argv) < 2:
        print("Usage: python make_call.py <phone_number> [--patient <patient_id>]")
        print("Example: python make_call.py +919876543210")
        print("Example: python make_call.py +919876543210 --patient P001")
        print()
        print("Prerequisites:")
        print("  1. Agent must be running: python agent.py dev")
        print("  2. SIP_OUTBOUND_TRUNK_ID must be set in .env")
        print("  3. Twilio Elastic SIP Trunk must be configured")
        sys.exit(1)

    phone_number = sys.argv[1]
    patient_id = "P001"

    if "--patient" in sys.argv:
        idx = sys.argv.index("--patient")
        if idx + 1 < len(sys.argv):
            patient_id = sys.argv[idx + 1]

    # Basic validation
    if not phone_number.startswith("+"):
        print("Phone number must include country code (e.g. +919876543210)")
        sys.exit(1)

    asyncio.run(make_call(phone_number, patient_id))


if __name__ == "__main__":
    main()

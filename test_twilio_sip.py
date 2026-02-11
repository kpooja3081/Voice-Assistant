"""Test Twilio SIP Trunk + LiveKit Integration.

This script validates your Twilio + LiveKit setup before making real calls.
Run each test independently to isolate issues.

Usage:
    python test_twilio_sip.py              # Run all checks
    python test_twilio_sip.py --call +91XXXXXXXXXX  # Make a real test call
"""

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("twilio-sip-test")

# Required env vars for SIP calling
REQUIRED_ENV = {
    "LIVEKIT_URL": "LiveKit server URL (wss://...)",
    "LIVEKIT_API_KEY": "LiveKit API key",
    "LIVEKIT_API_SECRET": "LiveKit API secret",
    "SIP_OUTBOUND_TRUNK_ID": "LiveKit outbound SIP trunk ID (ST_...)",
}

OPTIONAL_ENV = {
    "TWILIO_PHONE_NUMBER": "Your Twilio caller ID phone number",
}


def check_env_vars() -> bool:
    """Test 1: Verify all required environment variables are set."""
    print("\n" + "=" * 60)
    print("TEST 1: Environment Variables")
    print("=" * 60)

    all_ok = True
    for var, description in REQUIRED_ENV.items():
        value = os.getenv(var, "")
        if value:
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"  [OK]   {var} = {masked}")
        else:
            print(f"  [FAIL] {var} is NOT SET  ({description})")
            all_ok = False

    for var, description in OPTIONAL_ENV.items():
        value = os.getenv(var, "")
        if value:
            print(f"  [OK]   {var} = {value}")
        else:
            print(f"  [WARN] {var} not set  ({description})")

    if all_ok:
        print("\n  Result: All required env vars are set.")
    else:
        print("\n  Result: MISSING required env vars. Fix .env before proceeding.")
    return all_ok


async def check_livekit_connection() -> bool:
    """Test 2: Verify LiveKit API connectivity."""
    print("\n" + "=" * 60)
    print("TEST 2: LiveKit API Connection")
    print("=" * 60)

    try:
        from livekit import api

        livekit_url = os.getenv("LIVEKIT_URL", "")
        api_key = os.getenv("LIVEKIT_API_KEY", "")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "")

        http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")

        lk = api.LiveKitAPI(url=http_url, api_key=api_key, api_secret=api_secret)

        # List rooms to verify connectivity
        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
        print(f"  [OK]   Connected to LiveKit at {http_url}")
        print(f"  [OK]   Active rooms: {len(rooms.rooms)}")
        for room in rooms.rooms:
            print(f"         - {room.name} ({room.num_participants} participants)")

        await lk.aclose()
        return True

    except Exception as e:
        print(f"  [FAIL] Cannot connect to LiveKit: {e}")
        return False


async def check_sip_trunk() -> bool:
    """Test 3: Verify the SIP outbound trunk exists and is configured."""
    print("\n" + "=" * 60)
    print("TEST 3: SIP Outbound Trunk Configuration")
    print("=" * 60)

    try:
        from livekit import api

        livekit_url = os.getenv("LIVEKIT_URL", "")
        api_key = os.getenv("LIVEKIT_API_KEY", "")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "")

        http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
        lk = api.LiveKitAPI(url=http_url, api_key=api_key, api_secret=api_secret)

        # List outbound SIP trunks
        trunks = await lk.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        print(f"  [OK]   Found {len(trunks.items)} outbound SIP trunk(s)")

        found = False
        for trunk in trunks.items:
            trunk_info = f"         - ID: {trunk.sip_trunk_id}, Name: {trunk.name}"
            if hasattr(trunk, "address") and trunk.address:
                trunk_info += f", Address: {trunk.address}"
            print(trunk_info)
            if trunk.sip_trunk_id == trunk_id:
                found = True
                print(f"  [OK]   Target trunk '{trunk_id}' found!")

        if not found and trunk_id:
            print(f"  [WARN] Trunk ID '{trunk_id}' not found in list.")
            print("         It may still work if configured correctly.")

        await lk.aclose()
        return True

    except Exception as e:
        print(f"  [FAIL] Cannot query SIP trunks: {e}")
        print(f"         This may be normal if SIP is not enabled yet.")
        return False


async def make_test_call(phone_number: str) -> bool:
    """Test 4: Make an actual outbound test call."""
    print("\n" + "=" * 60)
    print(f"TEST 4: Outbound Test Call to {phone_number}")
    print("=" * 60)

    if not phone_number.startswith("+"):
        print("  [FAIL] Phone number must start with + (E.164 format)")
        return False

    try:
        from livekit import api
        import uuid

        livekit_url = os.getenv("LIVEKIT_URL", "")
        api_key = os.getenv("LIVEKIT_API_KEY", "")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "")

        http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
        lk = api.LiveKitAPI(url=http_url, api_key=api_key, api_secret=api_secret)

        room_name = f"test-call-{uuid.uuid4().hex[:8]}"

        print(f"  [INFO] Creating SIP participant...")
        print(f"         Room: {room_name}")
        print(f"         Trunk: {trunk_id}")
        print(f"         Dialing: {phone_number}")

        participant = await lk.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=f"phone-{phone_number}",
                participant_name="Test Call",
                play_dialtone=True,
            )
        )

        print(f"  [OK]   Call connected!")
        print(f"         Participant ID: {participant.participant_id}")
        print(f"         Room: {room_name}")
        print()
        print("  The phone should be ringing now.")
        print("  NOTE: Without an agent running, you'll hear silence after answering.")
        print("  Press Ctrl+C to end the call.")

        try:
            await asyncio.sleep(30)  # Keep call alive for 30 seconds
        except KeyboardInterrupt:
            pass

        # Clean up: delete the room
        print("\n  [INFO] Cleaning up room...")
        try:
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            print(f"  [OK]   Room '{room_name}' deleted.")
        except Exception:
            pass

        await lk.aclose()
        return True

    except Exception as e:
        print(f"  [FAIL] Call failed: {e}")
        error_str = str(e)
        if "trunk" in error_str.lower():
            print("  HINT: Check your SIP_OUTBOUND_TRUNK_ID is correct.")
        elif "auth" in error_str.lower():
            print("  HINT: Check Twilio trunk authentication (credentials or IP ACL).")
        elif "sip" in error_str.lower():
            print("  HINT: SIP may not be enabled on your LiveKit project.")
        return False


async def run_all_tests(phone_number: str | None = None):
    """Run all tests in sequence."""
    print("\n" + "#" * 60)
    print("  Twilio SIP + LiveKit Integration Test Suite")
    print("#" * 60)

    results = {}

    # Test 1: Env vars
    results["env"] = check_env_vars()

    if not results["env"]:
        print("\n\nCannot proceed without required env vars. Stopping.")
        return results

    # Test 2: LiveKit connection
    results["livekit"] = await check_livekit_connection()

    # Test 3: SIP trunk
    results["sip_trunk"] = await check_sip_trunk()

    # Test 4: Real call (only if requested)
    if phone_number:
        results["call"] = await make_test_call(phone_number)
    else:
        print("\n" + "=" * 60)
        print("TEST 4: Outbound Call (SKIPPED)")
        print("=" * 60)
        print("  Pass --call +phoneNumber to make a real test call.")

    # Summary
    print("\n" + "#" * 60)
    print("  TEST SUMMARY")
    print("#" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    all_passed = all(results.values())
    if all_passed:
        print("\n  All tests passed! Ready to make calls.")
    else:
        print("\n  Some tests failed. Fix issues above before calling.")

    return results


def main():
    phone_number = None

    if "--call" in sys.argv:
        idx = sys.argv.index("--call")
        if idx + 1 < len(sys.argv):
            phone_number = sys.argv[idx + 1]
        else:
            print("Error: --call requires a phone number (e.g., --call +919876543210)")
            sys.exit(1)

    asyncio.run(run_all_tests(phone_number))


if __name__ == "__main__":
    main()

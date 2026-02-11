"""Setup LiveKit Outbound SIP Trunk for Twilio.

Interactive script to create an outbound SIP trunk in LiveKit
that points to your Twilio Elastic SIP Trunk.

Usage:
    python setup_sip_trunk.py

Prerequisites:
    1. Twilio Elastic SIP Trunk already created (with termination URI)
    2. Twilio credential list configured for trunk authentication
    3. Phone number purchased and associated with the trunk
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sip-trunk-setup")


async def create_outbound_trunk():
    """Interactively create a LiveKit outbound SIP trunk."""
    from livekit import api

    livekit_url = os.getenv("LIVEKIT_URL", "")
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")

    if not all([livekit_url, api_key, api_secret]):
        print("ERROR: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET must be set in .env")
        return

    print()
    print("=" * 60)
    print("  LiveKit Outbound SIP Trunk Setup (for Twilio)")
    print("=" * 60)
    print()
    print("Before running this, you need:")
    print("  1. A Twilio Elastic SIP Trunk with Termination configured")
    print("  2. A credential list (username/password) on the trunk")
    print("  3. A Twilio phone number associated with the trunk")
    print()

    # Collect Twilio trunk info
    trunk_domain = input("Twilio Termination SIP URI (e.g., my-trunk.pstn.twilio.com): ").strip()
    if not trunk_domain:
        print("ERROR: Trunk domain is required.")
        return

    phone_number = input("Twilio phone number (E.164, e.g., +14155551234): ").strip()
    if not phone_number.startswith("+"):
        print("ERROR: Phone number must start with + (E.164 format).")
        return

    auth_user = input("Twilio credential list username: ").strip()
    auth_pass = input("Twilio credential list password: ").strip()

    trunk_name = input("Trunk name (default: Twilio Outbound): ").strip() or "Twilio Outbound"

    print()
    print(f"Creating outbound trunk:")
    print(f"  Name:     {trunk_name}")
    print(f"  Address:  {trunk_domain}")
    print(f"  Number:   {phone_number}")
    print(f"  Auth:     {auth_user} / {'*' * len(auth_pass)}")

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
    lk = api.LiveKitAPI(url=http_url, api_key=api_key, api_secret=api_secret)

    try:
        trunk = await lk.sip.create_sip_outbound_trunk(
            api.CreateSIPOutboundTrunkRequest(
                trunk=api.SIPOutboundTrunkInfo(
                    name=trunk_name,
                    address=trunk_domain,
                    numbers=[phone_number],
                    auth_username=auth_user,
                    auth_password=auth_pass,
                )
            )
        )

        trunk_id = trunk.sip_trunk_id
        print()
        print("=" * 60)
        print("  SUCCESS! Outbound SIP trunk created.")
        print("=" * 60)
        print()
        print(f"  Trunk ID: {trunk_id}")
        print()
        print("  Add this to your .env file:")
        print(f"    SIP_OUTBOUND_TRUNK_ID={trunk_id}")
        print(f"    TWILIO_PHONE_NUMBER={phone_number}")
        print()
        print("  Then test with:")
        print("    python test_twilio_sip.py")
        print("    python test_twilio_sip.py --call +phoneNumber")

    except Exception as e:
        print(f"\nERROR creating trunk: {e}")
        print("\nTroubleshooting:")
        print("  - Check your LiveKit URL and credentials")
        print("  - Ensure SIP is enabled on your LiveKit Cloud project")
        print("  - Verify the Twilio trunk domain is correct")
    finally:
        await lk.aclose()


async def list_trunks():
    """List existing SIP trunks."""
    from livekit import api

    livekit_url = os.getenv("LIVEKIT_URL", "")
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")

    http_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
    lk = api.LiveKitAPI(url=http_url, api_key=api_key, api_secret=api_secret)

    try:
        trunks = await lk.sip.list_sip_trunk(api.ListSIPTrunkRequest())
        print(f"\nFound {len(trunks.items)} SIP trunk(s):")
        for t in trunks.items:
            print(f"  - ID: {t.sip_trunk_id}")
            print(f"    Name: {t.name}")
            if hasattr(t, "outbound_address") and t.outbound_address:
                print(f"    Address: {t.outbound_address}")
            if hasattr(t, "outbound_number") and t.outbound_number:
                print(f"    Number: {t.outbound_number}")
            print()
    except Exception as e:
        print(f"Error listing trunks: {e}")
    finally:
        await lk.aclose()


def main():
    import sys

    if "--list" in sys.argv:
        asyncio.run(list_trunks())
    else:
        asyncio.run(create_outbound_trunk())


if __name__ == "__main__":
    main()

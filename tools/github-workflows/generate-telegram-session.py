#!/usr/bin/env python3
"""
One-time helper: mint a Telethon session string for your own Telegram account.

Run this ON YOUR OWN COMPUTER or your own VPS:

    pip install telethon
    python3 generate-telegram-session.py

It will ask for:
  - your api_id and api_hash  (https://my.telegram.org -> API development tools)
  - your PHONE NUMBER (international format, e.g. +94771234567)
       ^ NOT the bot token. A bot token would create a bot session, which
         GitHub Actions would then fail with "API access for bot users is
         restricted".
  - the login code Telegram sends to your Telegram app
    (and your 2FA password, if you have one)

Then it prints a long string like:  1BQANOTEuMTA4L...=
Add that string to your repo secrets as TG_SESSION.

Keep it secret: whoever holds this string IS logged in as you.
If it ever leaks: Telegram -> Settings -> Devices -> terminate the session.
"""

import re


def main():
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        raise SystemExit("telethon is not installed. Run:  pip install telethon")

    print("== Telegram session string generator ==\n")
    api_id = int(input("api_id (number from my.telegram.org): ").strip())
    api_hash = input("api_hash (32 chars from my.telegram.org): ").strip()

    # Ask for the phone number ourselves (with a guard) instead of letting
    # Telethon prompt for it - Telethon's prompt also accepts bot tokens,
    # which silently creates a BOT session that is useless for this workflow.
    while True:
        phone = input("your phone number, international format (e.g. +94771234567): ").strip()
        if re.fullmatch(r"\+?\d{7,15}", phone):
            break
        if re.fullmatch(r"\d{8,12}:[\w-]{20,}", phone):
            print("  -> that is a BOT TOKEN. This helper must be YOUR account.")
            print("     Open Telegram and check your own profile for the number, then enter it here.")
            continue
        print("  -> that does not look like a phone number. Example: +94771234567")

    client = TelegramClient(StringSession(), api_id, api_hash)
    client.start(phone=phone)  # asks only for the login code (+ 2FA password if set)

    me = client.get_me()
    if getattr(me, "bot", False):
        raise SystemExit(
            "\n!! Logged in as a BOT - that is wrong for this workflow.\n"
            "   Delete this session and run the helper again, entering your PHONE NUMBER."
        )
    name = " ".join(filter(None, [getattr(me, "first_name", ""), getattr(me, "last_name", "")]))
    username = "@" + me.username if getattr(me, "username", "") else "(no username)"
    print(f"\nLogged in as: {name} {username}   <- user account, correct")

    session = client.session.save()
    print("\n== DONE. Add this string to your repo secrets as TG_SESSION ==\n")
    print(session)
    client.disconnect()


if __name__ == "__main__":
    main()

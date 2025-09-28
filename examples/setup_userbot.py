#!/usr/bin/env python3
"""
Script to setup userbot sessions for ArchFairFight.
Run this script to authenticate userbot accounts and generate session files.
"""

import os
import sys
from pyrogram import Client

def setup_userbot_session():
    """Setup a userbot session."""
    print("ArchFairFight Userbot Setup")
    print("=" * 30)
    
    # Get API credentials
    api_id = input("Enter your API ID: ").strip()
    api_hash = input("Enter your API Hash: ").strip()
    
    if not api_id or not api_hash:
        print("Error: API ID and Hash are required!")
        return False
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("Error: API ID must be a number!")
        return False
    
    # Get session name
    session_name = input("Enter session name (e.g., userbot1): ").strip()
    if not session_name:
        session_name = "userbot1"
    
    # Create sessions directory
    sessions_dir = "sessions"
    os.makedirs(sessions_dir, exist_ok=True)
    
    session_path = os.path.join(sessions_dir, session_name)
    
    print(f"\nCreating session: {session_path}")
    print("You will be prompted to enter your phone number and verification code.")
    print("Make sure to use a Telegram account that you want to use as a userbot.")
    print()
    
    try:
        # Create and start client
        client = Client(session_path, api_id=api_id, api_hash=api_hash)
        
        with client:
            me = client.get_me()
            print(f"✅ Successfully logged in as: {me.first_name}")
            if me.username:
                print(f"   Username: @{me.username}")
            print(f"   Session saved: {session_path}.session")
            
        print(f"\n✅ Userbot session setup complete!")
        print(f"Add this to your .env file:")
        print(f"USERBOT_SESSIONS={session_path}.session")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up userbot session: {e}")
        return False

def main():
    """Main function."""
    if not setup_userbot_session():
        sys.exit(1)
    
    # Ask if user wants to setup another session
    while True:
        setup_another = input("\nDo you want to setup another userbot session? (y/n): ").strip().lower()
        if setup_another in ['y', 'yes']:
            if not setup_userbot_session():
                break
        elif setup_another in ['n', 'no']:
            break
        else:
            print("Please enter 'y' or 'n'")
    
    print("\n🎉 All done! Your userbot sessions are ready.")
    print("Make sure to add all session paths to your .env file under USERBOT_SESSIONS")
    print("Example: USERBOT_SESSIONS=sessions/userbot1.session,sessions/userbot2.session")

if __name__ == "__main__":
    main()
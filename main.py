import os
import asyncio
from fastapi import FastAPI
import uvicorn
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import CreateChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.errors import FloodWaitError
from datetime import datetime

# Environment variables
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION_STRING")
PORT = int(os.environ.get("PORT", 8000))

# Source and backup chat settings
SOURCE_CHAT_ID = -1001552790071
BACKUP_CHAT_ID = None

# Create FastAPI app
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "alive", "message": "Telegram backup bot is running"}

BOTS_TO_IGNORE = [
    '@KPSLeech6Bot',
    '@KPSLeech5Bot',
    '@KPSLeech4Bot',
    '@KPSLeech3Bot',
    '@KPSLeech2Bot',
    '@KPSLeech1Bot',
    '@KPSMirrorXBot',
    '@KPSLeechBot'
]

async def get_next_channel_number():
    """Find the next available channel number by checking existing dialogs"""
    try:
        max_num = 0
        async for dialog in client.iter_dialogs():
            if dialog.name.startswith("💾 Backup #"):
                try:
                    current_num = int(dialog.name.split('#')[1].split()[0])
                    max_num = max(max_num, current_num)
                except (IndexError, ValueError):
                    continue
        return max_num + 1
    except Exception as e:
        print(f"⚠️ Error checking existing channels: {str(e)}")
        return 1  # Fallback to 1 if there's an error

async def create_backup_channel():
    """Creates a new backup channel with serial number"""
    try:
        channel_num = await get_next_channel_number()
        timestamp = datetime.now().strftime("%Y-%m-%d")
        title = f"💾 Backup #{channel_num} ({timestamp})"
        
        created = await client(CreateChannelRequest(
            title=title,
            about=f"Automatically created backup channel #{channel_num}",
            megagroup=True,
            broadcast=False
        ))

        new_chat_id = created.chats[0].id
        print(f"✅ Backup channel created (ID: {new_chat_id}) - {title}")

        try:
            invite = await client(ExportChatInviteRequest(peer=new_chat_id))
            print(f"🔗 Permanent invite link: {invite.link}")
        except Exception as e:
            print(f"⚠️ Couldn't create invite link: {str(e)}")

        await client(JoinChannelRequest(channel=new_chat_id))
        print("👀 Channel joined successfully")

        return new_chat_id

    except FloodWaitError as e:
        print(f"⏳ Flood wait: Please wait {e.seconds} seconds before trying again")
        return None
    except Exception as e:
        print(f"❌ Channel creation failed: {str(e)}")
        return None

async def setup_backup_chat():
    """Handles the backup chat setup"""
    # First try to find the most recent backup channel
    try:
        latest_channel = None
        latest_num = 0
        async for dialog in client.iter_dialogs():
            if dialog.name.startswith("💾 Backup #"):
                try:
                    current_num = int(dialog.name.split('#')[1].split()[0])
                    if current_num > latest_num:
                        latest_num = current_num
                        latest_channel = dialog.entity
                except (IndexError, ValueError):
                    continue
        
        if latest_channel:
            print(f"🔍 Found existing backup channel: {latest_channel.title}")
            return latest_channel.id
    except Exception as e:
        print(f"⚠️ Error searching existing channels: {str(e)}")

    # If no existing channel found, create a new one
    return await create_backup_channel()

@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def message_handler(event):
    if not BACKUP_CHAT_ID:
        return

    try:
        sender = await event.get_sender()

        if sender.bot or (hasattr(sender, 'username') and sender.username in BOTS_TO_IGNORE):
            print(f"🤖 Ignoring message from bot: {getattr(sender, 'username', 'unknown')}")
            return

        name = getattr(sender, 'first_name', 'Unknown')
        if getattr(sender, 'last_name', ''):
            name += f" {sender.last_name}"
        if getattr(sender, 'username', ''):
            name += f" (@{sender.username})"

        if event.text:
            await client.send_message(
                entity=BACKUP_CHAT_ID,
                message=f"👤 {name}\n⏰ {event.date}\n💬 {event.text}"
            )
        elif event.media:
            await client.send_file(
                entity=BACKUP_CHAT_ID,
                file=event.media,
                caption=f"📎 From {name}"
            )
    except Exception as e:
        print(f"🚫 Forward error: {str(e)}")

async def start_bot():
    await client.start()

    try:
        await client.get_entity(SOURCE_CHAT_ID)
        print("✅ Source chat verified")
    except Exception as e:
        print(f"❌ Source chat error: {str(e)}")
        return

    global BACKUP_CHAT_ID
    BACKUP_CHAT_ID = await setup_backup_chat()
    if not BACKUP_CHAT_ID:
        print("💀 Failed to establish backup channel")
        return

    print(f"\n🟢 Ready! Monitoring {SOURCE_CHAT_ID} → {BACKUP_CHAT_ID}")
    await client.run_until_disconnected()

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    server_thread = Thread(target=run_fastapi, daemon=True)
    server_thread.start()
    
    client.loop.run_until_complete(start_bot())

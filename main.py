import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import CreateChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.errors import FloodWaitError

# Environment variables
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION_STRING")

# Source and backup chat settings
SOURCE_CHAT_ID = -1001552790071  # Replace with your group/channel ID
BACKUP_CHAT_ID = None  # Will be set automatically

# Create client
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# List of bots to ignore
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

async def create_backup_channel():
    """Creates a new backup channel (supergroup)"""
    try:
        created = await client(CreateChannelRequest(
            title="💾 Message Backup Channel",
            about="Automatically created for message backups",
            megagroup=True,
            broadcast=False
        ))

        new_chat_id = created.chats[0].id
        print(f"✅ Backup channel created (ID: {new_chat_id})")

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
    new_chat_id = await create_backup_channel()
    if new_chat_id:
        return new_chat_id

    print("\n🔄 Trying fallback solutions...")

    try:
        if BACKUP_CHAT_ID:
            await client(JoinChannelRequest(channel=BACKUP_CHAT_ID))
            print(f"✅ Joined existing backup channel (ID: {BACKUP_CHAT_ID})")
            return BACKUP_CHAT_ID
    except Exception as e:
        print(f"⚠️ Couldn't join existing channel: {str(e)}")

    try:
        print("Attempting to create basic group...")
        async with client.conversation('me') as conv:
            await conv.send_message('/newgroup')
            await conv.get_response()
            await conv.send_message('Message Backup Group')
            await conv.get_response()
            print("✅ Basic group created")
            return None
    except Exception as e:
        print(f"❌ Basic group creation failed: {str(e)}")
        return None

@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def message_handler(event):
    if not BACKUP_CHAT_ID:
        return

    try:
        sender = await event.get_sender()

        if sender.bot:
            print(f"🤖 Ignoring message from bot: {sender.username}")
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

async def main():
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
        print("\n🔧 Manual solution:")
        print("1. Create a channel manually")
        print("2. Add your bot as admin")
        print("3. Set BACKUP_CHAT_ID to its ID (-100 prefix)")
        return

    print(f"\n🟢 Ready! Monitoring {SOURCE_CHAT_ID} → {BACKUP_CHAT_ID}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())

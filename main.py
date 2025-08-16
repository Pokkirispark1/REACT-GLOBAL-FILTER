import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import os
from database import init_db, get_connected_groups, is_group_connected, init_database_config
from reactions import handle_reactions
from filters_handler import handle_filters, filter_command, list_filters_command, del_filter_command

# Bot configuration
API_ID = 26592588
API_HASH = "4f78c40e672ad86e10384cc8a0b43dc7"
BOT_TOKEN = "8090595880:AAH5w6sgXU38DxoZ19T_Hfm-x7cZWcOapG4"
ADMINS = [1769132732, 560951157]
MONGODB_URI = "mongodb+srv://reactionbkots:reactionbkots@cluster0.onptwey.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "Reactions"
R_EMOJIS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏"]

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMINS

app = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await message.reply_text(
        "**Available Commands:**\n\n"
        "/connect -100xxxxxxx - Connect bot to a group\n"
        "/filter keyword response - Set auto-reply filter\n"
        "/filters - List all filters\n"
        "/delfilter keyword - Delete a filter"
    )

@app.on_message(filters.command("connect") & filters.private)
async def connect_command(client, message: Message):
    # Check if user is admin
    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Only admins can use this command!")
        return
        
    try:
        if len(message.command) < 2:
            await message.reply_text("Usage: /connect -100xxxxxxx")
            return
        
        chat_id = int(message.command[1])
        user_id = message.from_user.id
        
        # Check if user is admin in the target group
        try:
            member = await client.get_chat_member(chat_id, user_id)
            if member.status not in ["administrator", "creator"]:
                await message.reply_text("You must be an admin in that group!")
                return
        except:
            await message.reply_text("Invalid group ID or bot is not in the group!")
            return
        
        # Save connection to database
        from database import save_connection
        await save_connection(chat_id, user_id)
        
        await message.reply_text(f"Bot connected to group {chat_id} successfully!")
        
    except ValueError:
        await message.reply_text("Invalid group ID format!")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@app.on_message(filters.group & ~filters.bot)
async def group_message_handler(client, message: Message):
    chat_id = message.chat.id
    
    # Check if group is connected
    if not await is_group_connected(chat_id):
        return
    
    # Handle reactions
    await handle_reactions(client, message)
    
    # Handle filters
    await handle_filters(client, message)

# Filter management commands
@app.on_message(filters.command("filter") & filters.private)
async def set_filter(client, message: Message):
    # Check if user is admin
    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Only admins can use this command!")
        return
    await filter_command(client, message)

@app.on_message(filters.command("filters") & filters.private) 
async def list_filters(client, message: Message):
    # Check if user is admin
    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Only admins can use this command!")
        return
    await list_filters_command(client, message)

@app.on_message(filters.command("delfilter") & filters.private)
async def delete_filter(client, message: Message):
    # Check if user is admin
    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Only admins can use this command!")
        return
    await del_filter_command(client, message)

@app.on_ready
async def on_startup():
    """Called when bot starts"""
    init_database_config(MONGODB_URI, DATABASE_NAME)
    await init_db()
    print("Bot started successfully!")

if __name__ == "__main__":
    app.run()

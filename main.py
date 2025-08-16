import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import os
from database import init_db, get_connected_groups, is_group_connected
from reactions import handle_reactions
from filters_handler import handle_filters, filter_command, list_filters_command, del_filter_command

# Bot configuration
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

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
    await filter_command(client, message)

@app.on_message(filters.command("filters") & filters.private) 
async def list_filters(client, message: Message):
    await list_filters_command(client, message)

@app.on_message(filters.command("delfilter") & filters.private)
async def delete_filter(client, message: Message):
    await del_filter_command(client, message)

async def main():
    await init_db()
    await app.start()
    print("Bot started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

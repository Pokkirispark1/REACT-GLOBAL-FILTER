import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config_vars import configVars
import random
import logging
import json
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=configVars.CLOUDINARY_URL.split('@')[-1],
    api_key=configVars.CLOUDINARY_URL.split('://')[1].split(':')[0],
    api_secret=configVars.CLOUDINARY_URL.split('://')[1].split(':')[1].split('@')[0]
)

# JSON file ID for Cloudinary
DATA_FILE_ID = "bot_data.json"

# Load data from Cloudinary
def load_data():
    try:
        response = cloudinary.api.resource(DATA_FILE_ID, resource_type="raw")
        data = json.loads(response["secure_url"].get(timeout=10).text)
        configVars.CHAT_DATA["connected_groups"] = set(data.get("connected_groups", []))
        configVars.CHAT_DATA["filters"] = data.get("filters", {})
        logger.info("Loaded data from Cloudinary")
    except Exception as e:
        logger.warning(f"Failed to load data from Cloudinary: {str(e)}")
        configVars.CHAT_DATA["connected_groups"] = set()
        configVars.CHAT_DATA["filters"] = {}

# Save data to Cloudinary
def save_data():
    try:
        data = {
            "connected_groups": list(configVars.CHAT_DATA["connected_groups"]),
            "filters": configVars.CHAT_DATA["filters"]
        }
        cloudinary.uploader.upload(
            json.dumps(data),
            public_id=DATA_FILE_ID,
            resource_type="raw",
            invalidate=True
        )
        logger.info("Saved data to Cloudinary")
    except Exception as e:
        logger.error(f"Failed to save data to Cloudinary: {str(e)}")

# Initialize the bot
app = Client(
    "AutoReactionBot",
    api_id=configVars.API_ID,
    api_hash=configVars.API_HASH,
    bot_token=configVars.BOT_TOKEN
)

# Load data on startup
load_data()

# Helper function to check if user is admin
def is_admin(user_id):
    return user_id in configVars.ADMINS

# Command: /start
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply(configVars.START_MESSAGE)

# Command: /connect <group_id>
@app.on_message(filters.command("connect") & filters.private)
async def connect_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Only admins can use this command.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("Usage: /connect <group_id>")
        return

    try:
        group_id = int(args[1])
        # Verify if the bot is in the group
        chat = await client.get_chat(group_id)
        if chat.type not in ["group", "supergroup"]:
            await message.reply("Invalid group ID. Please provide a valid group ID.")
            return

        configVars.CHAT_DATA["connected_groups"].add(group_id)
        save_data()  # Save to Cloudinary
        await message.reply(f"Connected to group {group_id}.")
        await client.send_message(
            configVars.LOG_CHANNEL,
            f"Connected to group {group_id} by {message.from_user.id}"
        )
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
        logger.error(f"Connect command error: {str(e)}")

# Command: /filter <keyword> <response>
@app.on_message(filters.command("filter") & filters.private)
async def filter_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Only admins can use this command.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Usage: /filter <keyword> <response>")
        return

    keyword = args[1].lower()
    response = args[2]
    configVars.CHAT_DATA["filters"][keyword] = response
    save_data()  # Save to Cloudinary
    await message.reply(f"Filter set: '{keyword}' -> '{response}'")
    await client.send_message(
        configVars.LOG_CHANNEL,
        f"Filter added: '{keyword}' -> '{response}' by {message.from_user.id}"
    )

# Command: /delfilter <keyword>
@app.on_message(filters.command("delfilter") & filters.private)
async def delfilter_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Only admins can use this command.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("Usage: /delfilter <keyword>")
        return

    keyword = args[1].lower()
    if keyword not in configVars.CHAT_DATA["filters"]:
        await message.reply(f"No filter found for keyword: '{keyword}'")
        return

    del configVars.CHAT_DATA["filters"][keyword]
    save_data()  # Save to Cloudinary
    await message.reply(f"Filter for '{keyword}' deleted.")
    await client.send_message(
        configVars.LOG_CHANNEL,
        f"Filter deleted: '{keyword}' by {message.from_user.id}"
    )

# Command: /listfilters
@app.on_message(filters.command("listfilters") & filters.private)
async def listfilters_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Only admins can use this command.")
        return

    if not configVars.CHAT_DATA["filters"]:
        await message.reply("No filters set.")
        return

    filter_list = "\n".join(
        f"- '{k}' -> '{v}'" for k, v in configVars.CHAT_DATA["filters"].items()
    )
    await message.reply(f"Current filters:\n{filter_list}")
    await client.send_message(
        configVars.LOG_CHANNEL,
        f"Filter list requested by {message.from_user.id}"
    )

# Handle new messages in connected groups
@app.on_message(filters.group & filters.text)
async def handle_group_message(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in configVars.CHAT_DATA["connected_groups"]:
        return

    # Auto-reaction with random emoji
    try:
        emoji = random.choice(configVars.R_EMOJIS)
        await client.set_reaction(chat_id, message.id, emoji)
        logger.info(f"Reacted with {emoji} to message {message.id} in {chat_id}")
    except Exception as e:
        logger.error(f"Error setting reaction: {str(e)}")
        await client.send_message(
            configVars.LOG_CHANNEL,
            f"Failed to react in {chat_id}: {str(e)}"
        )

    # Check for keyword filters
    message_text = message.text.lower()
    for keyword, response in configVars.CHAT_DATA["filters"].items():
        if keyword in message_text:
            try:
                await message.reply(response

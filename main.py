import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config_vars import configVars
import random
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MongoDB
try:
    mongo_client = MongoClient(configVars.DB_URI)
    db = mongo_client["AutoReactionBot"]
    groups_collection = db["connected_groups"]
    filters_collection = db["filters"]
    # Test connection
    mongo_client.admin.command("ping")
    logger.info("Connected to MongoDB")
except ConnectionFailure as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise SystemExit("MongoDB connection failed. Please check DB_URI.")

# Initialize the bot
app = Client(
    "AutoReactionBot",
    api_id=configVars.API_ID,
    api_hash=configVars.API_HASH,
    bot_token=configVars.BOT_TOKEN
)

# Initialize in-memory cache
configVars.CHAT_DATA["connected_groups"] = set(
    doc["group_id"] for doc in groups_collection.find()
)
configVars.CHAT_DATA["filters"] = {
    doc["keyword"]: doc["response"] for doc in filters_collection.find()
}

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

        # Save to MongoDB and cache
        groups_collection.update_one(
            {"group_id": group_id},
            {"$set": {"group_id": group_id}},
            upsert=True
        )
        configVars.CHAT_DATA["connected_groups"].add(group_id)
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
    # Save to MongoDB and cache
    filters_collection.update_one(
        {"keyword": keyword},
        {"$set": {"keyword": keyword, "response": response}},
        upsert=True
    )
    configVars.CHAT_DATA["filters"][keyword] = response
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

    # Remove from MongoDB and cache
    filters_collection.delete_one({"keyword": keyword})
    del configVars.CHAT_DATA["filters"][keyword]
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
                await message.reply(response)
                logger.info(f"Responded to '{keyword}' with '{response}' in {chat_id}")
                await client.send_message(
                    configVars.LOG_CHANNEL,
                    f"Responded to '{keyword}' in {chat_id}"
                )
            except Exception as e:
                logger.error(f"Error responding to filter: {str(e)}")
                await client.send_message(
                    configVars.LOG_CHANNEL,
                    f"Failed to respond in {chat_id}: {str(e)}"
                )

# Start the bot
async def main():
    await app.start()
    logger.info("Bot started")
    await asyncio.Event().wait()  # Keep the bot running

if __name__ == "__main__":
    asyncio.run(main())

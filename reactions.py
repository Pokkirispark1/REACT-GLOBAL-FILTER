import random
from pyrogram import Client
from pyrogram.types import Message

R_EMOJIS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏"]

async def handle_reactions(client: Client, message: Message):
    """Handle automatic reactions to messages"""
    try:
        # Randomly select an emoji
        emoji = random.choice(R_EMOJIS)
        
        # React to the message
        await message.react(emoji)
        
    except Exception as e:
        print(f"Error reacting to message: {e}")
        # Silently continue if reaction fails

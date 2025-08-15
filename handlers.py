import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, FloodWait, BadRequest

from database import db
from utils import (
    is_admin, extract_group_id, get_random_reaction, format_user_info,
    format_chat_info, extract_filter_parts, extract_remove_filter_keyword,
    is_group_chat, is_private_chat, format_filters_list, get_help_text,
    get_stats_text, sanitize_text
)
from config import Config

logger = logging.getLogger(__name__)

class MessageHandlers:
    def __init__(self, app: Client):
        self.app = app
        
    def setup_handlers(self):
        """Setup all message handlers"""
        
        # Admin commands
        @self.app.on_message(filters.command("connect") & filters.private)
        async def handle_connect(client: Client, message: Message):
            """Handle /connect command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            group_id = extract_group_id(message.text)
            if not group_id:
                await message.reply(
                    "❌ Invalid group ID format!\n\n"
                    "Usage: `/connect -100xxxxxxxxx`\n"
                    "Example: `/connect -1001234567890`"
                )
                return
            
            try:
                # Try to get chat info
                chat = await client.get_chat(group_id)
                
                # Check if bot is admin in the group
                bot_member = await client.get_chat_member(group_id, "me")
                if not bot_member.privileges or not bot_member.privileges.can_delete_messages:
                    await message.reply(
                        "❌ Bot must be an admin in the group with message management permissions!"
                    )
                    return
                
                # Add to database
                success = await db.add_connected_group(
                    group_id=group_id,
                    group_title=chat.title,
                    admin_id=message.from_user.id
                )
                
                if success:
                    await message.reply(
                        f"✅ Successfully connected to **{chat.title}**!\n"
                        f"Group ID: `{group_id}`\n\n"
                        "Bot will now react to all messages in this group."
                    )
                    logger.info(f"Group {group_id} connected by {format_user_info(message.from_user)}")
                else:
                    await message.reply("❌ Failed to connect group. Please try again.")
                    
            except ChatAdminRequired:
                await message.reply("❌ Bot must be an admin in the target group!")
            except UserNotParticipant:
                await message.reply("❌ Bot is not a member of this group!")
            except Exception as e:
                logger.error(f"Error connecting group: {e}")
                await message.reply("❌ Failed to connect group. Please check the group ID.")
        
        @self.app.on_message(filters.command("disconnect") & filters.private)
        async def handle_disconnect(client: Client, message: Message):
            """Handle /disconnect command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            group_id = extract_group_id(message.text)
            if not group_id:
                await message.reply(
                    "❌ Invalid group ID format!\n\n"
                    "Usage: `/disconnect -100xxxxxxxxx`"
                )
                return
            
            success = await db.remove_connected_group(group_id)
            
            if success:
                await message.reply(f"✅ Successfully disconnected from group `{group_id}`!")
                logger.info(f"Group {group_id} disconnected by {format_user_info(message.from_user)}")
            else:
                await message.reply("❌ Group not found or already disconnected.")
        
        @self.app.on_message(filters.command("filter") & filters.private)
        async def handle_add_filter(client: Client, message: Message):
            """Handle /filter command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            keyword, response = extract_filter_parts(message.text)
            
            if not keyword or not response:
                await message.reply(
                    "❌ Invalid filter format!\n\n"
                    "Usage: `/filter keyword response`\n"
                    "Example: `/filter hello Hi there! How are you?`\n\n"
                    "Rules:\n"
                    "• Keyword must be alphanumeric (no spaces)\n"
                    "• Response must be less than 1000 characters"
                )
                return
            
            # Sanitize response
            response = sanitize_text(response)
            
            success = await db.add_filter(keyword, response, message.from_user.id)
            
            if success:
                await message.reply(
                    f"✅ Filter added successfully!\n\n"
                    f"**Keyword:** `{keyword}`\n"
                    f"**Response:** {response}"
                )
                logger.info(f"Filter '{keyword}' added by {format_user_info(message.from_user)}")
            else:
                await message.reply("❌ Failed to add filter. Please try again.")
        
        @self.app.on_message(filters.command("removefilter") & filters.private)
        async def handle_remove_filter(client: Client, message: Message):
            """Handle /removefilter command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            keyword = extract_remove_filter_keyword(message.text)
            
            if not keyword:
                await message.reply(
                    "❌ Invalid format!\n\n"
                    "Usage: `/removefilter keyword`\n"
                    "Example: `/removefilter hello`"
                )
                return
            
            success = await db.remove_filter(keyword)
            
            if success:
                await message.reply(f"✅ Filter `{keyword}` removed successfully!")
                logger.info(f"Filter '{keyword}' removed by {format_user_info(message.from_user)}")
            else:
                await message.reply(f"❌ Filter `{keyword}` not found.")
        
        @self.app.on_message(filters.command("filters") & filters.private)
        async def handle_list_filters(client: Client, message: Message):
            """Handle /filters command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            filters_list = await db.get_all_filters()
            formatted_text = format_filters_list(filters_list)
            
            await message.reply(formatted_text)
        
        @self.app.on_message(filters.command("stats") & filters.private)
        async def handle_stats(client: Client, message: Message):
            """Handle /stats command"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                connected_groups = await db.get_connected_groups()
                all_filters = await db.get_all_filters()
                
                stats_text = get_stats_text(len(connected_groups), len(all_filters))
                await message.reply(stats_text)
                
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                await message.reply("❌ Failed to get statistics.")
        
        @self.app.on_message(filters.command("help"))
        async def handle_help(client: Client, message: Message):
            """Handle /help command"""
            if is_private_chat(message):
                if not is_admin(message.from_user.id):
                    await message.reply("❌ You are not authorized to use this bot.")
                    return
                
                help_text = get_help_text()
                await message.reply(help_text)
            # Ignore help command in groups
        
        # Message reactions and filters
        @self.app.on_message(filters.text & ~filters.command(["connect", "disconnect", "filter", "removefilter", "filters", "stats", "help"]))
        async def handle_messages(client: Client, message: Message):
            """Handle all text messages for reactions and filters"""
            
            # Only process messages in connected groups
            if is_group_chat(message):
                is_connected = await db.is_group_connected(message.chat.id)
                if not is_connected:
                    return
                
                # Add reaction to message
                await self.add_reaction(message)
                
                # Check for filters
                await self.check_filters(message)
            
            elif is_private_chat(message) and is_admin(message.from_user.id):
                # Check for filters in admin PM as well
                await self.check_filters(message)
    
    async def add_reaction(self, message: Message):
        """Add reaction to message"""
        try:
            reaction = get_random_reaction()
            await message.react(emoji=reaction, big=True)
            
        except BadRequest as e:
            # Try with default reaction if reaction is invalid
            try:
                await message.react(emoji=Config.DEFAULT_REACTION, big=True)
            except Exception as e:
                logger.error(f"Failed to add any reaction: {e}")
                
        except FloodWait as e:
            logger.warning(f"FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
    
    async def check_filters(self, message: Message):
        """Check message for filters and respond"""
        if not message.text:
            return
        
        try:
            # Split message into words and check each
            words = message.text.lower().split()
            
            for word in words:
                # Clean word (remove punctuation)
                clean_word = ''.join(char for char in word if char.isalnum() or char == '_')
                
                if not clean_word:
                    continue
                
                # Check if word matches any filter
                filter_response = await db.get_filter(clean_word)
                
                if filter_response:
                    await message.reply(filter_response)
                    logger.info(
                        f"Filter '{clean_word}' triggered by {format_user_info(message.from_user)} "
                        f"in {format_chat_info(message)}"
                    )
                    break  # Only respond to first match
                    
        except Exception as e:
            logger.error(f"Error checking filters: {e}")

# Create handlers instance
handlers = None

def setup_handlers(app: Client):
    """Setup all handlers for the app"""
    global handlers
    handlers = MessageHandlers(app)
    handlers.setup_handlers()
    logger.info("Message handlers setup completed!")

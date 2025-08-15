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
        
        @self.app.on_message(filters.command("testreact") & filters.private)
        async def handle_test_reaction(client: Client, message: Message):
            """Test reaction functionality"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                # Test reaction on the command message itself
                await self.add_reaction(message)
                await message.reply("✅ Test reaction attempted! Check if reaction was added above.")
                
                # Also test different reaction methods
                test_msg = await message.reply("Testing different reaction methods...")
                
                try:
                    await test_msg.react("👍")
                    await asyncio.sleep(1)
                    await test_msg.react("❤️")
                    await message.reply("✅ Direct reaction method works!")
                except Exception as e:
                    await message.reply(f"❌ Direct reaction failed: {e}")
                    
            except Exception as e:
                await message.reply(f"❌ Test reaction failed: {e}")
                logger.error(f"Test reaction error: {e}")
        
        @self.app.on_message(filters.command("test") & filters.group)
        async def handle_group_test(client: Client, message: Message):
            """Test reactions in group"""
            try:
                # Check if user is admin
                if not is_admin(message.from_user.id):
                    return
                
                logger.info(f"Group test command from admin in group {message.chat.id}")
                
                # Test reaction on this message
                await self.add_reaction(message)
                
                # Send a test message and react to it
                test_msg = await message.reply("🧪 Testing bot reactions...")
                await asyncio.sleep(1)
                await self.add_reaction(test_msg)
                
            except Exception as e:
                logger.error(f"Group test error: {e}")
                try:
                    await message.reply(f"❌ Test failed: {e}")
                except:
                    pass
        async def handle_check_group(client: Client, message: Message):
            """Check if a group is properly connected"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            group_id = extract_group_id(message.text)
            if not group_id:
                await message.reply("Usage: `/checkgroup -100xxxxxxxxx`")
                return
            
            try:
                is_connected = await db.is_group_connected(group_id)
                chat = await client.get_chat(group_id)
                
                status_text = f"**Group Status Check:**\n\n"
                status_text += f"**Group:** {chat.title}\n"
                status_text += f"**ID:** `{group_id}`\n"
                status_text += f"**Connected:** {'✅ Yes' if is_connected else '❌ No'}\n"
                
                if is_connected:
                    # Check bot permissions
                    try:
                        bot_member = await client.get_chat_member(group_id, "me")
                        status_text += f"**Bot Status:** {bot_member.status}\n"
                        if bot_member.privileges:
                            status_text += f"**Can Delete Messages:** {'✅' if bot_member.privileges.can_delete_messages else '❌'}\n"
                    except Exception as e:
                        status_text += f"**Permission Check Failed:** {e}\n"
                
                await message.reply(status_text)
                
            except Exception as e:
                await message.reply(f"❌ Error checking group: {e}")
        @self.app.on_message(filters.command("debug") & filters.private)
        async def handle_debug_info(client: Client, message: Message):
            """Get debug information"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                connected_groups = await db.get_connected_groups()
                total_filters = await db.get_all_filters()
                
                debug_text = f"**🔍 Debug Information:**\n\n"
                debug_text += f"**Connected Groups:** {len(connected_groups)}\n"
                debug_text += f"**Active Filters:** {len(total_filters)}\n"
                debug_text += f"**Available Reactions:** {len(Config.REACTIONS)}\n"
                debug_text += f"**Default Reaction:** {Config.DEFAULT_REACTION}\n\n"
                
                if connected_groups:
                    debug_text += "**Connected Groups:**\n"
                    for group in connected_groups[:5]:  # Show first 5
                        debug_text += f"• {group.get('group_title', 'Unknown')} (`{group.get('group_id')}`)\n"
                    if len(connected_groups) > 5:
                        debug_text += f"... and {len(connected_groups) - 5} more\n"
                else:
                    debug_text += "**No groups connected**\n"
                
                debug_text += f"\n**Bot Status:** Online ✅\n"
                debug_text += f"**Logging Level:** {Config.LOG_LEVEL}\n"
                
                await message.reply(debug_text)
                
            except Exception as e:
                await message.reply(f"❌ Debug error: {e}")
                logger.error(f"Debug command error: {e}")
        
        @self.app.on_message(filters.command("logs") & filters.private)
        async def handle_get_logs(client: Client, message: Message):
            """Get recent logs"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                import os
                if os.path.exists('bot.log'):
                    with open('bot.log', 'r') as f:
                        lines = f.readlines()
                        # Get last 20 lines
                        recent_lines = lines[-20:] if len(lines) > 20 else lines
                        logs_text = ''.join(recent_lines)
                        
                    if len(logs_text) > 4000:  # Telegram message limit
                        logs_text = logs_text[-4000:]
                        
                    await message.reply(f"**Recent Logs:**\n```\n{logs_text}\n```")
                else:
                    await message.reply("❌ Log file not found")
                    
            except Exception as e:
                await message.reply(f"❌ Error reading logs: {e}")
        @self.app.on_message(filters.command("testfilter") & filters.private)
        async def handle_test_filter(client: Client, message: Message):
            """Test filter functionality"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                # Get all filters
                all_filters = await db.get_all_filters()
                
                if not all_filters:
                    await message.reply("❌ No filters found in database!")
                    return
                
                test_text = "Testing filters:\n\n"
                
                for filter_data in all_filters[:5]:  # Test first 5 filters
                    keyword = filter_data.get("keyword", "unknown")
                    response = filter_data.get("response", "No response")
                    
                    # Test this filter
                    filter_result = await db.get_filter(keyword)
                    if filter_result:
                        test_text += f"✅ **{keyword}** → {response[:30]}{'...' if len(response) > 30 else ''}\n"
                    else:
                        test_text += f"❌ **{keyword}** → Filter not working\n"
                
                test_text += f"\nTotal filters: {len(all_filters)}"
                await message.reply(test_text)
                
                # Test a simple filter response
                if all_filters:
                    first_filter = all_filters[0]
                    keyword = first_filter.get("keyword")
                    response = first_filter.get("response")
                    
                    await message.reply(f"Testing filter '{keyword}':")
                    await self.check_filters(message.reply_to_message if hasattr(message, 'reply_to_message') else message)
                
            except Exception as e:
                await message.reply(f"❌ Test filter error: {e}")
                logger.error(f"Test filter error: {e}")
        
        @self.app.on_message(filters.command("forcereact") & filters.private)
        async def handle_force_react(client: Client, message: Message):
            """Force test a reaction"""
            if not is_admin(message.from_user.id):
                await message.reply("❌ You are not authorized to use this command.")
                return
            
            try:
                group_id = extract_group_id(message.text)
                if not group_id:
                    await message.reply("Usage: `/forcereact -100xxxxxxxxx`")
                    return
                
                # Check if group is connected
                is_connected = await db.is_group_connected(group_id)
                if not is_connected:
                    await message.reply(f"❌ Group {group_id} is not connected!")
                    return
                
                # Send a test message to the group
                try:
                    test_msg = await client.send_message(
                        chat_id=group_id,
                        text="🧪 **Force Reaction Test**\n\nThis message should get a reaction automatically!"
                    )
                    
                    # Force add reaction
                    await self.add_reaction(test_msg)
                    
                    await message.reply(f"✅ Force reaction test sent to group {group_id}")
                    
                except Exception as e:
                    await message.reply(f"❌ Failed to send test message: {e}")
                
            except Exception as e:
                await message.reply(f"❌ Force react error: {e}")
                logger.error(f"Force react error: {e}")
            """Handle /help command"""
            if is_private_chat(message):
                if not is_admin(message.from_user.id):
                    await message.reply("❌ You are not authorized to use this bot.")
                    return
                
                help_text = get_help_text()
                await message.reply(help_text)
            # Ignore help command in groups
        
        # Message reactions and filters - More comprehensive handler
        @self.app.on_message(~filters.bot & ~filters.service)
        async def handle_all_messages(client: Client, message: Message):
            """Handle all messages for reactions and filters"""
            
            try:
                # Skip if no user (system messages, etc.)
                if not message.from_user:
                    logger.debug("Skipping message with no user")
                    return
                
                # Skip bot messages
                if message.from_user.is_bot:
                    logger.debug("Skipping bot message")
                    return
                
                # Log every message for debugging
                logger.info(f"Received message from {format_user_info(message.from_user)} in {format_chat_info(message)}")
                logger.info(f"Message type: {message.chat.type}, Text: {message.text[:50] if message.text else 'No text'}")
                
                # Handle commands separately - but allow /test in groups
                if message.text and message.text.startswith('/'):
                    command = message.text.split()[0].lower()
                    # Only skip admin commands in private chat, allow /test in groups
                    if command in ['/connect', '/disconnect', '/filter', '/removefilter', '/filters', '/stats', '/help', '/testreact', '/checkgroup', '/debug', '/logs']:
                        if is_private_chat(message):
                            logger.debug(f"Skipping admin command in PM: {command}")
                            return
                    elif command != '/test':  # Allow /test in groups
                        logger.debug(f"Skipping command: {command}")
                        return
                
                # Handle group messages
                if is_group_chat(message):
                    logger.info(f"Processing group message in chat {message.chat.id}")
                    
                    is_connected = await db.is_group_connected(message.chat.id)
                    logger.info(f"Group {message.chat.id} connection status: {is_connected}")
                    
                    if not is_connected:
                        logger.info(f"Group {message.chat.id} is not connected, ignoring message")
                        return
                    
                    logger.info(f"✅ Group is connected! Processing message {message.id}")
                    
                    # Add reaction to message
                    logger.info(f"🎭 Adding reaction to message {message.id}")
                    await self.add_reaction(message)
                    
                    # Check for filters if message has text
                    if message.text:
                        logger.info(f"🔍 Checking filters for text: {message.text[:30]}")
                        await self.check_filters(message)
                    else:
                        logger.info("No text in message, skipping filter check")
                
                # Handle private messages from admins
                elif is_private_chat(message) and is_admin(message.from_user.id):
                    logger.info(f"Processing admin PM: {message.text[:50] if message.text else 'No text'}")
                    
                    # Check for filters in admin PM
                    if message.text:
                        logger.info("🔍 Checking filters in admin PM")
                        await self.check_filters(message)
                else:
                    logger.debug(f"Ignoring message from non-admin in private chat: {message.from_user.id}")
                    
            except Exception as e:
                logger.error(f"❌ Error in handle_all_messages: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def add_reaction(self, message: Message):
        """Add reaction to message"""
        try:
            reaction = get_random_reaction()
            logger.info(f"Attempting to add reaction '{reaction}' to message {message.id}")
            
            # Try the reaction
            await message.react(reaction)
            logger.info(f"✅ Successfully added reaction '{reaction}' to message {message.id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add reaction '{reaction}' to message {message.id}: {e}")
            
            # Try with default reaction
            try:
                logger.info(f"Trying default reaction '{Config.DEFAULT_REACTION}' to message {message.id}")
                await message.react(Config.DEFAULT_REACTION)
                logger.info(f"✅ Successfully added default reaction to message {message.id}")
            except Exception as e2:
                logger.error(f"❌ Failed to add default reaction to message {message.id}: {e2}")
                # Check if it's a permission issue
                if "CHAT_ADMIN_REQUIRED" in str(e2):
                    logger.error("Bot needs admin permissions to add reactions!")
                elif "REACTION_INVALID" in str(e2):
                    logger.error("Reaction emoji is not supported in this chat!")
                else:
                    logger.error(f"Unknown reaction error: {e2}")
    
    async def check_filters(self, message: Message):
        """Check message for filters and respond"""
        if not message.text:
            logger.debug("No text in message for filter check")
            return
        
        try:
            logger.info(f"🔍 Checking filters for message: '{message.text[:50]}'")
            
            # Split message into words and check each
            words = message.text.lower().split()
            logger.info(f"Words to check: {words}")
            
            for word in words:
                # Clean word (remove punctuation)
                clean_word = ''.join(char for char in word if char.isalnum() or char == '_')
                
                if not clean_word:
                    continue
                
                logger.info(f"Checking filter for word: '{clean_word}'")
                
                # Check if word matches any filter
                filter_response = await db.get_filter(clean_word)
                
                if filter_response:
                    logger.info(f"✅ Filter '{clean_word}' matched! Sending response: '{filter_response[:30]}'")
                    await message.reply(filter_response)
                    logger.info(
                        f"Filter '{clean_word}' triggered by {format_user_info(message.from_user)} "
                        f"in {format_chat_info(message)}"
                    )
                    break  # Only respond to first match
                else:
                    logger.debug(f"No filter found for word: '{clean_word}'")
            
            logger.info("Filter check completed")
                    
        except Exception as e:
            logger.error(f"❌ Error checking filters: {e}")
            import traceback
            logger.error(f"Filter check traceback: {traceback.format_exc()}")

# Create handlers instance
handlers = None

def setup_handlers(app: Client):
    """Setup all handlers for the app"""
    global handlers
    handlers = MessageHandlers(app)
    handlers.setup_handlers()
    logger.info("Message handlers setup completed!")

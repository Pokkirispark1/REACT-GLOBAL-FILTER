import logging
import random
import re
from typing import Optional, List
from pyrogram.types import Message, User
from config import Config

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in Config.ADMINS

def extract_group_id(text: str) -> Optional[int]:
    """Extract group ID from connect command"""
    try:
        # Match patterns like -100123456789, -123456789, or 123456789
        pattern = r'(-?\d{10,})'
        match = re.search(pattern, text)
        
        if match:
            group_id = int(match.group(1))
            # Convert to supergroup format if needed
            if not str(group_id).startswith('-100') and group_id > 0:
                group_id = int(f"-100{group_id}")
            return group_id
    except ValueError:
        pass
    
    return None

def get_random_reaction() -> str:
    """Get a random reaction from the list"""
    try:
        return random.choice(Config.REACTIONS)
    except (IndexError, ValueError):
        return Config.DEFAULT_REACTION

def format_user_info(user: User) -> str:
    """Format user information for logging"""
    if not user:
        return "Unknown User"
    
    info = f"User: {user.first_name}"
    if user.last_name:
        info += f" {user.last_name}"
    if user.username:
        info += f" (@{user.username})"
    info += f" (ID: {user.id})"
    
    return info

def format_chat_info(message: Message) -> str:
    """Format chat information for logging"""
    if not message.chat:
        return "Unknown Chat"
    
    info = f"Chat: {message.chat.title or message.chat.first_name or 'Unknown'}"
    info += f" (ID: {message.chat.id})"
    
    return info

def extract_filter_parts(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract keyword and response from filter command"""
    try:
        # Remove /filter command
        parts = text.split(' ', 1)
        if len(parts) < 2:
            return None, None
        
        # Split into keyword and response
        filter_content = parts[1].strip()
        filter_parts = filter_content.split(' ', 1)
        
        if len(filter_parts) < 2:
            return None, None
        
        keyword = filter_parts[0].strip().lower()
        response = filter_parts[1].strip()
        
        # Validate keyword (no spaces, special chars)
        if not re.match(r'^[a-zA-Z0-9_]+$', keyword):
            return None, None
        
        # Validate response length
        if len(response) > Config.MAX_FILTER_LENGTH:
            return None, None
        
        return keyword, response
        
    except Exception as e:
        logger.error(f"Failed to extract filter parts: {e}")
        return None, None

def extract_remove_filter_keyword(text: str) -> Optional[str]:
    """Extract keyword from remove filter command"""
    try:
        parts = text.split(' ', 1)
        if len(parts) < 2:
            return None
        
        keyword = parts[1].strip().lower()
        
        # Validate keyword
        if not re.match(r'^[a-zA-Z0-9_]+$', keyword):
            return None
        
        return keyword
        
    except Exception as e:
        logger.error(f"Failed to extract remove filter keyword: {e}")
        return None

def sanitize_text(text: str) -> str:
    """Sanitize text for database storage"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Limit length
    if len(text) > Config.MAX_FILTER_LENGTH:
        text = text[:Config.MAX_FILTER_LENGTH] + "..."
    
    return text

def is_group_chat(message: Message) -> bool:
    """Check if message is from a group chat"""
    return message.chat.type in ["group", "supergroup"]

def is_private_chat(message: Message) -> bool:
    """Check if message is from a private chat"""
    return message.chat.type == "private"

def format_filters_list(filters: List[dict], page: int = 1, per_page: int = 10) -> str:
    """Format filters list for display"""
    if not filters:
        return "No filters found."
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_filters = filters[start_idx:end_idx]
    
    text = f"**Active Filters** (Page {page}):\n\n"
    
    for i, filter_data in enumerate(page_filters, start=start_idx + 1):
        keyword = filter_data.get("keyword", "unknown")
        response = filter_data.get("response", "No response")
        
        # Truncate long responses
        if len(response) > 50:
            response = response[:47] + "..."
        
        text += f"{i}. **{keyword}** → {response}\n"
    
    total_pages = (len(filters) + per_page - 1) // per_page
    if total_pages > 1:
        text += f"\nPage {page} of {total_pages}"
    
    return text

def get_help_text() -> str:
    """Get help text for users"""
    return """
**Bot Commands:**

**Admin Commands:**
/connect -100xxxxx - Connect bot to a group
/disconnect -100xxxxx - Disconnect bot from a group
/filter keyword response - Add a new filter
/removefilter keyword - Remove a filter
/filters - List all active filters
/stats - Get bot statistics
/help - Show this help message

**How it works:**
1. Add this bot to any group as admin
2. Use /connect command with group ID to activate
3. Bot will react to all messages in connected groups
4. Set global filters that work in all connected groups

**Filter Example:**
/filter hello Hi there! How are you?

When someone types "hello", bot will reply with "Hi there! How are you?"
"""

def get_stats_text(connected_groups: int, total_filters: int) -> str:
    """Get statistics text"""
    return f"""
**📊 Bot Statistics:**

🔗 Connected Groups: {connected_groups}
📝 Active Filters: {total_filters}
🎭 Available Reactions: {len(Config.REACTIONS)}
👑 Total Admins: {len(Config.ADMINS)}

**🚀 Bot is working perfectly!**
"""

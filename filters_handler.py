import re
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import save_filter, get_filter, get_all_filters, delete_filter, get_connected_groups

async def handle_filters(client: Client, message: Message):
    """Handle auto-reply filters in groups"""
    if not message.text:
        return
    
    chat_id = message.chat.id
    text = message.text.lower().strip()
    
    # Check for filter matches
    filter_data = await get_filter(chat_id, text)
    
    if filter_data:
        response = filter_data["response"]
        buttons = filter_data.get("buttons", [])
        
        # Create inline keyboard if buttons exist
        keyboard = None
        if buttons:
            keyboard_buttons = []
            row = []
            
            for button in buttons:
                btn = InlineKeyboardButton(button["text"], url=button["url"])
                row.append(btn)
                
                # If same_line is False or row has 2 buttons, start new row
                if not button.get("same_line", False) or len(row) >= 2:
                    keyboard_buttons.append(row)
                    row = []
            
            # Add remaining buttons if any
            if row:
                keyboard_buttons.append(row)
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        # Send response
        await message.reply_text(response, reply_markup=keyboard)

async def filter_command(client: Client, message: Message):
    """Handle /filter command"""
    try:
        text = message.text
        
        # Parse the command
        if len(message.command) < 3:
            await message.reply_text(
                "Usage: /filter keyword response\n\n"
                "Example: /filter hi Hello there!\n\n"
                "For buttons:\n"
                "/filter hi Hello!\n"
                "[Button 1](buttonurl://example.com)\n"
                "[Button 2](buttonurl://example.com:same)"
            )
            return
        
        keyword = message.command[1].lower()
        
        # Extract response and buttons
        response_text = " ".join(message.command[2:])
        buttons = []
        
        # Parse buttons from the message
        button_pattern = r'\[([^\]]+)\]\(buttonurl://([^)]+)\)'
        button_matches = re.findall(button_pattern, text)
        
        for button_text, button_url in button_matches:
            same_line = button_url.endswith(':same')
            if same_line:
                button_url = button_url.replace(':same', '')
            
            buttons.append({
                "text": button_text,
                "url": button_url,
                "same_line": same_line
            })
            
            # Remove button markup from response
            response_text = re.sub(rf'\[{re.escape(button_text)}\]\(buttonurl://[^)]+\)', '', response_text)
        
        response_text = response_text.strip()
        
        if not response_text:
            await message.reply_text("Response text cannot be empty!")
            return
        
        user_id = message.from_user.id
        
        # Get user's connected groups
        connected_groups = await get_connected_groups()
        
        if not connected_groups:
            await message.reply_text("No groups connected! Use /connect first.")
            return
        
        # Save filter for all connected groups (you can modify this logic)
        for chat_id in connected_groups:
            await save_filter(chat_id, keyword, response_text, buttons)
        
        btn_info = f" with {len(buttons)} button(s)" if buttons else ""
        await message.reply_text(f"Filter '{keyword}' saved{btn_info}!")
        
    except Exception as e:
        await message.reply_text(f"Error saving filter: {str(e)}")

async def list_filters_command(client: Client, message: Message):
    """Handle /filters command"""
    try:
        connected_groups = await get_connected_groups()
        
        if not connected_groups:
            await message.reply_text("No groups connected!")
            return
        
        all_filters = []
        for chat_id in connected_groups:
            filters = await get_all_filters(chat_id)
            all_filters.extend(filters)
        
        if not all_filters:
            await message.reply_text("No filters found!")
            return
        
        filter_list = "**Active Filters:**\n\n"
        for f in all_filters:
            buttons_info = f" ({len(f.get('buttons', []))} buttons)" if f.get('buttons') else ""
            filter_list += f"• `{f['keyword']}`{buttons_info}\n"
        
        await message.reply_text(filter_list)
        
    except Exception as e:
        await message.reply_text(f"Error listing filters: {str(e)}")

async def del_filter_command(client: Client, message: Message):
    """Handle /delfilter command"""
    try:
        if len(message.command) < 2:
            await message.reply_text("Usage: /delfilter keyword")
            return
        
        keyword = message.command[1].lower()
        connected_groups = await get_connected_groups()
        
        deleted_count = 0
        for chat_id in connected_groups:
            if await delete_filter(chat_id, keyword):
                deleted_count += 1
        
        if deleted_count > 0:
            await message.reply_text(f"Filter '{keyword}' deleted from {deleted_count} group(s)!")
        else:
            await message.reply_text(f"Filter '{keyword}' not found!")
            
    except Exception as e:
        await message.reply_text(f"Error deleting filter: {str(e)}")

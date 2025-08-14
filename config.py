import os
from typing import List

class Config:
    # Telegram API Configuration
    API_ID = int(os.environ.get('API_ID', '12345678'))  # Replace with your API ID
    API_HASH = os.environ.get('API_HASH', 'your_api_hash_here')  # Replace with your API hash
    BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')  # Replace with your bot token
    
    # Admin Configuration
    ADMINS = [int(admin) for admin in os.environ.get('ADMINS', '123456789').split()]  # Replace with admin user IDs
    
    # MongoDB Configuration
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')  # Replace with your MongoDB URL
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'telegram_bot_db')  # Replace with your database name
    
    # Bot Configuration
    REACTIONS = os.environ.get('REACTIONS', '🤝 😇 🤗 😍 👍 🎅 😐 🥰 🤩 😱 🤣 😘 👏 😛 😈 🎉 ⚡️ 🫡 🤓 😎 🏆 🔥 🤭 🌚 🆒 👻 😁').split()
    
    # Default reaction if others fail
    DEFAULT_REACTION = "⚡️"
    
    # Bot settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    MAX_FILTER_LENGTH = 1000  # Maximum length for filter responses

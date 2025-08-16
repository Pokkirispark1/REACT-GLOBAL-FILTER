from os import environ

# Configuration variables for the application
class configVars:
    BOT_TOKEN = environ.get("BOT_TOKEN", "7723147652:AAGyF6qIgG8_RGk6dHxfamDbdb1IAubZXxo")
    API_ID = int(environ.get("API_ID", 28723907))
    API_HASH = environ.get("API_HASH", "390ab5f4798822d2a0eb5b85c4fb7d6c")
    LOG_CHANNEL = int(environ.get("LOG_CHANNEL", -1002077780554))
    DB_URI = environ.get("DB_URI", "mongodb+srv://reactionbkots:reactionbkots@cluster0.onptwey.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    ADMINS = list(map(int, environ.get("ADMINS", "1769132732 560951157").split()))
    START_MESSAGE = environ.get("START_MESSAGE", "Hello! I'm an auto-reaction and filter bot. Admins can use /connect <group_id> to connect a group, /filter <keyword> <response> to set a filter, /delfilter <keyword> to delete a filter, and /listfilters to view all filters.")
    CHAT_DATA = {}  # Dictionary for in-memory cache
    R_EMOJIS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏"]  # Fixed invalid emoji

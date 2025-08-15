import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import BadRequest

from config import Config
from database import db
from handlers import setup_handlers

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.app = None
        
    async def initialize(self):
        """Initialize the bot"""
        try:
            # Validate configuration
            if not self.validate_config():
                raise ValueError("Invalid configuration")
            
            # Create Pyrogram client
            self.app = Client(
                "reaction_filter_bot",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=Config.BOT_TOKEN
            )
            
            # Connect to database
            await db.connect()
            
            # Setup message handlers
            setup_handlers(self.app)
            
            logger.info("Bot initialization completed!")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate bot configuration"""
        try:
            # Check required fields
            required_fields = [
                (Config.API_ID, "API_ID"),
                (Config.API_HASH, "API_HASH"),
                (Config.BOT_TOKEN, "BOT_TOKEN"),
                (Config.MONGO_URL, "MONGO_URL"),
                (Config.ADMINS, "ADMINS")
            ]
            
            for value, name in required_fields:
                if not value or (isinstance(value, str) and value.strip() in ['', 'your_api_hash_here', 'your_bot_token_here']):
                    logger.error(f"Missing or invalid {name} in configuration!")
                    return False
            
            # Validate API ID
            if not isinstance(Config.API_ID, int) or Config.API_ID <= 0:
                logger.error("API_ID must be a positive integer!")
                return False
            
            # Validate admins list
            if not Config.ADMINS or not all(isinstance(admin, int) for admin in Config.ADMINS):
                logger.error("ADMINS must be a list of integers!")
                return False
            
            # Validate reactions list
            if not Config.REACTIONS:
                logger.warning("No reactions configured, using default reaction only")
            
            logger.info("Configuration validation passed!")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def start(self):
        """Start the bot"""
        try:
            await self.initialize()
            
            logger.info("Starting Telegram bot...")
            await self.app.start()
            
            # Get bot information
            me = await self.app.get_me()
            logger.info(f"Bot started successfully!")
            logger.info(f"Bot Name: {me.first_name}")
            logger.info(f"Bot Username: @{me.username}")
            logger.info(f"Bot ID: {me.id}")
            
            # Print startup information
            connected_groups = await db.get_connected_groups()
            total_filters = await db.get_all_filters()
            
            logger.info(f"Connected Groups: {len(connected_groups)}")
            logger.info(f"Active Filters: {len(total_filters)}")
            logger.info(f"Total Admins: {len(Config.ADMINS)}")
            logger.info("Bot is ready to receive messages!")
            
            # Print admin information
            logger.info("Authorized Admins:")
            for admin_id in Config.ADMINS:
                logger.info(f"  - Admin ID: {admin_id}")
            
            # Print connected groups information
            if connected_groups:
                logger.info("Connected Groups:")
                for group in connected_groups:
                    logger.info(f"  - {group.get('group_title', 'Unknown')} (ID: {group.get('group_id')})")
            else:
                logger.info("No groups connected yet. Use /connect command to add groups.")
            
            # Print active filters information
            if total_filters:
                logger.info(f"Active Filters: {len(total_filters)} filters loaded")
            else:
                logger.info("No filters configured yet. Use /filter command to add filters.")
            
            print("\n" + "="*50)
            print("🤖 TELEGRAM REACTION & FILTER BOT")
            print("="*50)
            print(f"✅ Bot Username: @{me.username}")
            print(f"✅ Bot ID: {me.id}")
            print(f"✅ Connected Groups: {len(connected_groups)}")
            print(f"✅ Active Filters: {len(total_filters)}")
            print(f"✅ Total Reactions: {len(Config.REACTIONS)}")
            print(f"✅ Authorized Admins: {len(Config.ADMINS)}")
            print("="*50)
            print("🚀 Bot is now ONLINE and ready!")
            print("📝 Check bot.log for detailed logs")
            print("⚡ Use Ctrl+C to stop the bot")
            print("="*50 + "\n")
            
            # Keep the bot running
            await self.app.idle()
            
        except BadRequest as e:
            if "API_ID" in str(e) or "API_HASH" in str(e):
                logger.error("❌ Invalid API credentials! Please check your API_ID and API_HASH.")
                print("❌ ERROR: Invalid API credentials! Please check your .env file.")
            elif "BOT_TOKEN" in str(e) or "token" in str(e).lower():
                logger.error("❌ Invalid BOT_TOKEN! Please check your bot token.")
                print("❌ ERROR: Invalid BOT_TOKEN! Please check your .env file.")
            else:
                logger.error(f"❌ Bad request error: {e}")
                print(f"❌ ERROR: {e}")
        except Exception as e:
            error_msg = str(e).lower()
            if "api_id" in error_msg or "api_hash" in error_msg:
                logger.error("❌ Invalid API credentials! Please check your API_ID and API_HASH.")
                print("❌ ERROR: Invalid API credentials! Please check your .env file.")
            elif "token" in error_msg:
                logger.error("❌ Invalid BOT_TOKEN! Please check your bot token.")
                print("❌ ERROR: Invalid BOT_TOKEN! Please check your .env file.")
            else:
                logger.error(f"❌ Failed to start bot: {e}")
                print(f"❌ ERROR: Failed to start bot: {e}")
            raise
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("Shutting down bot...")
            
            if self.app:
                await self.app.stop()
                logger.info("Pyrogram client stopped!")
            
            await db.disconnect()
            logger.info("Database disconnected!")
            
            logger.info("Bot shutdown completed successfully!")
            print("\n👋 Bot stopped successfully!")
            
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
            print(f"❌ Error during shutdown: {e}")

async def main():
    """Main function to run the bot"""
    bot = TelegramBot()
    
    try:
        print("🚀 Initializing Telegram Reaction & Filter Bot...")
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user (Ctrl+C)")
        print("\n⚠️ Bot interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        print(f"❌ Unexpected error: {e}")
        
    finally:
        await bot.stop()

def check_environment():
    """Check if environment is properly configured"""
    try:
        print("🔍 Checking environment configuration...")
        
        # Check if config can be imported
        from config import Config
        
        # Basic validation
        missing_vars = []
        
        if not Config.API_ID or Config.API_ID == 12345678:
            missing_vars.append("API_ID")
            
        if not Config.API_HASH or Config.API_HASH == 'your_api_hash_here':
            missing_vars.append("API_HASH")
            
        if not Config.BOT_TOKEN or Config.BOT_TOKEN == 'your_bot_token_here':
            missing_vars.append("BOT_TOKEN")
            
        if not Config.ADMINS or Config.ADMINS == [123456789]:
            missing_vars.append("ADMINS")
        
        if missing_vars:
            print(f"❌ Missing or invalid configuration for: {', '.join(missing_vars)}")
            print("📝 Please check your .env file or environment variables")
            return False
        
        print("✅ Environment configuration looks good!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📝 Make sure all required files are present")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    try:
        # Check environment before starting
        if not check_environment():
            print("\n❌ Environment check failed. Please fix the issues above.")
            exit(1)
        
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Bot terminated by user")
        
    except Exception as e:
        logger.error(f"Fatal error in __main__: {e}")
        print(f"❌ Fatal error: {e}")
        exit(1)
        
    finally:
        print("🔄 Cleaning up...")
        # Additional cleanup if needed
        try:
            # Cancel any remaining tasks
            pending = asyncio.all_tasks()
            for task in pending:
                task.cancel()
        except:
            pass
        
        print("✅ Cleanup completed!")

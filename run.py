#!/usr/bin/env python3
"""
Alternative runner for the Telegram bot with automatic environment loading
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    # Try to load environment variables from .env file
    from dotenv import load_dotenv
    env_file = current_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment variables from {env_file}")
    else:
        print(f"⚠️  .env file not found at {env_file}")
        print("Make sure to set environment variables manually or create .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install it with: pip install python-dotenv")

# Import and run the main bot
if __name__ == "__main__":
    try:
        from main import main
        import asyncio
        
        print("🚀 Starting Telegram Reaction & Filter Bot...")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

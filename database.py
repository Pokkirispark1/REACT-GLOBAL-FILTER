from motor.motor_asyncio import AsyncIOMotorClient
import os

# Import from main config (will be set by main.py)
MONGODB_URI = None
DATABASE_NAME = None
client = None
db = None
connections_collection = None
filters_collection = None

def init_database_config(mongodb_uri, database_name):
    """Initialize database configuration"""
    global MONGODB_URI, DATABASE_NAME, client, db, connections_collection, filters_collection
    MONGODB_URI = mongodb_uri
    DATABASE_NAME = database_name
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    connections_collection = db.connections
    filters_collection = db.filters

async def init_db():
    """Initialize database collections"""
    global connections_collection, filters_collection
    if connections_collection is None or filters_collection is None:
        raise Exception("Database not configured. Call init_database_config() first.")
    
    # Create indexes for better performance
    await connections_collection.create_index("chat_id", unique=True)
    await filters_collection.create_index([("chat_id", 1), ("keyword", 1)], unique=True)
    print("Database initialized successfully!")

async def save_connection(chat_id: int, user_id: int):
    """Save group connection"""
    global connections_collection
    await connections_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "admin_id": user_id}},
        upsert=True
    )

async def is_group_connected(chat_id: int) -> bool:
    """Check if group is connected"""
    global connections_collection
    result = await connections_collection.find_one({"chat_id": chat_id})
    return result is not None

async def get_connected_groups():
    """Get all connected groups"""
    global connections_collection
    cursor = connections_collection.find({})
    groups = []
    async for doc in cursor:
        groups.append(doc["chat_id"])
    return groups

async def save_filter(chat_id: int, keyword: str, response: str, buttons: list = None):
    """Save filter to database"""
    global filters_collection
    filter_data = {
        "chat_id": chat_id,
        "keyword": keyword.lower(),
        "response": response,
        "buttons": buttons or []
    }
    
    await filters_collection.update_one(
        {"chat_id": chat_id, "keyword": keyword.lower()},
        {"$set": filter_data},
        upsert=True
    )

async def get_filter(chat_id: int, keyword: str):
    """Get filter by keyword"""
    global filters_collection
    return await filters_collection.find_one({
        "chat_id": chat_id, 
        "keyword": keyword.lower()
    })

async def get_all_filters(chat_id: int):
    """Get all filters for a chat"""
    global filters_collection
    cursor = filters_collection.find({"chat_id": chat_id})
    filters = []
    async for doc in cursor:
        filters.append(doc)
    return filters

async def delete_filter(chat_id: int, keyword: str):
    """Delete filter"""
    global filters_collection
    result = await filters_collection.delete_one({
        "chat_id": chat_id, 
        "keyword": keyword.lower()
    })
    return result.deleted_count > 0

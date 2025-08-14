import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        """Initialize database connection"""
        try:
            self.client = AsyncIOMotorClient(Config.MONGO_URL)
            self.db = self.client[Config.DATABASE_NAME]
            
            # Test connection
            await self.client.admin.command('ismaster')
            logger.info("Database connected successfully!")
            
            # Create indexes for better performance
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Index for connected groups
            await self.db.connected_groups.create_index("group_id", unique=True)
            
            # Index for filters
            await self.db.filters.create_index("keyword")
            
            logger.info("Database indexes created successfully!")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database disconnected!")
    
    # Connected Groups Operations
    async def add_connected_group(self, group_id: int, group_title: str, admin_id: int) -> bool:
        """Add a connected group to database"""
        try:
            group_data = {
                "group_id": group_id,
                "group_title": group_title,
                "admin_id": admin_id,
                "is_active": True
            }
            
            await self.db.connected_groups.update_one(
                {"group_id": group_id},
                {"$set": group_data},
                upsert=True
            )
            
            logger.info(f"Group {group_id} connected successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add connected group: {e}")
            return False
    
    async def remove_connected_group(self, group_id: int) -> bool:
        """Remove a connected group from database"""
        try:
            result = await self.db.connected_groups.delete_one({"group_id": group_id})
            
            if result.deleted_count > 0:
                logger.info(f"Group {group_id} disconnected successfully!")
                return True
            else:
                logger.warning(f"Group {group_id} not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove connected group: {e}")
            return False
    
    async def is_group_connected(self, group_id: int) -> bool:
        """Check if a group is connected"""
        try:
            group = await self.db.connected_groups.find_one({"group_id": group_id, "is_active": True})
            return group is not None
        except Exception as e:
            logger.error(f"Failed to check group connection: {e}")
            return False
    
    async def get_connected_groups(self) -> List[Dict[str, Any]]:
        """Get all connected groups"""
        try:
            cursor = self.db.connected_groups.find({"is_active": True})
            groups = await cursor.to_list(length=None)
            return groups
        except Exception as e:
            logger.error(f"Failed to get connected groups: {e}")
            return []
    
    # Filter Operations
    async def add_filter(self, keyword: str, response: str, admin_id: int) -> bool:
        """Add a new filter to database"""
        try:
            filter_data = {
                "keyword": keyword.lower(),
                "response": response,
                "admin_id": admin_id,
                "is_active": True
            }
            
            await self.db.filters.update_one(
                {"keyword": keyword.lower()},
                {"$set": filter_data},
                upsert=True
            )
            
            logger.info(f"Filter '{keyword}' added successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add filter: {e}")
            return False
    
    async def remove_filter(self, keyword: str) -> bool:
        """Remove a filter from database"""
        try:
            result = await self.db.filters.delete_one({"keyword": keyword.lower()})
            
            if result.deleted_count > 0:
                logger.info(f"Filter '{keyword}' removed successfully!")
                return True
            else:
                logger.warning(f"Filter '{keyword}' not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove filter: {e}")
            return False
    
    async def get_filter(self, keyword: str) -> Optional[str]:
        """Get filter response by keyword"""
        try:
            filter_doc = await self.db.filters.find_one({"keyword": keyword.lower(), "is_active": True})
            return filter_doc["response"] if filter_doc else None
        except Exception as e:
            logger.error(f"Failed to get filter: {e}")
            return None
    
    async def get_all_filters(self) -> List[Dict[str, Any]]:
        """Get all active filters"""
        try:
            cursor = self.db.filters.find({"is_active": True})
            filters = await cursor.to_list(length=None)
            return filters
        except Exception as e:
            logger.error(f"Failed to get all filters: {e}")
            return []
    
    async def search_filters(self, query: str) -> List[Dict[str, Any]]:
        """Search filters by keyword"""
        try:
            cursor = self.db.filters.find({
                "keyword": {"$regex": query.lower(), "$options": "i"},
                "is_active": True
            })
            filters = await cursor.to_list(length=None)
            return filters
        except Exception as e:
            logger.error(f"Failed to search filters: {e}")
            return []

# Global database instance
db = Database()

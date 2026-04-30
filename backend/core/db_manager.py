import redis 
from django.conf import settings 
from django.db import connections 
from django.db.utils import OperationalError 
import logging 
from tenacity import retry, stop_after_attempt, wait_exponential 

logger = logging.getLogger(__name__) 

class DatabaseManager: 
    """Manage database connections with retry logic""" 
    
    def __init__(self): 
        self.redis_client = None 
    
    @retry( 
        stop=stop_after_attempt(5), 
        wait=wait_exponential(multiplier=1, min=4, max=10) 
    ) 
    def init_redis(self): 
        """Initialize Redis connection with retry""" 
        try: 
            self.redis_client = redis.Redis( 
                host=settings.REDIS_CONFIG['host'], 
                port=settings.REDIS_CONFIG['port'], 
                password=settings.REDIS_CONFIG['password'], 
                db=settings.REDIS_CONFIG['db'], 
                decode_responses=True, 
                socket_keepalive=True, 
                socket_connect_timeout=5, 
                retry_on_timeout=True 
            ) 
            # Test connection 
            self.redis_client.ping() 
            logger.info("Redis connection established successfully") 
        except Exception as e: 
            logger.error(f"Failed to connect to Redis: {e}") 
            raise 
    
    def get_redis(self): 
        """Get Redis client instance""" 
        if not self.redis_client: 
            self.init_redis() 
        return self.redis_client 
    
    def check_postgres_health(self): 
        """Check PostgreSQL connection health""" 
        try: 
            connection = connections['default'] 
            connection.cursor() 
            return True 
        except OperationalError as e: 
            logger.error(f"PostgreSQL connection error: {e}") 
            return False 
    
    def close_connections(self): 
        """Close all database connections""" 
        for conn in connections.all(): 
            conn.close_if_unusable_or_obsolete() 
        
        if self.redis_client: 
            self.redis_client.close() 

db_manager = DatabaseManager() 

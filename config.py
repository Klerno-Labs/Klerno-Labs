"""
Comprehensive configuration management for Klerno Labs.
Handles database initialization, cache services, and environment variables.
"""

import os
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles database initialization and management."""
    
    @staticmethod
    def ensure_data_directory() -> Path:
        """Ensure the data directory exists."""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"[OK] Data directory ensured: {data_dir.absolute()}")
        return data_dir
    
    @staticmethod
    def initialize_sqlite_db(db_path: str) -> bool:
        """Initialize SQLite database with required tables."""
        try:
            # Ensure data directory exists
            DatabaseManager.ensure_data_directory()
            
            # Create database file if it doesn't exist
            db_file = Path(db_path)
            if not db_file.exists():
                logger.info(f"🔧 Creating new SQLite database: {db_file.absolute()}")
                
                # Create basic tables
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Monitoring logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS monitoring_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        level TEXT,
                        message TEXT,
                        component TEXT,
                        data TEXT
                    )
                """)
                
                conn.commit()
                conn.close()
                logger.info("[OK] SQLite database initialized with basic tables")
            else:
                logger.info(f"[OK] SQLite database already exists: {db_file.absolute()}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQLite database: {e}")
            return False


class CacheManager:
    """Handles Redis and Memcached connections with graceful fallbacks."""
    
    def __init__(self):
        self.redis_client = None
        self.memcached_client = None
        self.use_redis = self._str_to_bool(os.getenv("USE_REDIS", "false"))
        self.use_memcached = self._str_to_bool(os.getenv("USE_MEMCACHED", "false"))
    
    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ("true", "1", "yes", "on")
    
    def initialize_redis(self) -> bool:
        """Initialize Redis connection with graceful fallback."""
        if not self.use_redis:
            logger.info("[SKIP] Redis disabled in configuration")
            return False
        
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("[OK] Redis connection established")
            return True
        except ImportError:
            logger.warning("⚠️  Redis library not installed, skipping Redis initialization")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Redis not available: {e} - continuing without Redis")
            self.redis_client = None
            return False
    
    def initialize_memcached(self) -> bool:
        """Initialize Memcached connection with graceful fallback."""
        if not self.use_memcached:
            logger.info("[SKIP] Memcached disabled in configuration")
            return False
        
        try:
            import pymemcache.client.base as memcache
            servers = os.getenv("MEMCACHED_SERVERS", "localhost:11211").split(",")
            self.memcached_client = memcache.Client((servers[0].strip(),))
            # Test connection
            self.memcached_client.set("test", "1", expire=1)
            logger.info("[OK] Memcached connection established")
            return True
        except ImportError:
            logger.warning("⚠️  pymemcache not installed, skipping Memcached initialization")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Memcached not available: {e} - continuing without Memcached")
            self.memcached_client = None
            return False


class Settings:
    """Comprehensive application settings with smart defaults."""
    
    def __init__(self):
        # Load from .env if available
        self._load_env_file()
        
        # Core Application Settings
        self.app_env = os.getenv("APP_ENV", "development")
        self.environment = os.getenv("ENVIRONMENT", self.app_env)
        self.debug = self._str_to_bool(os.getenv("DEBUG", "false"))
        
        # Server Configuration
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.workers = int(os.getenv("WORKERS", "1"))
        self.log_level = os.getenv("LOG_LEVEL", "info")
        self.reload = self._str_to_bool(os.getenv("RELOAD", "true"))
        
        # Security Configuration
        self.jwt_secret = os.getenv("JWT_SECRET", "supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef")
        self.secret_key = os.getenv("SECRET_KEY", "klerno_labs_secret_key_2025_very_secure_32_chars_minimum")
        self.api_key = os.getenv("API_KEY", "dev-api-key")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        
        # Database Configuration
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/klerno.db")
        self.db_path = os.getenv("DB_PATH", "./data/klerno.db")
        self.sqlite_path = os.getenv("SQLITE_PATH", "./data/klerno.db")
        
        # Health Check Configuration
        self.healthcheck_path = os.getenv("HEALTHCHECK_PATH", "/healthz")
        self.health_check_endpoint = os.getenv("HEALTH_CHECK_ENDPOINT", "/healthz")
        
        # Backend Configuration
        self.primary_backend_port = int(os.getenv("PRIMARY_BACKEND_PORT", "8000"))
        self.backend_targets = os.getenv("BACKEND_TARGETS", f"localhost:{self.primary_backend_port}")
        
        # Feature Flags
        self.enable_monitoring = self._str_to_bool(os.getenv("ENABLE_MONITORING", "true"))
        self.enable_enterprise_features = self._str_to_bool(os.getenv("ENABLE_ENTERPRISE_FEATURES", "true"))
        self.enable_performance_optimization = self._str_to_bool(os.getenv("ENABLE_PERFORMANCE_OPTIMIZATION", "true"))
        self.enable_security_hardening = self._str_to_bool(os.getenv("ENABLE_SECURITY_HARDENING", "true"))
        
        # Admin Configuration
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@klerno.com")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "SecureAdminPass123!")
        
        # Legacy compatibility
        self.paywall_code = os.getenv("PAYWALL_CODE", "Labs2025")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.risk_threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
        
        # Email Configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
        self.alert_email_from = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
        self.alert_email_to = os.getenv("ALERT_EMAIL_TO", "you@example.com")
        
        # XRPL Settings
        self.xrpl_net = os.getenv("XRPL_NET", "testnet")
        self.destination_wallet = os.getenv("DESTINATION_WALLET", "")
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        
        # Auto-initialize database
        self._initialize_database()
        
        # Initialize cache services
        self._initialize_cache_services()
    
    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ("true", "1", "yes", "on")
    
    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        env_file = Path(".env")
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info("[OK] Loaded environment variables from .env file")
            except ImportError:
                logger.info("⚠️  python-dotenv not installed, loading environment manually")
                self._manual_env_load(env_file)
            except Exception as e:
                logger.warning(f"⚠️  Error loading .env file: {e}")
    
    def _manual_env_load(self, env_file: Path):
        """Manually load environment variables from .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            logger.info("[OK] Manually loaded environment variables from .env file")
        except Exception as e:
            logger.warning(f"⚠️  Error manually loading .env file: {e}")
    
    def _initialize_database(self):
        """Initialize database with auto-creation."""
        try:
            success = self.db_manager.initialize_sqlite_db(self.db_path)
            if success:
                logger.info(f"[OK] Database initialized: {self.db_path}")
            else:
                logger.error(f"❌ Database initialization failed: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
    
    def _initialize_cache_services(self):
        """Initialize cache services with graceful fallbacks."""
        redis_success = self.cache_manager.initialize_redis()
        memcached_success = self.cache_manager.initialize_memcached()
        
        if not redis_success and not memcached_success:
            logger.info("[INFO] Running without cache services (Redis and Memcached disabled/unavailable)")
        
        self.redis_available = redis_success
        self.memcached_available = memcached_success
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "path": self.db_path,
            "initialized": True
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration status."""
        return {
            "redis_enabled": self.cache_manager.use_redis,
            "redis_available": getattr(self, 'redis_available', False),
            "memcached_enabled": self.cache_manager.use_memcached,
            "memcached_available": getattr(self, 'memcached_available', False)
        }
    
    def get_backend_targets(self) -> list:
        """Get list of backend targets."""
        targets = []
        for target in self.backend_targets.split(','):
            target = target.strip()
            if target:
                targets.append(target)
        return targets
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() in ("production", "prod")
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() in ("development", "dev", "local")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

# Log configuration summary
logger.info("[STARTUP] Klerno Labs Configuration Summary:")
logger.info(f"   Environment: {settings.app_env}")
logger.info(f"   Port: {settings.port}")
logger.info(f"   Database: {settings.db_path}")
logger.info(f"   Health Check: {settings.healthcheck_path}")
logger.info(f"   Backend Targets: {settings.get_backend_targets()}")
logger.info(f"   Cache Services: {settings.get_cache_config()}")
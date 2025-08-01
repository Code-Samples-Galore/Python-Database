from functools import wraps
from peewee import *
from loguru import logger
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure loguru
logger.add("logs/database.log", rotation="1 MB", retention="10 days", level="INFO")

# Proxy database that can be configured later
database_proxy = DatabaseProxy()

class BaseModel(Model):
    class Meta:
        database = database_proxy

class Person(BaseModel):
    name = CharField(max_length=100, index=True)
    age = IntegerField()

def configure_database(db_type='sqlite', **kwargs):
    """Configure the database. Supports 'sqlite' or 'mysql'."""
    logger.info(f"Configuring database: type={db_type}, kwargs={kwargs}")
    if db_type == 'sqlite':
        db = SqliteDatabase(kwargs.get('database', 'app.db'), autoconnect=False)
    elif db_type == 'mysql':
        db = MySQLDatabase(
            kwargs.get('database', 'test_db'),
            user=kwargs.get('user', 'root'),
            password=kwargs.get('password', ''),
            host=kwargs.get('host', 'localhost'),
            port=kwargs.get('port', 3306),
            autoconnect=False
        )
    else:
        logger.error(f"Invalid database type: {db_type}")
        raise ValueError("db_type must be 'sqlite' or 'mysql'")

    database_proxy.initialize(db)
    logger.info(f"Database configured successfully: {db}")
    return db

def with_database(func):
    """Decorator to handle database connections."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if database is already connected
        was_closed = database_proxy.is_closed()

        if was_closed:
            logger.debug(f"Opening database connection for function: {func.__name__}")
            database_proxy.connect()
        else:
            logger.debug(f"Using existing database connection for function: {func.__name__}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in function {func.__name__}: {e}")
            raise
        finally:
            # Only close if we opened the connection
            if was_closed and not database_proxy.is_closed():
                logger.debug(f"Closing database connection for function: {func.__name__}")
                database_proxy.close()
    return wrapper

@with_database
def create_tables_if_not_exist():
    """Create tables if they don't exist."""
    # Check if tables already exist
    if database_proxy.table_exists(Person):
        return

    logger.info("Creating tables if they don't exist")
    database_proxy.create_tables([Person], safe=True)
    logger.info("Tables created successfully")

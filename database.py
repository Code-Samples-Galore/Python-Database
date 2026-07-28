"""Database models and connection management."""

from functools import wraps

from loguru import logger
from peewee import (
    CharField,
    DatabaseProxy,
    IntegerField,
    Model,
    MySQLDatabase,
    SqliteDatabase,
)

from logging_config import setup_logging

setup_logging()

# Longest name the schema accepts. SQLite ignores VARCHAR limits while MySQL
# in strict mode rejects overflow, so this is enforced in Python too.
MAX_NAME_LENGTH = 100

# Keyword names whose values must never reach the log files.
_SECRET_KEYS = frozenset({"password", "passwd", "pwd", "secret", "token"})

# Proxy database that can be configured later
database_proxy = DatabaseProxy()


def _redact(kwargs):
    """Return a copy of *kwargs* with secret values masked, safe for logging."""
    return {
        key: "***" if key.lower() in _SECRET_KEYS else value
        for key, value in kwargs.items()
    }


class BaseModel(Model):
    class Meta:
        database = database_proxy


class Person(BaseModel):
    name = CharField(max_length=MAX_NAME_LENGTH, index=True)
    age = IntegerField()

    def validate(self):
        """Reject values the two backends would treat differently.

        SQLite silently stores over-long names and negative ages; MySQL in
        strict mode raises on the former. Validating here keeps both backends
        behaving identically.
        """
        name = (self.name or "").strip()
        if not name:
            raise ValueError("name must not be empty")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(
                f"name must be at most {MAX_NAME_LENGTH} characters (got {len(name)})"
            )
        if self.age is None or int(self.age) < 0:
            raise ValueError("age must be a non-negative integer")
        self.name = name

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)


def configure_database(db_type='sqlite', **kwargs):
    """Configure the database. Supports 'sqlite' or 'mysql'."""
    logger.info("Configuring database: type={}, kwargs={}", db_type, _redact(kwargs))
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
        logger.error("Invalid database type: {}", db_type)
        raise ValueError("db_type must be 'sqlite' or 'mysql'")

    database_proxy.initialize(db)
    logger.info("Database configured successfully: {}", type(db).__name__)
    return db


def with_database(func):
    """Decorator to handle database connections."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if database_proxy.obj is None:
            raise RuntimeError(
                "Database is not configured. Call configure_database() first."
            )

        # Only the outermost decorated call owns the connection, so nested
        # calls neither reconnect nor close it out from under the caller.
        was_closed = database_proxy.is_closed()

        if was_closed:
            logger.debug("Opening database connection for function: {}", func.__name__)
            database_proxy.connect()
        else:
            logger.debug("Using existing database connection for function: {}", func.__name__)

        try:
            # atomic() nests as a savepoint, so a failure part-way through a
            # multi-statement function rolls back instead of half-committing.
            with database_proxy.atomic():
                result = func(*args, **kwargs)
            logger.debug("Function {} executed successfully", func.__name__)
            return result
        except Exception as e:
            logger.error("Error in function {}: {}", func.__name__, e)
            raise
        finally:
            # Only close if we opened the connection
            if was_closed and not database_proxy.is_closed():
                logger.debug("Closing database connection for function: {}", func.__name__)
                database_proxy.close()
    return wrapper


@with_database
def create_tables_if_not_exist():
    """Create tables if they don't exist."""
    logger.info("Creating tables if they don't exist")
    database_proxy.create_tables([Person], safe=True)
    logger.info("Tables created successfully")

from functools import wraps
from peewee import *

# Proxy database that can be configured later
database_proxy = DatabaseProxy()

class BaseModel(Model):
    class Meta:
        database = database_proxy

class Person(BaseModel):
    name = CharField(max_length=100)
    age = IntegerField()

def configure_database(db_type='sqlite', **kwargs):
    """Configure the database. Supports 'sqlite' or 'mysql'."""
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
        raise ValueError("db_type must be 'sqlite' or 'mysql'")

    database_proxy.initialize(db)
    return db

def with_database(func):
    """Decorator to handle database connections."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if database is already connected
        was_closed = database_proxy.is_closed()

        if was_closed:
            database_proxy.connect()

        try:
            return func(*args, **kwargs)
        finally:
            # Only close if we opened the connection
            if was_closed and not database_proxy.is_closed():
                database_proxy.close()
    return wrapper

@with_database
def create_tables_if_not_exist():
    """Create tables if they don't exist."""
    database_proxy.create_tables([Person], safe=True)

import pytest
from unittest.mock import patch
from peewee import SqliteDatabase
from database import Person, database_proxy, configure_database, with_database, create_tables_if_not_exist

@pytest.fixture
def in_memory_db():
    """Create an in-memory database for testing."""
    test_db = SqliteDatabase(':memory:', autoconnect=False)
    database_proxy.initialize(test_db)
    test_db.connect()
    test_db.create_tables([Person], safe=True)
    yield test_db
    test_db.close()

def test_person_creation(in_memory_db):
    """Test creating a person in the database."""
    person = Person.create(name="John Doe", age=30)
    assert person.name == "John Doe"
    assert person.age == 30
    assert person.id is not None

def test_person_listing(in_memory_db):
    """Test listing persons from the database."""
    Person.create(name="Alice", age=25)
    Person.create(name="Bob", age=35)

    persons = list(Person.select())
    assert len(persons) == 2
    assert persons[0].name == "Alice"
    assert persons[1].name == "Bob"

def test_with_database_decorator(in_memory_db):
    """Test the database connection decorator."""
    @with_database
    def create_test_person():
        return Person.create(name="Test Person", age=40)

    person = create_test_person()
    assert person.name == "Test Person"
    assert person.age == 40

def test_configure_sqlite_database():
    """Test configuring SQLite database."""
    db = configure_database('sqlite', database='test.db')
    assert isinstance(db, SqliteDatabase)

def test_configure_mysql_database():
    """Test configuring MySQL database."""
    from peewee import MySQLDatabase
    db = configure_database('mysql', database='test_db', user='test', password='test')
    assert isinstance(db, MySQLDatabase)

def test_invalid_database_type():
    """Test invalid database type raises error."""
    with pytest.raises(ValueError):
        configure_database('invalid_type')

def test_nested_with_database_decorators(in_memory_db):
    """Test that nested with_database decorators only open one connection."""

    @with_database
    def inner_function():
        return Person.create(name="Inner Person", age=25)

    @with_database
    def outer_function():
        # Ensure tables exist when we reconnect
        create_tables_if_not_exist()
        person1 = Person.create(name="Outer Person", age=30)
        person2 = inner_function()
        return person1, person2

    # Start with closed connection
    if not in_memory_db.is_closed():
        in_memory_db.close()

    # Track connection calls using mock
    with patch.object(in_memory_db, 'connect', wraps=in_memory_db.connect) as mock_connect, \
         patch.object(in_memory_db, 'close', wraps=in_memory_db.close) as mock_close:

        person1, person2 = outer_function()

        # Should have called connect only once
        assert mock_connect.call_count == 1
        # Should have called close only once
        assert mock_close.call_count == 1
        assert person1.name == "Outer Person"
        assert person2.name == "Inner Person"

import pytest
from unittest.mock import patch
from peewee import SqliteDatabase

from database import (
    MAX_NAME_LENGTH,
    Person,
    _redact,
    configure_database,
    create_tables_if_not_exist,
    database_proxy,
    with_database,
)


@pytest.fixture(autouse=True)
def restore_proxy():
    """configure_database() mutates a module global; put it back afterwards.

    Without this, a test that configures MySQL leaves every later test
    pointing at an unreachable server.
    """
    original = database_proxy.obj
    yield
    database_proxy.initialize(original)


@pytest.fixture
def in_memory_db():
    """Create an in-memory database for testing."""
    test_db = SqliteDatabase(':memory:', autoconnect=False)
    database_proxy.initialize(test_db)
    test_db.connect()
    test_db.create_tables([Person], safe=True)
    yield test_db
    if not test_db.is_closed():
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

    # Explicit ordering: row order is not guaranteed without ORDER BY.
    persons = list(Person.select().order_by(Person.id))
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
        # Closing an in-memory database discards it, so rebuild the schema.
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


def test_unconfigured_database_raises_clear_error():
    """with_database should explain itself instead of leaking a Proxy error."""
    database_proxy.initialize(None)

    @with_database
    def noop():
        return None

    with pytest.raises(RuntimeError, match="configure_database"):
        noop()


def test_redact_masks_secret_values():
    """Secrets must never be handed to the logger."""
    redacted = _redact({"user": "admin", "password": "hunter2", "host": "db"})
    assert redacted == {"user": "admin", "password": "***", "host": "db"}


def test_configure_database_does_not_log_password():
    """The MySQL password must not reach the log sinks."""
    from loguru import logger

    captured = []
    sink_id = logger.add(captured.append, level="DEBUG")
    try:
        configure_database(
            'mysql', database='prod', user='admin', password='SuperSecret123!'
        )
    finally:
        logger.remove(sink_id)

    messages = "".join(captured)
    assert "SuperSecret123!" not in messages
    assert "***" in messages


@pytest.mark.parametrize(
    "name, age",
    [
        ("", 30),
        ("   ", 30),
        ("X" * (MAX_NAME_LENGTH + 1), 30),
        ("Valid Name", -1),
    ],
)
def test_person_rejects_invalid_values(in_memory_db, name, age):
    """Validation is enforced in Python so SQLite and MySQL agree."""
    with pytest.raises(ValueError):
        Person.create(name=name, age=age)

    assert Person.select().count() == 0


def test_person_name_is_stripped(in_memory_db):
    """Surrounding whitespace is trimmed before it reaches the database."""
    person = Person.create(name="  Padded Name  ", age=20)
    assert person.name == "Padded Name"


def test_with_database_rolls_back_on_error(in_memory_db):
    """A failure part-way through a decorated function must not half-commit."""

    @with_database
    def two_writes_then_fail():
        Person.create(name="First", age=1)
        Person.create(name="Second", age=2)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        two_writes_then_fail()

    assert Person.select().count() == 0

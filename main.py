"""CLI application entry point."""

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from database import (
    Person,
    configure_database,
    create_tables_if_not_exist,
    with_database,
)
from logging_config import setup_logging

setup_logging()

DEFAULT_DATABASE = "persons.db"

app = typer.Typer(help="Manage a person database.")
console = Console()

# Set by the callback, consumed lazily by each command so that --help never
# touches the database.
_database_path = DEFAULT_DATABASE
_ready = False


@app.callback()
def configure(
    database: str = typer.Option(
        DEFAULT_DATABASE, "--database", help="SQLite database file to use."
    ),
):
    """Manage a person database."""
    global _database_path, _ready
    _database_path = database
    _ready = False


def _ensure_database():
    """Connect and create the schema on first real command invocation."""
    global _ready
    if _ready:
        return
    logger.info("Starting application")
    configure_database('sqlite', database=_database_path)
    create_tables_if_not_exist()
    _ready = True


@app.command()
def create(name: str, age: int):
    """Create a new person in the database."""
    _ensure_database()
    logger.info("Starting person creation process with name={}, age={}", name, age)

    try:
        person = _create_person(name, age)
        logger.info("Person created successfully: {}, age {}", person.name, person.age)
        console.print(f"✅ Created person: {person.name}, age {person.age}", style="green")
    except ValueError as e:
        logger.error("Invalid person data: {}", e)
        console.print(f"❌ Invalid input: {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("Failed to create person: {}", e)
        console.print(f"❌ Failed to create person: {e}", style="red")
        raise typer.Exit(1)


@with_database
def _create_person(name, age):
    return Person.create(name=name, age=age)


@app.command("list")
def list_persons(
    limit: int = typer.Option(
        None, "--limit", help="Maximum number of persons to show."
    ),
    offset: int = typer.Option(0, "--offset", help="Number of persons to skip."),
):
    """List all persons in the database."""
    _ensure_database()
    logger.info("Listing persons (limit={}, offset={})", limit, offset)
    try:
        _print_persons(limit, offset)
    except Exception as e:
        logger.error("Failed to list persons: {}", e)
        console.print(f"❌ Failed to list persons: {e}", style="red")
        raise typer.Exit(1)


@with_database
def _print_persons(limit, offset):
    query = Person.select().order_by(Person.id)
    if offset:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    table = Table(title="Persons")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Age", justify="right", style="green")

    # iterator() streams rows straight off the cursor rather than caching
    # every model instance, so memory stays flat on large tables.
    count = 0
    for person in query.iterator():
        table.add_row(str(person.id), person.name, str(person.age))
        count += 1

    if count == 0:
        logger.info("No persons found in database")
        console.print("No persons found in the database.", style="yellow")
        return

    logger.info("Found {} persons in database", count)
    console.print(table)


if __name__ == "__main__":
    app()

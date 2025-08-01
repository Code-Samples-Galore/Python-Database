import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from loguru import logger
import os
from database import Person, configure_database, with_database, create_tables_if_not_exist

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure loguru for main application
logger.add("logs/app.log", rotation="1 MB", retention="10 days", level="INFO")

app = typer.Typer()
console = Console()

# Configure SQLite database by default
logger.info("Starting application")
configure_database('sqlite', database='persons.db')

# Create tables if they don't exist
create_tables_if_not_exist()

@app.command()
@with_database
def create(name: str, age: int):
    """Create a new person in the database."""
    logger.info(f"Starting person creation process with name={name}, age={age}")

    try:
        person = Person.create(name=name, age=age)
        logger.info(f"Person created successfully: {person.name}, age {person.age}")
        console.print(f"✅ Created person: {person.name}, age {person.age}", style="green")
    except Exception as e:
        logger.error(f"Failed to create person: {e}")
        console.print(f"❌ Failed to create person: {e}", style="red")
        raise typer.Exit(1)

@app.command()
@with_database
def list():
    """List all persons in the database."""
    logger.info("Listing all persons")
    try:
        persons = Person.select()

        if not persons:
            logger.info("No persons found in database")
            console.print("No persons found in the database.", style="yellow")
            return

        logger.info(f"Found {len(persons)} persons in database")
        table = Table(title="Persons")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Age", justify="right", style="green")

        for person in persons:
            table.add_row(str(person.id), person.name, str(person.age))

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to list persons: {e}")
        console.print(f"❌ Failed to list persons: {e}", style="red")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from database import Person, configure_database, with_database, create_tables_if_not_exist

app = typer.Typer()
console = Console()

# Configure SQLite database by default
configure_database('sqlite', database='persons.db')

# Create tables if they don't exist
create_tables_if_not_exist()

@app.command()
@with_database
def create():
    """Create a new person in the database."""
    name = Prompt.ask("Enter person's name")
    age = typer.prompt("Enter person's age", type=int)

    person = Person.create(name=name, age=age)
    console.print(f"✅ Created person: {person.name}, age {person.age}", style="green")

@app.command()
@with_database
def list():
    """List all persons in the database."""
    persons = Person.select()

    if not persons:
        console.print("No persons found in the database.", style="yellow")
        return

    table = Table(title="Persons")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Age", justify="right", style="green")

    for person in persons:
        table.add_row(str(person.id), person.name, str(person.age))

    console.print(table)

if __name__ == "__main__":
    app()

# 🗄️ Peewee Database Example

A Python CLI application for managing a person database with support for SQLite and MySQL backends. Built with Peewee ORM, Typer CLI framework, and Rich for beautiful terminal output.

## ⚙️ Installation

### 📋 Prerequisites

- Python 3.10+ (required by the pinned `typer`/`rich` versions)
- pip

### 📦 Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

For MySQL support, also install:

```bash
pip install PyMySQL
```

## 🚀 Usage

### 🖥️ CLI Commands

#### ➕ Create a Person

```bash
python main.py create "John Doe" 30
```

#### 📃 List All Persons

```bash
python main.py list
```

Large tables can be paged through:

```bash
python main.py list --limit 20 --offset 40
```

#### 🗄️ Choosing a Database File

The default database file is `persons.db`. Override it with the global `--database` option, which must come before the subcommand:

```bash
python main.py --database ./other.db list
```

The database file is opened lazily, so `--help` never creates one.

### ✅ Validation Rules

`Person` is validated in Python on every save, so SQLite and MySQL behave the same way:

- `name` must be non-empty after stripping whitespace
- `name` must be at most 100 characters
- `age` must be a non-negative integer

Invalid input exits with status `1` and leaves the database untouched. Because
Click treats a leading `-` as an option, pass `--` before a negative value:
`python main.py create -- "Name" -1`.

### 🗃️ Database Configuration

The application uses SQLite by default with a file named `persons.db`. You can configure different database backends in the code:

#### 🐍 SQLite Configuration

```python
configure_database('sqlite', database='my_app.db')
```

#### 🐬 MySQL Configuration

```python
configure_database('mysql', 
                  database='my_db',
                  user='username',
                  password='password',
                  host='localhost',
                  port=3306)
```

### 🛠️ Database Functions

#### `configure_database(db_type, **kwargs)`

Configure the database connection. Credential-bearing keys (`password`, `token`, …) are masked before the configuration is logged.

**Parameters:**
- `db_type`: Either 'sqlite' or 'mysql'
- `**kwargs`: Database-specific configuration options

#### `@with_database`

Decorator that automatically manages database connections for functions.

```python
@with_database
def my_database_function():
    # Database operations here
    person = Person.create(name="Example", age=25)
    return person
```

Behaviour:

- Only the outermost decorated call opens and closes the connection, so nested decorated functions reuse it.
- The wrapped call runs inside `atomic()`, so a failure part-way through several writes rolls the whole thing back.
- Calling a decorated function before `configure_database()` raises `RuntimeError` with an actionable message.

#### `create_tables_if_not_exist()`

Creates database tables if they don't already exist.

## 🗂️ Project Structure

```
Python-Database/
├── database.py          # Database models and connection management
├── logging_config.py    # Shared Loguru sink configuration
├── main.py              # CLI application entry point
├── requirements.txt     # Python dependencies
├── pytest.ini           # Test configuration (puts repo root on sys.path)
├── README.md            # This file
├── CLAUDE.md            # Guidance for Claude Code
├── LICENSE              # MIT license
├── .gitignore
├── tests/
│   ├── conftest.py      # Redirects test logs away from logs/
│   ├── test_database.py # Model, connection and validation tests
│   ├── test_logging_config.py # Log routing and log-directory tests
│   └── test_main.py     # CLI tests
└── logs/                # Application logs (created automatically, gitignored)
    ├── app.log
    └── database.log
```

## 📝 Logging

The application uses Loguru for comprehensive logging:

- **Application logs**: `logs/app.log` — records emitted by the CLI
- **Database logs**: `logs/database.log` — records emitted by `database.py`

`logs/` sits next to the source files, not in the current working directory, so
logs always land in the same place no matter where the CLI is invoked from.

Loguru's `logger` is a single process-wide object, so every sink receives every
record unless it is filtered. `logging_config.setup_logging()` applies that
filter, configures a stderr sink, and is idempotent so repeated imports do not
stack duplicate handlers.

Logs are automatically rotated (1 MB) and retained for 10 days.

Two environment variables adjust logging:

| Variable | Default | Effect |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Minimum level for the console and file sinks |
| `LOG_DIR` | `logs/` beside the source | Directory the log files are written to |

Database passwords are redacted before being logged.

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=database --cov=main --cov=logging_config --cov-report=html
```

## 📄 License

MIT License

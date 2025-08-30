# 🗄️ Peewee Database Example

A Python CLI application for managing a person database with support for SQLite and MySQL backends. Built with Peewee ORM, Typer CLI framework, and Rich for beautiful terminal output.

## ⚙️ Installation

### 📋 Prerequisites

- Python 3.7+
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

Configure the database connection.

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

#### `create_tables_if_not_exist()`

Creates database tables if they don't already exist.

## 🗂️ Project Structure

```
Database/
├── database.py          # Database models and connection management
├── main.py              # CLI application entry point
├── README.md            # This file
├── tests/
│   └── test_database.py # Test suite
└── logs/                # Application logs (created automatically)
    ├── app.log
    └── database.log
```

## 📝 Logging

The application uses Loguru for comprehensive logging:

- **Application logs**: `logs/app.log`
- **Database logs**: `logs/database.log`

Logs are automatically rotated (1 MB) and retained for 10 days.

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=database --cov-report=html
```

## 📄 License

MIT License

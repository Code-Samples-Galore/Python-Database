# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

A small Typer CLI over a Peewee ORM `Person` table, with Rich for terminal
output and Loguru for logging. SQLite is the default backend; MySQL is
supported through the same `configure_database()` entry point.

Four modules, no package layout — everything is imported from the repo root:

| File | Role |
| --- | --- |
| `database.py` | `Person` model, `configure_database()`, `with_database` decorator |
| `logging_config.py` | Single source of truth for Loguru sinks |
| `main.py` | Typer CLI (`create`, `list`) |
| `tests/` | `test_database.py`, `test_main.py` |

## Commands

```bash
pip install -r requirements.txt   # install deps
pytest                            # run the suite (testpaths=tests)
pytest tests/test_main.py -v      # single file
python main.py --help             # CLI help (does not touch the database)
python main.py create "Ada" 36
python main.py list --limit 20 --offset 40
```

`pytest.ini` sets `pythonpath = .`. Without it, pytest's default `prepend`
import mode only puts `tests/` on `sys.path` and every test fails with
`ModuleNotFoundError: No module named 'database'`. Requires pytest >= 7.0.

## Architecture notes

### Connection handling

`database_proxy` is a Peewee `DatabaseProxy` initialised at runtime by
`configure_database()`, which lets the models be defined before a backend is
chosen. Anything that touches the database goes through `@with_database`:

- Only the **outermost** decorated call opens and closes the connection —
  `was_closed` is captured on entry and the `finally` block closes only if that
  call opened it. Nested decorated functions reuse the open connection.
  `tests/test_database.py::test_nested_with_database_decorators` asserts
  exactly one `connect()`/`close()` pair; keep it passing.
- The wrapped call runs inside `database_proxy.atomic()` so partial failures
  roll back rather than half-committing.
- It raises `RuntimeError` when the proxy is uninitialised, instead of letting
  Peewee surface `AttributeError: Cannot use uninitialized Proxy.`

### Loguru is a process-wide singleton

Every sink added to `logger` receives **every** record. Adding an `app.log`
sink and a `database.log` sink without a `filter` writes an identical copy of
everything to both — that was a real bug here. `logging_config.setup_logging()`
owns all sink setup, routes records by module name, and is guarded by a
`_configured` flag so repeated imports do not stack handlers. Add sinks there,
not in `database.py` or `main.py`.

`configure_database()` logs its kwargs, so it runs them through `_redact()`
first. If you add a credential-bearing keyword, add its name to `_SECRET_KEYS`.

### Deliberate choices — don't undo these

- **No import-time database work in `main.py`.** `configure_database()` and
  `create_tables_if_not_exist()` are called from `_ensure_database()`, invoked
  by each command body. Moving them back to module scope makes `--help` create
  `persons.db` and opens a connection on every invocation. Two tests in
  `test_main.py` guard this.
- **The list command function is `list_persons`, registered as
  `@app.command("list")`.** Naming it `list` shadows the builtin at module
  scope.
- **CLI commands are thin wrappers.** The `@with_database` work lives in
  private helpers (`_create_person`, `_print_persons`) so the decorator never
  has to interact with Typer's signature introspection.
- **`_print_persons` uses `.iterator()`.** Peewee caches every model instance
  of a plain `select()`; on 50k rows that measured 31 MiB peak versus 0.01 MiB
  with `.iterator()`. Use `--limit`/`--offset` for bounded output.

### Validation

`Person.validate()` runs from `Person.save()`, so it covers `create()` too.
It rejects empty/whitespace names, names over `MAX_NAME_LENGTH` (100), and
negative ages, and strips surrounding whitespace. The checks live in Python
rather than in DDL constraints because SQLite ignores `VARCHAR` limits while
MySQL in strict mode rejects overflow — validating here keeps the backends
consistent and works against pre-existing schemas.

## Testing conventions

- `restore_proxy` in `test_database.py` is an autouse fixture that snapshots
  and restores `database_proxy.obj`. `configure_database()` mutates a module
  global, so without it the MySQL config test leaves later tests pointing at an
  unreachable server. Any new test that calls `configure_database()` needs this
  in scope.
- `in_memory_db` uses `:memory:`, which is **discarded when the connection
  closes**. A test that closes the connection mid-way has to recreate the
  schema before using it again.
- Assert row order only with an explicit `order_by()`.
- CLI tests use `typer.testing.CliRunner` and a `tmp_path` database, and reset
  `main._ready` / `main._database_path` between tests.
- `tests/conftest.py` points `LOG_DIR` at a temp directory. It has to run
  before any test module is imported, because `logging_config` reads the
  variable at import time.

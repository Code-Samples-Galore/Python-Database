import os
import tempfile

# logging_config reads LOG_DIR at import time, and importing `database` from a
# test module triggers that import. Redirect it here — before any test module
# is imported — so running the suite does not append to the real logs/.
os.environ.setdefault(
    "LOG_DIR", os.path.join(tempfile.gettempdir(), "python-database-test-logs")
)

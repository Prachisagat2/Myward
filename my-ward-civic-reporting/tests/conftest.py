import os
import tempfile

# Must be set BEFORE the app is imported so tests use a throwaway DB/upload dir.
_tmp = tempfile.mkdtemp(prefix="myward-test-")
os.environ["MYWARD_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MYWARD_UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ.pop("MYWARD_ADMIN_KEY", None)

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

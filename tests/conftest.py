# =========================================
# تهيئة الاختبارات: قاعدة بيانات مؤقتة معزولة لكل جلسة اختبار
# التشغيل: pytest
# =========================================
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# قاعدة بيانات مؤقتة قبل استيراد أي وحدة من erp
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["ERP_DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ERP_MQTT_BROKER", None)

from fastapi.testclient import TestClient  # noqa: E402

from erp.main import app  # noqa: E402
from erp.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    seed()
    yield
    os.unlink(_tmp_db.name)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

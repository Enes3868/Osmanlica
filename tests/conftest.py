import sys
from pathlib import Path

# Testlerin proje kökündeki modülleri (checker, app) bulabilmesi için.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

TESTLER = Path(__file__).resolve().parent
VERI = TESTLER.parent / "data"


@pytest.fixture
def istemci(tmp_path):
    """Flask test istemcisi: küçük örnek veri ve geçici veritabanıyla; data/sozluk.db'ye dokunmaz."""
    import app as uygulama

    uygulama.app.config.update(
        TESTING=True,
        SOZLUK_DB=tmp_path / "test.db",
        VERI_DOSYALARI=[VERI / "sema.sql", TESTLER / "veri" / "ornek_veri.sql"],
    )
    with uygulama.app.test_client() as c:
        yield c

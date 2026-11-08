import sys
from pathlib import Path

# Testlerin proje kökündeki modülleri (checker, app) bulabilmesi için.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

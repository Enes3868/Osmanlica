"""Sunucu (alwaysdata, uWSGI) için giriş noktası.

uWSGI varsayılan olarak "application" adlı nesneyi arar.
Site modu ve anahtarlar ortam değişkenleriyle verilir (bkz. YAYIN.md).
"""

from app import app as application  # noqa: F401

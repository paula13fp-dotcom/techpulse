from __future__ import annotations
"""Database engine and session management."""
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection

from techpulse.config.settings import settings
from techpulse.database.models import metadata

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{settings.DB_PATH}",
            connect_args={"check_same_thread": False},
        )
        # Enable WAL mode and foreign keys on every connection
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    return _engine


def init_db():
    """Create all tables and insert seed data."""
    engine = get_engine()
    metadata.create_all(engine)
    _seed(engine)


def _seed(engine):
    """Insert static lookup data if not present."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO sources (name, display_name, base_url) VALUES
            -- Fuentes originales
            ('reddit',      'Reddit',        'https://www.reddit.com'),
            ('youtube',     'YouTube',       'https://www.youtube.com'),
            ('xda',         'XDA Forums',    'https://xdadevelopers.com'),
            ('gsmarena',    'GSMArena',      'https://www.gsmarena.com'),
            ('tiktok',      'TikTok',        'https://www.tiktok.com'),
            ('x',           'X (Twitter)',   'https://x.com'),
            -- Blogs ES (originales)
            ('xataka',         'Xataka',           'https://www.xataka.com'),
            ('xatakamovil',    'Xataka Movil',     'https://www.xatakamovil.com'),
            ('muycomputer',    'MuyComputer',      'https://www.muycomputer.com'),
            ('andro4all',      'Andro4all',        'https://andro4all.com'),
            ('hipertextual',   'Hipertextual',     'https://hipertextual.com'),
            ('applesfera',     'Applesfera',       'https://www.applesfera.com'),
            -- Blogs ES (nuevos)
            ('hardzone',       'Hardzone',         'https://hardzone.es'),
            ('tuexperto',      'TuExperto',        'https://www.tuexperto.com'),
            ('iphoneros',      'iPhoneros',        'https://iphoneros.com'),
            -- Leaks/rumores EN (nuevos)
            ('9to5mac',          '9to5Mac',           'https://9to5mac.com'),
            ('9to5google',       '9to5Google',        'https://9to5google.com'),
            ('macrumors',        'MacRumors',         'https://www.macrumors.com'),
            ('androidauthority', 'Android Authority', 'https://www.androidauthority.com'),
            ('wccftech',         'Wccftech',          'https://wccftech.com'),
            ('theverge',         'The Verge',         'https://www.theverge.com'),
            ('sammobile',        'SamMobile',         'https://www.sammobile.com'),
            ('androidpolice',    'Android Police',    'https://www.androidpolice.com'),
            ('phandroid',        'Phandroid',         'https://phandroid.com'),
            ('techradar',        'TechRadar',         'https://www.techradar.com')
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO device_categories (slug, name) VALUES
            ('phones',       'Móviles'),
            ('smartwatches', 'Smartwatches'),
            ('tablets',      'Tablets')
        """))
        # Seed known products
        _seed_products(conn)


def _seed_products(conn: Connection):
    from techpulse.config.constants import PRODUCT_KEYWORDS
    import json

    brand_map = {
        "Apple": ["iphone", "ipad", "apple watch"],
        "Samsung": ["samsung", "galaxy"],
        "Google": ["pixel"],
        "OnePlus": ["oneplus"],
        "Xiaomi": ["xiaomi"],
        "Nothing": ["nothing phone"],
    }

    category_rows = conn.execute(text("SELECT id, slug FROM device_categories")).fetchall()
    cat_map = {row.slug: row.id for row in category_rows}

    for keyword, canonical in PRODUCT_KEYWORDS.items():
        brand = "Unknown"
        for b, patterns in brand_map.items():
            if any(p in keyword.lower() for p in patterns):
                brand = b
                break

        category_id = cat_map.get("phones")
        if any(w in keyword.lower() for w in ["watch", "wear"]):
            category_id = cat_map.get("smartwatches")
        elif any(w in keyword.lower() for w in ["ipad", "tablet", "tab"]):
            category_id = cat_map.get("tablets")

        conn.execute(text("""
            INSERT OR IGNORE INTO products (canonical_name, brand, category_id, aliases)
            VALUES (:name, :brand, :cat_id, :aliases)
        """), {
            "name": canonical,
            "brand": brand,
            "cat_id": category_id,
            "aliases": json.dumps([keyword]),
        })


@contextmanager
def get_db():
    """Yield a database connection as a context manager."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn

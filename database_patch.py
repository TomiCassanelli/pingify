import database

def patch_db():
    conn = database.get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artist_cache (
            artist_name TEXT PRIMARY KEY,
            artist_id TEXT,
            genres TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("DB patched.")

patch_db()

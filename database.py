import sqlite3

DB_NAME = "pingify.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notified_tracks (
            track_id TEXT PRIMARY KEY,
            track_name TEXT,
            artist_name TEXT,
            similarity_score REAL,
            notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ Base de datos inicializada")
    return conn


def track_exists(track_id, conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    cursor = conn.execute(
        "SELECT 1 FROM notified_tracks WHERE track_id = ?",
        (track_id,)
    )
    exists = cursor.fetchone() is not None
    
    if should_close:
        conn.close()
    
    return exists


def save_track(track_id, track_name, artist_name, similarity_score, conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    conn.execute(
        "INSERT OR IGNORE INTO notified_tracks (track_id, track_name, artist_name, similarity_score) VALUES (?, ?, ?, ?)",
        (track_id, track_name, artist_name, similarity_score)
    )
    conn.commit()
    
    if should_close:
        conn.close()


def get_recent_tracks(days=7, limit=50, conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    cursor = conn.execute("""
        SELECT track_id, track_name, artist_name, similarity_score, notified_at 
        FROM notified_tracks 
        ORDER BY notified_at DESC 
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    
    if should_close:
        conn.close()
    
    return results


def clear_all_tracks(conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    conn.execute("DELETE FROM notified_tracks")
    conn.commit()
    
    if should_close:
        conn.close()


if __name__ == "__main__":
    conn = init_db()
    print("📊 Estado de la base de datos:")
    
    cursor = conn.execute("SELECT COUNT(*) FROM notified_tracks")
    count = cursor.fetchone()[0]
    print(f"   Total de tracks notificados: {count}")
    
    conn.close()

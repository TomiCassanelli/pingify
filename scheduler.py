"""
Pingify Scheduler - Busca nuevos lanzamientos automáticamente.
Se ejecuta con cron: 0 22 * * * python scheduler.py
"""

import playlist_loader
import style_inference
import new_releases
import database
from app_config import Config
from datetime import datetime


def load_playlist_and_style():
    """Carga playlist y obtener estilo."""
    df = playlist_loader.load_playlist_tracks()
    if df.empty:
        return None, []
    
    tracks_text = playlist_loader.get_tracks_for_inference(df)
    seed_artists = playlist_loader.get_top_artist_names(df, limit=10)
    inference = style_inference.StyleInference()
    style = inference.infer(tracks_text)
    
    return style, seed_artists


def find_new_releases(style: dict, seed_artists: list[str], limit: int = 10) -> list:
    """Busca nuevos lanzamientos."""
    tracks = new_releases.discover_new_releases(
        style,
        seed_artists=seed_artists,
        limit=limit,
    )
    
    conn = database.init_db()
    new_only = [t for t in tracks if not database.track_exists(t["track_id"], conn)]
    conn.close()
    
    return new_only


def notify(text: str):
    """Notificación por CLI/console."""
    print(text)


def run():
    """Ejecución principal."""
    print(f"\n{'='*50}")
    print(f"🎵 PINGIFY - Auto Discovery")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    try:
        Config.validate()
    except ValueError as e:
        notify(f"❌ Config error: {e}")
        return
    
    style, seed_artists = load_playlist_and_style()
    if not style:
        notify("❌ No hay playlist")
        return
    
    print(f"\n📊 Estilo: {style.get('primary_genre')} / {style.get('mood')}")
    
    new_tracks = find_new_releases(style, seed_artists=seed_artists, limit=10)
    
    if not new_tracks:
        print("😴 No hay nuevos lanzamientos hoy")
        return
    
    print(f"\n🆕 {len(new_tracks)} NUEVOS LANZAMIENTOS:")
    print("=" * 50)
    
    for i, track in enumerate(new_tracks, 1):
        date = track.get("release_date", "?")[:4]
        print(f"{i}. {track['track_name']}")
        print(f"   {track['artist_name']} ({date})")
        
        database.save_track(
            track["track_id"],
            track["track_name"],
            track["artist_name"],
            1.0,
            None
        )
    
    print(f"\n✅ {len(new_tracks)} guardados en historial")
    print("=" * 50)


if __name__ == "__main__":
    run()

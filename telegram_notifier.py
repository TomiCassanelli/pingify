"""
Telegram Notifier - Envía recomendaciones automáticamente a las 10pm.
Se ejecuta con cron: 0 22 * * * python telegram_notifier.py
"""

import asyncio
from telegram import Bot
import playlist_loader
import style_inference
import new_releases
import database
from app_config import Config
from datetime import datetime


def load_style():
    """Carga estilo de la playlist."""
    df = playlist_loader.load_playlist_tracks()
    if df.empty:
        return None, []
    
    tracks_text = playlist_loader.get_tracks_for_inference(df)
    inference = style_inference.StyleInference()
    style = inference.infer(tracks_text)
    seed_artists = playlist_loader.get_top_artist_names(df, limit=10)
    return style, seed_artists


def find_new_tracks(style: dict, seed_artists: list[str], limit: int = 8) -> list:
    """Busca nuevos lanzamientos."""
    tracks = new_releases.discover_new_releases(
        style,
        seed_artists=seed_artists,
        limit=limit,
    )
    
    conn = database.init_db()
    new_only = [t for t in tracks if not database.track_exists(t["track_id"], conn)]
    conn.close()
    
    for track in new_only:
        database.save_track(
            track["track_id"],
            track["track_name"],
            track["artist_name"],
            1.0,
            None
        )
    
    return new_only


async def send_message(text: str):
    """Envía mensaje async."""
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=Config.TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
    print("✅ Enviado")


def notify():
    """Notificación principal."""
    print(f"\n{'='*50}")
    print(f"🔔 PINGIFY NOTIFIER - {datetime.now()}")
    print("=" * 50)
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Config: {e}")
        return
    
    style, seed_artists = load_style()
    if not style:
        print("❌ No hay estilo")
        return
    
    print(f"📊 Estilo: {style.get('primary_genre')} / {style.get('mood')}")
    
    new_tracks = find_new_tracks(style, seed_artists=seed_artists, limit=8)
    
    if not new_tracks:
        print("😴 No hay nuevos")
        return
    
    message = "🎵 *Nuevos Lanzamientos*\n\n"
    message += f"Basado en: *{style.get('primary_genre')}* / {style.get('mood')}\n\n"
    
    for i, track in enumerate(new_tracks, 1):
        date = track.get("release_date", "?")[:10]
        match_pct = track.get('match_pct', 70)
        message += f"{i}. *{track['track_name']}*\n   {track['artist_name']} ({date}) [{match_pct}% match]\n\n"
    
    message += f"\n🆕 {len(new_tracks)} nuevas"
    
    print(message)
    
    asyncio.run(send_message(message))


if __name__ == "__main__":
    notify()

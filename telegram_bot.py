"""
Telegram Bot para Pingify.
Acepta links de playlist de Spotify.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import re
import playlist_loader
import style_inference
import discovery_engine
import new_releases
import database
from app_config import Config


PLAYLIST_LINK_REGEX = r"(?:spotify\.com/playlist/|playlist/)([a-zA-Z0-9]+)"


from typing import Optional

def extract_playlist_id(text: str) -> Optional[str]:
    """Extrae ID de playlist de un link o texto."""
    match = re.search(PLAYLIST_LINK_REGEX, text)
    if match:
        return match.group(1)
    text = text.strip()
    if len(text) >= 22 and len(text) <= 40 and text.replace(" ", "").isalnum():
        return text
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Pingify - Descubridor Musical*\n\n"
        "Envía un link de playlist de Spotify o usa /profile\n\n"
        "Comandos:\n"
        "/start - Este mensaje\n"
        "/profile - Tu perfil (playlist del env)\n"
        "/discover - Recomendaciones (playlist del env)\n"
        "/new - Nuevos (playlist del env)",
        parse_mode="Markdown"
    )


async def handle_playlist_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa links de playlist."""
    text = update.message.text.strip()
    playlist_id = extract_playlist_id(text)
    
    if not playlist_id:
        await update.message.reply_text(
            "❌ No entendí. Envía un link de playlist de Spotify.\n"
            "Ej: https://open.spotify.com/playlist/5HU35Iu5jnuxRHvSViwJYA"
        )
        return
    
    await update.message.reply_text(f"🔍 Analizando playlist...")
    
    try:
        df = playlist_loader.load_playlist_tracks(playlist_id)
        
        if df.empty:
            await update.message.reply_text("❌ No encontré tracks")
            return
        
        tracks_text = playlist_loader.get_tracks_for_inference(df)
        inference = style_inference.StyleInference()
        style = inference.infer(tracks_text)
        
        msg = f"📊 *Perfil Musical*\n\n{inference.format_summary(style)}"
        await update.message.reply_text(msg, parse_mode="Markdown")
        
        await update.message.reply_text("🔍 Buscando recomendaciones...")
        
        recs = discovery_engine.discover(style, limit=5)
        
        if recs:
            msg = "🎵 *Recomendaciones*\n\n"
            for i, t in enumerate(recs, 1):
                match_pct = t.get('match_pct', 70)
                msg += f"{i}. {t['track_name']} - {t['artist_name']} [{match_pct}% match]\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
            
            for t in recs:
                database.save_track(t["track_id"], t["track_name"], t["artist_name"], 1.0, None)
        
        seed_artists = playlist_loader.get_top_artist_names(df, limit=10)
        new_tracks = new_releases.discover_new_releases(style, seed_artists=seed_artists, limit=3)
        
        if new_tracks:
            msg = "🆕 *Nuevos*\n\n"
            for i, t in enumerate(new_tracks, 1):
                date = t.get("release_date", "?")[:10]
                match_pct = t.get('match_pct', 70)
                msg += f"{i}. {t['track_name']} - {t['artist_name']} ({date}) [{match_pct}% match]\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
            
            for t in new_tracks:
                database.save_track(t["track_id"], t["track_name"], t["artist_name"], 1.0, None)
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 Analizando...")
    
    try:
        df = playlist_loader.load_playlist_tracks()
        tracks_text = playlist_loader.get_tracks_for_inference(df)
        inference = style_inference.StyleInference()
        style = inference.infer(tracks_text)
        
        await update.message.reply_text(
            f"📊 *Tu Perfil Musical*\n\n{inference.format_summary(style)}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando...")
    
    try:
        df = playlist_loader.load_playlist_tracks()
        tracks_text = playlist_loader.get_tracks_for_inference(df)
        inference = style_inference.StyleInference()
        style = inference.infer(tracks_text)
        
        recs = discovery_engine.discover(style, limit=8)
        
        if not recs:
            await update.message.reply_text("😴 No hay recomendaciones")
            return
        
        msg = "🎵 *Recomendaciones*\n\n"
        for i, t in enumerate(recs, 1):
            match_pct = t.get('match_pct', 70)
            msg += f"{i}. {t['track_name']} - {t['artist_name']} [{match_pct}% match]\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        
        for t in recs:
            database.save_track(t["track_id"], t["track_name"], t["artist_name"], 1.0, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆕 Buscando...")
    
    try:
        df = playlist_loader.load_playlist_tracks()
        tracks_text = playlist_loader.get_tracks_for_inference(df)
        inference = style_inference.StyleInference()
        style = inference.infer(tracks_text)
        
        seed_artists = playlist_loader.get_top_artist_names(df, limit=10)
        new_tracks = new_releases.discover_new_releases(style, seed_artists=seed_artists, limit=8)
        
        if not new_tracks:
            await update.message.reply_text("😴 No hay nuevos")
            return
        
        msg = "🆕 *Nuevos Lanzamientos*\n\n"
        for i, t in enumerate(new_tracks, 1):
            date = t.get("release_date", "?")[:10]
            match_pct = t.get('match_pct', 70)
            msg += f"{i}. {t['track_name']} - {t['artist_name']} ({date}) [{match_pct}% match]\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        
        for t in new_tracks:
            database.save_track(t["track_id"], t["track_name"], t["artist_name"], 1.0, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def main():
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("discover", discover))
    app.add_handler(CommandHandler("new", new_cmd))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_playlist_link))
    
    print("🤖 Bot iniciado")
    print("Envía link de playlist para analizar")
    print("/profile - Usar playlist del env")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

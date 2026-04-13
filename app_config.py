"""
Configuración centralizada para Pingify.
Carga variables de entorno y provee accessores seguros.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")
    SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    SPOTIFY_SCOPE = [
        "user-library-read",
        "user-follow-read",
        "playlist-read-private",
        "playlist-modify-public",
        "playlist-modify-private",
    ]
    
    SEARCH_LIMIT = 10
    
    @classmethod
    def validate(cls, require_telegram: bool = False, require_playlist: bool = False):
        missing = []
        required = [
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET", 
            "GROQ_API_KEY",
        ]

        if require_telegram:
            required.append("TELEGRAM_BOT_TOKEN")

        if require_playlist:
            required.append("SPOTIFY_PLAYLIST_ID")

        for attr in required:
            if not getattr(cls, attr):
                missing.append(attr)
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        
        return True


def get_config():
    return Config


if __name__ == "__main__":
    try:
        Config.validate()
        print("✅ Config validada correctamente")
    except ValueError as e:
        print(f"❌ {e}")
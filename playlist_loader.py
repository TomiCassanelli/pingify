"""
Playlist Loader - Extrae tracks de una playlist de Spotify.
Usa GET /playlists/{id}/items (nuevo endpoint).
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
import pandas as pd
from typing import Optional
from collections import Counter
from urllib.parse import urlparse
from app_config import Config

def get_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=Config.SPOTIFY_CLIENT_ID,
        client_secret=Config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=Config.SPOTIFY_REDIRECT_URI,
        scope=" ".join(Config.SPOTIFY_SCOPE),
        cache_handler=spotipy.CacheFileHandler(cache_path=".spotify_cache")
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def extract_playlist_id(playlist_input: Optional[str] = None) -> str:
    """
    Extrae un playlist_id desde:
    - URL web de Spotify
    - URI spotify:playlist:...
    - ID plano
    - fallback a Config.SPOTIFY_PLAYLIST_ID
    """
    raw = (playlist_input or Config.SPOTIFY_PLAYLIST_ID or "").strip()
    if not raw:
        raise ValueError("No se recibió playlist_id ni link de playlist")

    if raw.startswith("spotify:playlist:"):
        return raw.split(":")[-1].split("?")[0]

    if "open.spotify.com" in raw and "/playlist/" in raw:
        parsed = urlparse(raw)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "playlist":
            return parts[1]

    return raw.split("?")[0]


def load_playlist_tracks(playlist_id: Optional[str] = None) -> pd.DataFrame:
    """
    Carga todos los tracks de una playlist.
    
    Returns:
        DataFrame con columns: track_id, track_name, artist_name, artist_id, albums
    """
    playlist_id = extract_playlist_id(playlist_id)
    
    sp = get_spotify_client()
    
    tracks = []
    offset = 0
    limit = 100
    
    print(f"📀 Cargando playlist: {playlist_id}")
    
    while True:
        try:
            response = sp.playlist_items(playlist_id, offset=offset, limit=limit)
        except SpotifyException as error:
            if error.http_status == 403:
                raise PermissionError(
                    "Spotify devolvió 403. Esa playlist es privada o tu app/cuenta no tiene permisos para leerla. "
                    "Probá con una playlist pública o con una playlist propia compartida para ese usuario."
                ) from error
            if error.http_status == 404:
                raise ValueError(
                    "No se encontró la playlist. Verificá que el link/ID sea correcto."
                ) from error
            raise
        items = response.get("items", [])
        
        if not items:
            break
            
        for item in items:
            track = item.get("track") or item.get("item")
            
            if not track or not track.get("id"):
                continue
            
            if track.get("type") != "track":
                continue
            
            artists = track.get("artists") or []
            
            tracks.append({
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "artist_name": ", ".join(a.get("name", "") for a in artists),
                "artist_id": ", ".join(a.get("id", "") for a in artists if a.get("id")),
                "album_name": (track.get("album") or {}).get("name", ""),
                "album_id": (track.get("album") or {}).get("id", ""),
                "duration_ms": track.get("duration_ms"),
                "popularity": track.get("popularity"),
            })
        
        if offset + limit >= response.get("total", 0):
            break
        offset += limit
    
    df = pd.DataFrame(tracks)
    print(f"✅ {len(df)} tracks cargados")
    
    return df


def get_playlist_artists(df: pd.DataFrame) -> list[dict]:
    """
    Extrae artistas únicos de la playlist con su información.
    """
    if df.empty:
        return []
    
    artists_dict = {}
    
    for _, row in df.iterrows():
        artist_ids = row.get("artist_id", "").split(", ")
        artist_names = row.get("artist_name", "").split(", ")
        
        for aid, aname in zip(artist_ids, artist_names):
            if aid and aname:
                artists_dict[aid] = {
                    "artist_id": aid,
                    "artist_name": aname,
                }
    
    return list(artists_dict.values())


def get_playlist_summary(df: pd.DataFrame) -> dict:
    """
    Resumen básico de la playlist.
    """
    if df.empty:
        return {"total_tracks": 0, "unique_artists": 0}
    
    unique_artists = set()
    for artist_ids in df["artist_id"]:
        unique_artists.update(artist_ids.split(", "))
    
    return {
        "total_tracks": len(df),
        "unique_artists": len(unique_artists),
        "track_names": df["track_name"].tolist()[:15],
    }


def get_tracks_for_inference(df: pd.DataFrame, top_n: int = 20) -> str:
    """
   Genera string formateado para usar en el prompt de inference.
   Si la playlist es grande, muestrea de forma uniforme para evitar sesgo por orden.
    """
    if df.empty:
        return ""

    tracks = []

    if len(df) <= top_n:
        sample_df = df
    else:
        step = max(1, len(df) // top_n)
        sample_df = df.iloc[::step].head(top_n)

    for _, row in sample_df.iterrows():
        tracks.append(f"{row['track_name']} - {row['artist_name']}")
    
    return "\n".join(tracks)


def get_top_artist_names(df: pd.DataFrame, limit: int = 20) -> list[str]:
    """
    Retorna artistas más frecuentes de la playlist para usarlos como semillas.
    """
    if df.empty or "artist_name" not in df.columns:
        return []

    counts = Counter()
    for raw in df["artist_name"].dropna().tolist():
        names = [n.strip() for n in str(raw).split(",") if n.strip()]
        for name in names:
            counts[name] += 1

    return [name for name, _ in counts.most_common(limit)]


if __name__ == "__main__":
    df = load_playlist_tracks()
    print(f"\n📋 Resumen: {df.shape[0]} tracks")
    print(df.head())

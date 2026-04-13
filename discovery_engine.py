"""
Discovery Engine - Busca recomendaciones en Spotify basándose en el estilo inferido.
Usa el endpoint /search (límite 10 por request).
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from app_config import Config
import database


def get_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=Config.SPOTIFY_CLIENT_ID,
        client_secret=Config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=Config.SPOTIFY_REDIRECT_URI,
        scope=" ".join(Config.SPOTIFY_SCOPE),
        cache_handler=spotipy.CacheFileHandler(cache_path=".spotify_cache")
    )
    return spotipy.Spotify(auth_manager=auth_manager)


from datetime import datetime

def days_ago(date_str):
    if not date_str:
        return 999
    try:
        if len(date_str) == 4:
            return 999
        if len(date_str) == 7:
            release_dt = datetime.strptime(f"{date_str}-01", "%Y-%m-%d")
        else:
            release_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.now() - release_dt).days
    except:
        return 999

class DiscoveryEngine:
    def __init__(self):
        self.sp = get_spotify_client()
        self.limit = Config.SEARCH_LIMIT
    
    def search_by_genre(self, genre: str, limit: int = None) -> list[dict]:
        """
        Busca tracks por género.
        """
        limit = limit or self.limit
        
        try:
            results = self.sp.search(q=genre, type="track", limit=limit)
            tracks = results.get("tracks", {}).get("items", [])
            
            return self._parse_tracks(tracks)
        except Exception as e:
            print(f"⚠️ Error buscando por género: {e}")
            return []
    
    def search_by_artist(self, artist_name: str, limit: int = None) -> list[dict]:
        """
        Busca tracks de un artista específico.
        """
        limit = limit or self.limit
        
        try:
            query = f"artist:{artist_name}"
            results = self.sp.search(q=query, type="track", limit=limit)
            tracks = results.get("tracks", {}).get("items", [])
            
            return self._parse_tracks(tracks)
        except Exception as e:
            print(f"⚠️ Error buscando por artista: {e}")
            return []
    
    def search_by_genre_and_artist(self, genre: str, artist: str, limit: int = None) -> list[dict]:
        """
        Busca tracks que coincidan con género Y artista.
        """
        limit = limit or self.limit
        
        try:
            query = f"genre:{genre} artist:{artist}"
            results = self.sp.search(q=query, type="track", limit=limit)
            tracks = results.get("tracks", {}).get("items", [])
            
            return self._parse_tracks(tracks)
        except Exception as e:
            print(f"⚠️ Error en búsqueda combinada: {e}")
            return []
    
    def search_combined(self, style: dict, limit: int = None, days_back: int = None) -> list[dict]:
        """
        Busca usando search_queries de la IA + artistas similares.
        """
        limit = limit or self.limit
        results = []
        seen_ids = set()
        current_year = datetime.now().year
        
        queries = style.get("search_queries", [])
        if not queries:
            queries = style.get("similar_artists", [])[:5]
            
        fetch_limit = 10 if days_back else 3
        
        for query in queries[:5]:
            try:
                search_q = f"{query} year:{current_year}" if days_back else query
                res = self.sp.search(q=search_q, limit=fetch_limit, type="track")
                items = res.get("tracks", {}).get("items", [])
                
                for track in items:
                    if track.get("id") in seen_ids:
                        continue
                    
                    if days_back:
                        album = track.get("album") or {}
                        if album.get("album_type") == "compilation":
                            continue
                            
                        rel_date = album.get("release_date", "")
                        if days_ago(rel_date) > days_back:
                            continue
                            
                        # Evitar falsos nuevos lanzamientos (karaoke, en vivo, remasters)
                        t_name = track.get("name", "").lower()
                        a_name = album.get("name", "").lower()
                        fake_kws = ["remaster", "live", "karaoke", "cover", "tribute", "version", "versión", "en vivo"]
                        if any(k in t_name for k in fake_kws) or any(k in a_name for k in fake_kws):
                            continue
                            
                    seen_ids.add(track.get("id"))
                    
                    parsed = self._parse_tracks([track])
                    if parsed:
                        t = parsed[0]
                        t["search_source"] = f"query:{query}"
                        results.append(t)
            except Exception as e:
                pass
        
        similar = style.get("similar_artists", [])
        for artist in similar[:3]:
            if len(results) >= limit and not days_back:
                break
            try:
                search_q = f"artist:{artist} year:{current_year}" if days_back else f"artist:{artist}"
                res = self.sp.search(q=search_q, limit=fetch_limit, type="track")
                items = res.get("tracks", {}).get("items", [])
                
                for track in items:
                    if track.get("id") in seen_ids:
                        continue
                    
                    if days_back:
                        album = track.get("album") or {}
                        if album.get("album_type") == "compilation":
                            continue
                            
                        rel_date = album.get("release_date", "")
                        if days_ago(rel_date) > days_back:
                            continue
                            
                        # Evitar falsos nuevos lanzamientos (karaoke, en vivo, remasters)
                        t_name = track.get("name", "").lower()
                        a_name = album.get("name", "").lower()
                        fake_kws = ["remaster", "live", "karaoke", "cover", "tribute", "version", "versión", "en vivo"]
                        if any(k in t_name for k in fake_kws) or any(k in a_name for k in fake_kws):
                            continue
                            
                    seen_ids.add(track.get("id"))
                    
                    parsed = self._parse_tracks([track])
                    if parsed:
                        t = parsed[0]
                        t["search_source"] = f"artist:{artist}"
                        results.append(t)
            except Exception as e:
                pass
        
        # Sort if we are grabbing recent ones to prioritize best style matches
        # or we just return up to limit
        return results[:limit]
    
    def _parse_tracks(self, tracks: list) -> list[dict]:
        """Parsea tracks de la respuesta de Spotify."""
        result = []
        
        for track in tracks:
            if not track:
                continue
            
            artists = track.get("artists") or []
            
            result.append({
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "artist_name": ", ".join(a.get("name", "") for a in artists),
                "artist_id": ", ".join(a.get("id", "") for a in artists if a.get("id")),
                "album_name": (track.get("album") or {}).get("name", ""),
                "album_id": (track.get("album") or {}).get("id", ""),
                "release_date": (track.get("album") or {}).get("release_date", ""),
                "duration_ms": track.get("duration_ms"),
                "preview_url": track.get("preview_url"),
                "uri": track.get("uri"),
            })
        
        return result
    
    def filter_not_notified(self, tracks: list[dict], conn=None) -> list[dict]:
        """
        Filtra tracks que ya han sido notificados.
        """
        import sqlite3
        
        should_close = False
        if conn is None:
            conn = database.init_db()
            should_close = True
        
        filtered = []
        
        for track in tracks:
            track_id = track.get("track_id")
            if track_id and not database.track_exists(track_id, conn):
                filtered.append(track)
        
        if should_close:
            conn.close()
        
        return filtered
    
    def rank_by_style_match(self, tracks: list[dict], style: dict) -> list[dict]:
        """
        Rankea tracks según cuánto coinciden con el estilo.
        Prioriza tracks de artistas similares.
        """
        similar_artists = [a.lower() for a in style.get("similar_artists", [])]
        
        scored = []
        
        for track in tracks:
            score = 0
            artist_name = track.get("artist_name", "").lower()
            
            if any(sa in artist_name for sa in similar_artists):
                score += 10
            
            source = track.get("search_source", "")
            if source.startswith("artist:"):
                score += 5
            
            text = f"{track.get('track_name', '')}".lower()
            for vibe in style.get("vibes", []):
                if vibe.lower() in text:
                    score += 2
            
            # Base 70% por pasar los filtros iniciales. Max 100%
            match_pct = min(100, 70 + (score * 3))
            
            track["style_score"] = score
            track["match_pct"] = match_pct
            scored.append(track)
        
        # Filtramos dejando solo >= 85% de coincidencia
        filtered_scored = [t for t in scored if t.get("match_pct", 0) >= 85]
        filtered_scored.sort(key=lambda t: t.get("match_pct", 0), reverse=True)
        
        return filtered_scored


def discover(style: dict, limit: int = 10, days_back: int = None) -> list[dict]:
    """
    Función helper para descubrir tracks.
    Si days_back está presente, filtra los resultados a los últimos días.
    """
    engine = DiscoveryEngine()
    
    tracks = engine.search_combined(style, limit=limit, days_back=days_back)
    
    conn = database.init_db()
    tracks = engine.filter_not_notified(tracks, conn)
    conn.close()
    
    tracks = engine.rank_by_style_match(tracks, style)
    
    return tracks


if __name__ == "__main__":
    test_style = {
        "primary_genre": "latin pop",
        "sub_genre": "romantic latin pop",
        "mood": "romantic",
        "vibes": ["love", "heartbreak"],
        "similar_artists": ["Morat", "Sebastian Yatra"]
    }
    
    tracks = discover(test_style, limit=5)
    
    print("🎵 Recomendaciones:")
    for t in tracks:
        print(f"  • {t['track_name']} - {t['artist_name']}")
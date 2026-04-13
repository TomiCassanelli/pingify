"""
New Releases - Descubre lanzamientos recientes.
IMPLEMENTACIÓN ROBUSTA CURADA Y OPTIMIZADA.
Con caché de artistas y scoring avanzado anti-basura.
"""

from discovery_engine import get_spotify_client, days_ago
import database
import json
import unicodedata
import datetime

def remove_accents(input_str):
    if not input_str: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', input_str) if unicodedata.category(c) != 'Mn')

def _normalize_list(items):
    if not items:
        return []
    if isinstance(items, str):
        return [i.strip() for i in items.split(",") if i.strip()]
    return [i for i in items if i]

def _is_valid_new_release(album_data: dict, track_name: str, days_back: int) -> bool:
    if not album_data:
        return False
        
    if album_data.get("album_type") == "compilation":
        return False
        
    rel_date = album_data.get("release_date", "")
    if days_ago(rel_date) > days_back:
        return False
        
    t_name = track_name.lower()
    a_name = album_data.get("name", "").lower()
    
    # Basura/Reediciones/Skits
    fake_kws = [
        "remaster", "live", "karaoke", "cover", "tribute", "version", "versión", 
        "en vivo", "acoustic version", "acústico", "intro", "outro", "interlude", "skit"
    ]
    
    if any(k in t_name for k in fake_kws) or any(k in a_name for k in fake_kws):
        return False
        
    return True

def _parse_track(t: dict, album_data: dict, artist_genres: list) -> dict:
    artists = t.get("artists") or []
    return {
        "track_id": t.get("id"),
        "track_name": t.get("name"),
        "artist_name": ", ".join(a.get("name", "") for a in artists),
        "artist_id": ", ".join(a.get("id", "") for a in artists if a.get("id")),
        "album_name": album_data.get("name", ""),
        "album_id": album_data.get("id", ""),
        "release_date": album_data.get("release_date", ""),
        "duration_ms": t.get("duration_ms"),
        "preview_url": t.get("preview_url"),
        "uri": t.get("uri"),
        "artist_genres": artist_genres, # Agregamos géneros para el scoring avanzado
    }

def _get_cached_artist(artist_name: str, conn):
    cursor = conn.execute("SELECT artist_id, genres FROM artist_cache WHERE artist_name = ?", (artist_name.lower(),))
    row = cursor.fetchone()
    if row:
        return row[0], json.loads(row[1])
    return None, None

def _save_cached_artist(artist_name: str, artist_id: str, genres: list, conn):
    conn.execute(
        "INSERT OR REPLACE INTO artist_cache (artist_name, artist_id, genres) VALUES (?, ?, ?)",
        (artist_name.lower(), artist_id, json.dumps(genres))
    )
    conn.commit()

def _get_artists_recent_releases(sp, artist_names: list, days_back: int, conn) -> list:
    tracks = []
    seen_ids = set()
    
    for artist_name in artist_names:
        if not artist_name: continue
        
        try:
            artist_id, genres = _get_cached_artist(artist_name, conn)
            
            if not artist_id:
                # 1 request solo si no está en caché (Ahorramos 15 requests!)
                res = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
                items = res.get("artists", {}).get("items")
                if not items: continue
                
                artist_id = items[0]["id"]
                genres = items[0].get("genres", [])
                _save_cached_artist(artist_name, artist_id, genres, conn)
            
            albums_res = sp.artist_albums(artist_id, album_type="album,single", limit=5)
            for album in albums_res.get("items", []):
                
                if not _is_valid_new_release(album, "", days_back):
                    continue
                    
                t_res = sp.album_tracks(album["id"], limit=10)
                for t in t_res.get("items", []):
                    tid = t.get("id")
                    if not tid or tid in seen_ids:
                        continue
                        
                    if not _is_valid_new_release(album, t.get("name", ""), days_back):
                        continue
                        
                    seen_ids.add(tid)
                    tracks.append(_parse_track(t, album, genres))
        except Exception as e:
            pass
            
    return tracks

def _get_global_discovery_releases(sp, style: dict, days_back: int, conn) -> list:
    """Busca nuevos artistas globales fuera de la burbuja usando el año y género."""
    tracks = []
    seen_ids = set()
    current_year = datetime.datetime.now().year
    
    queries = []
    sub_genre = style.get("sub_genre", "").strip()
    primary = style.get("primary_genre", "").strip()
    
    if sub_genre: queries.append(f"{sub_genre} year:{current_year}")
    if primary: queries.append(f"{primary} year:{current_year}")
    if not queries: queries.append(f"latin pop year:{current_year}")
        
    for q in queries[:2]: # Max 2 queries para no quemar requests
        for offset in [0, 10, 20]: # 3 páginas = 30 resultados por query
            try:
                res = sp.search(q=q, type="track", limit=10, offset=offset)
                items = res.get("tracks", {}).get("items", [])
                if not items: break
                
                for t in items:
                    tid = t.get("id")
                    if not tid or tid in seen_ids:
                        continue
                    
                    album = t.get("album") or {}
                    if not _is_valid_new_release(album, t.get("name", ""), days_back):
                        continue
                        
                    # Intentar sacar géneros de caché
                    artist_id = t["artists"][0]["id"] if t.get("artists") else None
                    genres = []
                    if artist_id:
                        artist_name = t["artists"][0]["name"]
                        c_id, c_genres = _get_cached_artist(artist_name, conn)
                        if c_genres:
                            genres = c_genres
                            
                    seen_ids.add(tid)
                    tracks.append(_parse_track(t, album, genres))
            except Exception as e:
                break
                
    return tracks

def _score_and_filter_tracks(tracks: list, style: dict, seed_artists: list) -> list:
    scored = []
    
    mood = remove_accents(style.get("mood") or "").strip().lower()
    primary_genre = remove_accents(style.get("primary_genre") or "").strip().lower()
    sub_genre = remove_accents(style.get("sub_genre") or "").strip().lower()
    
    vibes = [remove_accents(v).lower() for v in _normalize_list(style.get("vibes", []))]
    similar_artists = [remove_accents(a).lower() for a in _normalize_list(style.get("similar_artists", []))]
    seed_artists = [remove_accents(a).lower() for a in (seed_artists or []) if a]
    
    # Análisis de perfil
    is_party = any(w in mood for w in ["party", "fiesta", "perreo", "club", "dance", "bailar", "energetic"])
    is_chill = any(w in mood for w in ["chill", "relax", "suave", "acoustic", "lofi", "introspectivo", "emotivo", "sad"])
    is_romantic = any(w in mood for w in ["romantic", "amor", "balada", "romance"])
    
    for t in tracks:
        score = 0
        t_name = remove_accents(t.get("track_name", "")).lower()
        a_name = remove_accents(t.get("artist_name", "")).lower()
        a_genres = [remove_accents(g).lower() for g in t.get("artist_genres", [])]
        
        # 1. Boosts directos
        if any(sa in a_name for sa in seed_artists): score += 5
        if any(sa in a_name for sa in similar_artists): score += 3
        
        # 2. Boost por vibes (letras)
        for vibe in vibes:
            if vibe.lower() in t_name:
                score += 3
                
        # 3. FILTROS AVANZADOS / PENALIZACIONES
        if is_party:
            if any(w in t_name for w in ["lullaby", "sleep", "relax", "acoustic", "piano"]): score -= 15
            if any("balada" in g for g in a_genres): score -= 5
            
        if is_chill or is_romantic:
            # Penaliza duramente reggaetoneros si buscas baladas introspectivas
            if any("reggaeton" in g or "trap" in g for g in a_genres): score -= 10
            # Penaliza nombres de track fiesteros
            if any(w in t_name for w in ["remix", "club", "mix", "dj", "perreo", "party"]): score -= 15
            
        # Refinar por el género requerido de la IA (e.g., si dice "balada" y el artista es de balada)
        if "balada" in sub_genre or "balada" in primary_genre:
            if any("balada" in g for g in a_genres): score += 5
            
        if "urbano" in sub_genre or "reggaeton" in primary_genre:
            if any("reggaeton" in g or "urbano" in g for g in a_genres): score += 5
            
        t["style_score"] = score
        
        # Match percentage calculation (0-100%)
        if score < 0:
            t["match_pct"] = 0
        else:
            # Base 70% for surviving strict filters, up to 100%
            match_pct = min(100, 70 + (score * 3))
            t["match_pct"] = match_pct
            
        scored.append(t)
        
    # Ordenar por score y quedarnos SOLO con los que superan el 85% de match
    scored.sort(key=lambda x: x.get("match_pct", 0), reverse=True)
    return [t for t in scored if t.get("match_pct", 0) >= 85]


def discover_new_releases(style: dict, seed_artists=None, limit: int = 10, days_back: int = 14) -> list[dict]:
    sp = get_spotify_client()
    conn = database.init_db()
    
    primary_genre = style.get("primary_genre") or "latin pop"
    mood = style.get("mood", "chill")
    
    print(f"🔍 Nuevos lanzamientos ({days_back} días) - mood: {mood} | genre: {primary_genre}")
    
    # 1. Usar ESTRICTAMENTE los artistas sugeridos por la IA,
    # porque la IA ya los filtró para que coincidan con el mood/género exacto (ej. puras baladas).
    # Ignoramos los seed_artists directos si la IA no los consideró "similares" al perfil.
    similar_artists_list = _normalize_list(style.get("similar_artists", []))
    target_artists = similar_artists_list[:10]
    
    # 1. Recolectar tracks de nuestra burbuja cerrada (Artistas similares)
    all_tracks = _get_artists_recent_releases(sp, target_artists, days_back, conn)
    
    # 2. Descubrimiento Global: Si nos quedamos cortos de temas nuevos, 
    # o simplemente para agregar variedad de artistas "fuera de la burbuja".
    global_tracks = _get_global_discovery_releases(sp, style, days_back, conn)
    all_tracks.extend(global_tracks)
    
    # 3. Filtrar repetidos absolutos
    unique_tracks = []
    seen = set()
    for t in all_tracks:
        if t["track_id"] not in seen:
            seen.add(t["track_id"])
            unique_tracks.append(t)
            
    # 3. Filtrar los ya notificados en DB
    not_notified = []
    for t in unique_tracks:
        if not database.track_exists(t["track_id"], conn):
            not_notified.append(t)
            
    conn.close()
    
    if not not_notified:
        return []
        
    # 4. Aplicar Scoring Estricto
    final_tracks = _score_and_filter_tracks(not_notified, style, seed_artists)
    
    return final_tracks[:limit]

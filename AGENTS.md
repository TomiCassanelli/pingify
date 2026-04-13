# AGENTS.md - Pingify Context

## Product Mission
Pingify analiza una playlist de Spotify elegida por el usuario (link/ID) y construye un perfil musical robusto (genre, sub_genre, mood, vibes, artistas afines). Con ese perfil, recomienda solo nuevos lanzamientos que coincidan con el mood y el estilo detectado.

## Primary User Flow
1. Usuario entrega playlist por link/ID desde CLI, Telegram o futura app web.
2. Se cargan tracks de la playlist (10, 100 o 1000).
3. Se infiere el perfil de estilo con LLM + metadatos musicales.
4. Se buscan candidatos de nuevos lanzamientos:
   - `tag:new` en Spotify.
   - Lanzamientos recientes de artistas semilla (similares + top de playlist).
5. Se scorean candidatos por afinidad de mood/genre/vibe.
6. Se filtran repetidos con base de datos local (`notified_tracks`).
7. Se muestran o notifican recomendaciones.

## Recommendation Rules
- Solo recomendar canciones nuevas (ventana configurable de dias recientes).
- Priorizar match de mood por encima de popularidad.
- Si un lanzamiento contradice el mood principal, descartarlo.
- Evitar repetir tracks ya notificados.

## Mood Taxonomy
Valores esperados de `mood`:
- `romantic`
- `heartbreak`
- `party`
- `chill`
- `energetic`
- `sad`
- `mixed`

## Current Channels
- CLI: `main.py`
- Telegram bot: `telegram_bot.py`
- Batch/cron: `scheduler.py`, `telegram_notifier.py`
- Web app: pendiente (usar mismos servicios de `playlist_loader.py`, `style_inference.py`, `new_releases.py`)

## Implementation Notes
- El input principal debe aceptar URL y URI de Spotify, no solo ID plano.
- Para playlists grandes, usar muestreo uniforme para inferencia y evitar sesgo por orden.
- `new_releases.py` debe combinar discovery por `tag:new` + releases de artistas semilla.
- Todas las rutas deben compartir la misma logica de scoring para consistencia.

## Prompting Guidance
- Pedir JSON estricto para inferencia de estilo.
- Evitar artistas inventados en `similar_artists`.
- Mantener consultas de Spotify accionables en `search_queries`.

## Definition of Done
- Playlist por link funciona en CLI y Telegram.
- Recomendaciones de nuevos lanzamientos respetan mood y estilo.
- Historial evita duplicados.
- El contexto del proyecto queda documentado en AGENTS.md y prompts/agentes de `.github`.

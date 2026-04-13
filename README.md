# Pingify

Pingify analiza una playlist de Spotify y recomienda **solo nuevos lanzamientos** que coincidan con el mood/estilo de esa playlist.

## Flujo

1. Usuario pasa playlist por URL/URI/ID (CLI o Telegram).
2. `playlist_loader.py` carga canciones y artistas.
3. `style_inference.py` genera perfil musical (genre, mood, vibes, artistas similares).
4. `new_releases.py` descubre candidatos recientes por:
	- `tag:new` de Spotify.
	- lanzamientos recientes de artistas semilla.
5. Se calcula score de afinidad (mood/genre/vibe + artistas) y se filtran duplicados con SQLite.

## Estructura

- `main.py`: CLI interactiva.
- `telegram_bot.py`: bot con comandos `/profile`, `/discover`, `/new`, `/history`.
- `scheduler.py`: job diario para descubrimiento.
- `telegram_notifier.py`: notifica lanzamientos por Telegram.
- `database.py`: historial de tracks notificados.

## Configuracion

Variables de entorno requeridas:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `GROQ_API_KEY`

Variables opcionales:

- `SPOTIFY_PLAYLIST_ID` (fallback si no se pasa link)
- `TELEGRAM_BOT_TOKEN` (necesaria para bot/notifier)
- `TELEGRAM_CHAT_ID` (necesaria para notifier)

## Uso rapido

### CLI

```bash
python main.py
```

El programa pide link/ID de playlist al iniciar.

### Telegram Bot

```bash
python telegram_bot.py
```

Comandos:

- `/profile [link]`
- `/discover [link]`
- `/new [link]`
- `/history`

Si no se pasa `[link]`, usa `SPOTIFY_PLAYLIST_ID`.

### Jobs diarios

```bash
python scheduler.py
python telegram_notifier.py
```

## Contexto para IA

- `AGENTS.md`: visión del problema y reglas del pipeline.
- `.github/prompts/`: prompts reutilizables para análisis y filtro.
- `.github/agents/`: agente especializado de Pingify.
- `.github/instructions/`: reglas permanentes de implementación.

## Roadmap corto

1. Exponer el pipeline como API (FastAPI) para una app web.
2. Permitir múltiples playlists por usuario con persistencia.
3. Añadir validación LLM opcional final para ranking top-N.
# pingify
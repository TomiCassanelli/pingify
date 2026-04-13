"""
CLI para Pingify - Descubridor Musical con IA.
"""

import playlist_loader
import style_inference
import discovery_engine
import new_releases
from app_config import Config


def main():
    print("🎵 Pingify - Descubridor Musical con IA")
    print("=" * 40)
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Config inválida: {e}")
        return

    playlist_input = input(
        "🔗 Pega el link/ID de playlist (Enter para usar SPOTIFY_PLAYLIST_ID): "
    ).strip()

    try:
        playlist_id = playlist_loader.extract_playlist_id(playlist_input or None)
    except ValueError as e:
        print(f"❌ {e}")
        return

    print(f"📀 Playlist: {playlist_id}")

    try:
        df = playlist_loader.load_playlist_tracks(playlist_id)
    except Exception as e:
        print(f"❌ Error cargando playlist: {e}")
        return
    
    if df.empty:
        print("❌ No hay tracks en la playlist")
        return
    
    print(f"   {len(df)} tracks cargados")
    seed_artists = playlist_loader.get_top_artist_names(df, limit=10)
    
    print("🎯 Analizando estilo musical...")
    tracks_text = playlist_loader.get_tracks_for_inference(df)
    
    inference = style_inference.StyleInference()
    style = inference.infer(tracks_text)
    
    print("✅ Listo\n")
    
    while True:
        print("=" * 40)
        print("🎵 PINGIFY - Menú")
        print("=" * 40)
        print("1. 🔍 Recomendaciones (similar artists)")
        print("2. 🆕 Nuevos lanzamientos (género/mood)")
        print("3. 📊 Ver perfil musical")
        print("4. 🚪 Salir")
        print()
        
        option = input("Elige: ").strip()
        
        if option == "1":
            print("\n🔍 Buscando...")
            recommendations = discovery_engine.discover(style, limit=8)
            
            if not recommendations:
                print("😴 No hay recomendaciones")
                continue
            
            print("\n" + "=" * 40)
            print(f"🎵 {len(recommendations)} RECOMENDACIONES")
            print("=" * 40)
            
            for i, track in enumerate(recommendations, 1):
                match_pct = track.get('match_pct', 70)
                print(f"\n{i}. {track['track_name']}")
                print(f"   {track['artist_name']} [Match: {match_pct}%]")
        
        elif option == "2":
            print("\n🆕 Buscando nuevos...")
            new_tracks = new_releases.discover_new_releases(
                style,
                seed_artists=seed_artists,
                limit=8,
            )
            
            if not new_tracks:
                print("😴 No hay nuevos")
                continue
            
            print("\n" + "=" * 40)
            print(f"🆕 {len(new_tracks)} LANZAMIENTOS")
            print("=" * 40)
            
            for i, track in enumerate(new_tracks, 1):
                date = track.get("release_date", "?")[:10]
                print(f"\n{i}. {track['track_name']}")
                
                match_pct = track.get('match_pct', 70)
                print(f"   {track['artist_name']} ({date}) [{match_pct}% Match]")
        
        elif option == "3":
            print("\n" + "=" * 40)
            print("📊 PERFIL MUSICAL")
            print("=" * 40)
            print(inference.format_summary(style))
        
        elif option == "4":
            print("👋")
            break


if __name__ == "__main__":
    main()

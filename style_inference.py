"""
Style Inference - Usa Groq API para inferir el estilo musical.
Simplificado - sin restricciones.
"""

from openai import OpenAI
import json
from app_config import Config


SYSTEM_PROMPT = """Eres un experto en música. Analiza las canciones y artistas, deduce el estilo real.

Responde SOLO JSON (sin texto extra):

{
  "primary_genre": "urban latin, reggaeton, trap, latin pop, rock, pop, etc",
  "sub_genre": "reggaeton, trap latino, dembow, latin trap, etc",  
  "mood": "upbeat, relajado, introspectivo, oscuro, bailable, emotivo, intenso",
  "decade": "2020s, 2010s",
  "language": "spanish, english, mixed",
  "vibes": "palabras que definan el estilo (5 palabras separadas por coma)",
  "similar_artists": "artistas reales del mismo estilo (5 separados por coma)"
}

No希 ограничения. No deduzcas solo por artistas."""


USER_PROMPT_TEMPLATE = """Analiza estas canciones:

{tracks}

Responde SOLO JSON."""


class StyleInference:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def infer(self, tracks_text: str) -> dict:
        user_prompt = USER_PROMPT_TEMPLATE.format(tracks=tracks_text)
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            return self._clean_result(result)
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return self._default()
    
    def _clean_result(self, result: dict) -> dict:
        defaults = {
            "primary_genre": "pop",
            "sub_genre": "general",
            "mood": "mixed",
            "decade": "2020s",
            "language": "mixed",
            "vibes": "variado",
            "similar_artists": ""
        }
        
        for k, v in defaults.items():
            if k not in result or not result.get(k):
                result[k] = v
        
        if isinstance(result.get("vibes"), list):
            result["vibes"] = ", ".join(result["vibes"])
        
        if isinstance(result.get("similar_artists"), list):
            result["similar_artists"] = ", ".join(result["similar_artists"])
        
        return result
    
    def _default(self):
        return {
            "primary_genre": "pop",
            "sub_genre": "general",
            "mood": "mixed",
            "decade": "2020s",
            "language": "mixed",
            "vibes": "variado",
            "similar_artists": ""
        }
    
    def format_summary(self, style: dict) -> str:
        lines = [
            f"🎵 Género: {style.get('primary_genre', '?')} / {style.get('sub_genre', '?')}",
            f"💭 Mood: {style.get('mood', '?')}",
            f"📅 Década: {style.get('decade', '?')}",
            f"🗣️ Idioma: {style.get('language', '?')}",
        ]
        
        vibes = style.get("vibes", "")
        if isinstance(vibes, str):
            vibes = [v.strip() for v in vibes.split(",")]
        if vibes:
            lines.append(f"✨ Vibe: {', '.join(vibes[:5])}")
        
        similar = style.get("similar_artists", "")
        if isinstance(similar, str):
            similar = [s.strip() for s in similar.split(",")]
        if similar:
            lines.append(f"🎤 Similares: {', '.join(similar[:5])}")
        
        return "\n".join(lines)


def infer_playlist_style(tracks_text: str) -> dict:
    inference = StyleInference()
    return inference.infer(tracks_text)


if __name__ == "__main__":
    test = """Bam Bam - Camila Cabello
Despacito - Luis Fonsi
Dakiti - J Balvin"""
    
    result = infer_playlist_style(test)
    print(json.dumps(result, indent=2))
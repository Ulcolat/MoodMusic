"""
Script para poblar el grafo RDF con canciones desde la API de Deezer.
Genera al menos 2000 canciones con metadatos de estado de ánimo y contexto.
Ejecutar una sola vez: python datos/populate_songs.py
"""

import urllib.request
import urllib.parse
import json
import time
import re

# Mapeo de géneros Deezer -> géneros MoodMusic
GENRE_MAP = {
    "Pop": "Pop",
    "Rap/Hip Hop": "HipHop",
    "Hip-Hop": "HipHop",
    "Rock": "Rock",
    "Electro": "Electronic",
    "Electronic": "Electronic",
    "Dance": "Electronic",
    "R&B": "RnB",
    "Soul & R&B": "RnB",
    "Jazz": "Jazz",
    "Classical": "Classical",
    "Latin": "Latin",
    "Reggaeton": "Reggaeton",
    "Urbano": "Urbano",
    "Alternative": "Rock",
    "Indie": "Indie",
    "Lo-Fi": "LoFi",
    "Salsa": "Salsa",
    "Metal": "Metal",
}

# Reglas de inferencia: género -> (ánimos, contextos)
GENRE_MOOD_CONTEXT = {
    "Pop":        (["Alegre", "Romantico", "Energico"], ["Fiesta", "Casa", "Trabajo"]),
    "HipHop":     (["Energico", "Estresado"], ["Ejercicio", "Trabajo", "Fiesta"]),
    "Rock":       (["Energico", "Triste", "Estresado"], ["Ejercicio", "Casa", "Trabajo"]),
    "Electronic": (["Energico", "Tranquilo"], ["Ejercicio", "Fiesta", "Trabajo"]),
    "RnB":        (["Romantico", "Tranquilo", "Alegre"], ["Casa", "Fiesta", "Descanso"]),
    "Jazz":       (["Tranquilo", "Romantico"], ["Casa", "Descanso", "Trabajo"]),
    "Classical":  (["Tranquilo", "Estresado", "Triste"], ["Estudio", "Descanso", "Casa"]),
    "Latin":      (["Alegre", "Romantico"], ["Fiesta", "Casa"]),
    "Reggaeton":  (["Alegre", "Energico"], ["Fiesta", "Ejercicio"]),
    "Urbano":     (["Tranquilo", "Romantico", "Alegre", "Triste"], ["Casa", "Fiesta", "Descanso"]),
    "Indie":      (["Tranquilo", "Triste"], ["Estudio", "Casa", "Descanso"]),
    "LoFi":       (["Tranquilo", "Estresado"], ["Estudio", "Trabajo", "Descanso"]),
    "Salsa":      (["Alegre", "Energico"], ["Fiesta", "Casa"]),
    "Metal":      (["Energico", "Estresado"], ["Ejercicio", "Trabajo"]),
}

# Búsquedas para obtener variedad de canciones
SEARCH_QUERIES = [
    # Urbano / Reggaeton colombiano
    "Feid", "J Balvin", "Maluma", "Karol G", "Bad Bunny", "Ozuna", "Anuel AA",
    "Rauw Alejandro", "Jhay Cortez", "Myke Towers", "Farruko", "Sech", "Dalex",
    "Nicky Jam", "Daddy Yankee", "Don Omar", "Wisin Yandel", "Arcangel",
    "Manuel Turizo", "Blessd", "Ryan Castro", "Mora", "Eladio Carrion",
    "Lunay", "Jhayco", "Dimelo Flow", "Kevvo", "Justin Quiles", "Rafa Pabön",
    "Lenny Tavarez", "Duki", "Trueno", "Bizarrap", "Nathy Peluso",
    "Paulo Londra", "Big One", "YSY A", "Ca7riel",
    # Pop internacional
    "The Weeknd", "Harry Styles", "Ed Sheeran", "Dua Lipa", "Olivia Rodrigo",
    "Billie Eilish", "Post Malone", "Justin Bieber", "Ariana Grande", "Taylor Swift",
    "Shawn Mendes", "Camila Cabello", "Sam Smith", "Lizzo", "Charlie Puth",
    "Bruno Mars", "Maroon 5", "One Direction", "5 Seconds of Summer",
    "Coldplay", "Imagine Dragons", "Twenty One Pilots", "Fall Out Boy",
    "Panic at the Disco", "Paramore", "Linkin Park",
    # Hip Hop
    "Drake", "Kendrick Lamar", "Travis Scott", "Cardi B", "Nicki Minaj",
    "Jay-Z", "Kanye West", "Eminem", "Lil Uzi Vert", "Future", "Young Thug",
    "Lil Baby", "Gunna", "21 Savage", "Offset", "Quavo", "Takeoff",
    "A$AP Rocky", "Tyler the Creator", "J. Cole", "Mac Miller", "Logic",
    "NF", "Juice WRLD", "Pop Smoke", "Rod Wave", "NBA YoungBoy",
    # R&B / Soul
    "Frank Ocean", "SZA", "H.E.R.", "Jhené Aiko", "Daniel Caesar",
    "Khalid", "Giveon", "Brent Faiyaz", "Lucky Daye", "PnB Rock",
    "Chris Brown", "Usher", "Ne-Yo", "John Legend", "Alicia Keys",
    # Electronic
    "Daft Punk", "Calvin Harris", "David Guetta", "Marshmello", "Kygo",
    "Martin Garrix", "Avicii", "Zedd", "Tiësto", "Diplo", "Skrillex",
    "Flume", "Odesza", "Petit Biscuit", "Madeon", "Porter Robinson",
    # Rock
    "Queen", "The Beatles", "Rolling Stones", "Metallica", "AC/DC",
    "Guns N Roses", "Nirvana", "Red Hot Chili Peppers", "Foo Fighters",
    "Arctic Monkeys", "The Killers", "Radiohead", "Muse", "Green Day",
    "Blink-182", "Sum 41", "Simple Plan", "My Chemical Romance",
    # Jazz / Classical
    "Miles Davis", "John Coltrane", "Bill Evans", "Chet Baker",
    "Norah Jones", "Diana Krall", "Amy Winehouse",
    "Ludovico Einaudi", "Yann Tiersen", "Max Richter", "Hans Zimmer",
    # Latin / Salsa
    "Marc Anthony", "Hector Lavoe", "Celia Cruz", "Willie Colon",
    "Carlos Vives", "Shakira", "Juanes", "Alejandro Sanz", "Enrique Iglesias",
    "Ricky Martin", "Marc Anthony", "Romeo Santos", "Prince Royce",
    # Indie
    "Tame Impala", "Rex Orange County", "Still Woozy", "Clairo", "Billie Marten",
    "Lord Huron", "Hozier", "The 1975", "Vampire Weekend", "Bon Iver",
    "Fleet Foxes", "Sufjan Stevens", "Iron Wine", "Jose Gonzalez",
    # LoFi / Chill
    "Lofi Girl", "ChilledCow", "Nujabes", "J Dilla", "Knxwledge",
]

def deezer_search(query, limit=50):
    """Busca canciones en Deezer."""
    q = urllib.parse.quote(query)
    url = f"https://api.deezer.com/search?q={q}&limit={limit}"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        return data.get("data", [])
    except Exception as e:
        print(f"  Error buscando '{query}': {e}")
        return []

def map_genre(deezer_genre_name):
    """Mapea el nombre del género Deezer al género MoodMusic."""
    if not deezer_genre_name:
        return "Pop"
    for key, val in GENRE_MAP.items():
        if key.lower() in deezer_genre_name.lower():
            return val
    return "Pop"

def infer_mood_context(genre_mm, artist_name, track_name):
    """Infiere estado de ánimo y contexto desde género y nombre de canción."""
    import random
    moods, contexts = GENRE_MOOD_CONTEXT.get(genre_mm, (["Alegre"], ["Casa"]))
    
    title_lower = track_name.lower()
    artist_lower = artist_name.lower()
    
    # Palabras clave para afinar ánimo
    sad_words = ["sad", "cry", "tear", "alone", "hurt", "pain", "triste", "lloro", "dolor", "sin ti"]
    happy_words = ["happy", "joy", "feliz", "alegr", "party", "fiesta", "celebrate"]
    calm_words = ["chill", "relax", "sleep", "dream", "sueño", "calma", "tranquil", "night", "noche"]
    energetic_words = ["power", "run", "fire", "go", "push", "fuerza", "energia", "beast"]
    romantic_words = ["love", "heart", "kiss", "amor", "corazon", "beso", "romance", "together"]
    stress_words = ["stress", "anxiety", "worry", "breath", "breathe"]
    
    for w in sad_words:
        if w in title_lower:
            return random.choice(["Triste"]), random.choice(["Casa", "Descanso"])
    for w in happy_words:
        if w in title_lower:
            return random.choice(["Alegre"]), random.choice(["Fiesta", "Casa"])
    for w in calm_words:
        if w in title_lower:
            return random.choice(["Tranquilo"]), random.choice(["Descanso", "Estudio"])
    for w in energetic_words:
        if w in title_lower:
            return random.choice(["Energico"]), random.choice(["Ejercicio", "Trabajo"])
    for w in romantic_words:
        if w in title_lower:
            return random.choice(["Romantico"]), random.choice(["Casa", "Descanso"])
    for w in stress_words:
        if w in title_lower:
            return random.choice(["Estresado"]), random.choice(["Descanso", "Casa"])
    
    return random.choice(moods), random.choice(contexts)

def sanitize_id(text):
    """Convierte texto a identificador RDF seguro."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', text)

def ttl_string(s):
    """Escapa una cadena para Turtle."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

def main():
    print("Iniciando recolección de canciones desde Deezer...")
    
    seen_ids = set()
    songs = []
    
    for query in SEARCH_QUERIES:
        if len(songs) >= 2500:
            break
        print(f"Buscando: {query} ({len(songs)} canciones hasta ahora)")
        results = deezer_search(query, limit=50)
        
        for track in results:
            if len(songs) >= 2500:
                break
            
            title = track.get("title_short") or track.get("title", "")
            artist = track.get("artist", {}).get("name", "")
            
            if not title or not artist:
                continue
            
            # Deduplicar: si el título ya existe para este artista, saltar
            key = f"{title.lower()}|{artist.lower()}"
            if key in seen_ids:
                continue
            seen_ids.add(key)
            
            # Obtener género
            album = track.get("album", {})
            genre_name = ""
            # Deezer search no devuelve genre directamente, inferir desde el query
            for dz_key in GENRE_MAP:
                if dz_key.lower() in query.lower():
                    genre_name = dz_key
                    break
            
            genre_mm = map_genre(genre_name)
            
            # Inferir ánimo y contexto
            mood, context = infer_mood_context(genre_mm, artist, title)
            
            # Calificación basada en rank
            rank = track.get("rank", 50000)
            rating = min(5.0, max(3.5, round(3.5 + (rank / 1000000) * 1.5, 1)))
            
            # Duración
            duration_secs = track.get("duration", 210)
            mins = duration_secs // 60
            secs = duration_secs % 60
            duration_str = f"{mins}:{secs:02d}"
            
            songs.append({
                "title": title,
                "artist": artist,
                "genre": genre_mm,
                "mood": mood,
                "context": context,
                "rating": rating,
                "duration": duration_str,
            })
        
        time.sleep(0.3)  # Rate limit suave
    
    print(f"\nTotal canciones recolectadas: {len(songs)}")
    
    # Leer TTL existente
    with open("datos/grafo.ttl", "r", encoding="utf-8") as f:
        existing = f.read()
    
    # Encontrar el número más alto de canción existente
    existing_nums = re.findall(r'mm:Cancion(\d+)', existing)
    next_num = max([int(n) for n in existing_nums], default=50) + 1
    
    # Construir TTL para nuevas canciones
    new_ttl_parts = []
    genres_used = set()
    
    for song in songs:
        # Verificar si ya existe (por título y artista)
        title_safe = ttl_string(song["title"])
        artist_safe = ttl_string(song["artist"])
        
        # Si ya está en el grafo, saltar
        if f'mm:titulo "{title_safe}"' in existing and f'mm:artista "{artist_safe}"' in existing:
            continue
        
        cancion_id = f"mm:Cancion{next_num}"
        next_num += 1
        genres_used.add(song["genre"])
        
        part = f"""{cancion_id} a mm:Cancion ;
    mm:aptoParaAnimo mm:{song["mood"]} ;
    mm:aptoParaContexto mm:{song["context"]} ;
    mm:artista "{artist_safe}" ;
    mm:calificacion "{song["rating"]}"^^xsd:float ;
    mm:duracion "{song["duration"]}" ;
    mm:perteneceAGenero mm:{song["genre"]} ;
    mm:titulo "{title_safe}" .\n"""
        new_ttl_parts.append(part)
    
    # Asegurarse de que todos los géneros usados están declarados
    genre_declarations = []
    all_genres = set(GENRE_MAP.values()) | genres_used
    for g in all_genres:
        if f"mm:{g} a mm:Genero" not in existing:
            genre_declarations.append(f"\nmm:{g} a mm:Genero .\n")
    
    # Append al grafo
    with open("datos/grafo.ttl", "a", encoding="utf-8") as f:
        f.write("\n")
        for part in new_ttl_parts:
            f.write("\n" + part)
        for decl in genre_declarations:
            f.write(decl)
    
    total_new = len(new_ttl_parts)
    print(f"Se agregaron {total_new} nuevas canciones al grafo.")
    print("Archivo datos/grafo.ttl actualizado.")

if __name__ == "__main__":
    main()

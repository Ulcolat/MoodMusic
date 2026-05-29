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

# Reglas de inferencia: género -> lista de (ánimo, contexto) válidos
# Cada par (ánimo, contexto) es una combinación legítima para ese género.
# Una canción recibirá UNA combinación al poblar, pero el algoritmo de
# recomendación tiene fallback escalonado para cubrir los huecos.
GENRE_MOOD_CONTEXT = {
    "Pop":        [
        ("Alegre","Fiesta"), ("Alegre","Casa"), ("Alegre","Trabajo"),
        ("Romantico","Casa"), ("Romantico","Descanso"),
        ("Energico","Ejercicio"), ("Energico","Trabajo"),
        ("Triste","Casa"), ("Triste","Descanso"),
        ("Tranquilo","Estudio"), ("Tranquilo","Casa"),
    ],
    "HipHop":     [
        ("Energico","Ejercicio"), ("Energico","Trabajo"), ("Energico","Fiesta"),
        ("Estresado","Casa"), ("Estresado","Descanso"),
        ("Triste","Casa"), ("Triste","Descanso"),
        ("Alegre","Fiesta"),
    ],
    "Rock":       [
        ("Energico","Ejercicio"), ("Energico","Trabajo"),
        ("Estresado","Ejercicio"), ("Estresado","Casa"),
        ("Triste","Casa"), ("Triste","Descanso"),
        ("Alegre","Fiesta"),
    ],
    "Electronic": [
        ("Energico","Ejercicio"), ("Energico","Fiesta"), ("Energico","Trabajo"),
        ("Tranquilo","Estudio"), ("Tranquilo","Descanso"),
        ("Alegre","Fiesta"),
    ],
    "RnB":        [
        ("Romantico","Casa"), ("Romantico","Descanso"), ("Romantico","Fiesta"),
        ("Tranquilo","Casa"), ("Tranquilo","Descanso"), ("Tranquilo","Estudio"),
        ("Alegre","Casa"), ("Alegre","Fiesta"),
        ("Triste","Casa"), ("Triste","Descanso"),
    ],
    "Jazz":       [
        ("Tranquilo","Casa"), ("Tranquilo","Descanso"), ("Tranquilo","Trabajo"), ("Tranquilo","Estudio"),
        ("Romantico","Casa"), ("Romantico","Descanso"),
        ("Estresado","Descanso"),
        ("Triste","Casa"),
    ],
    "Classical":  [
        ("Tranquilo","Estudio"), ("Tranquilo","Descanso"), ("Tranquilo","Casa"),
        ("Estresado","Descanso"), ("Estresado","Estudio"),
        ("Triste","Casa"), ("Triste","Descanso"), ("Triste","Estudio"),
    ],
    "Latin":      [
        ("Alegre","Fiesta"), ("Alegre","Casa"),
        ("Romantico","Casa"), ("Romantico","Fiesta"),
        ("Energico","Fiesta"), ("Energico","Ejercicio"),
    ],
    "Reggaeton":  [
        ("Alegre","Fiesta"), ("Alegre","Ejercicio"),
        ("Energico","Fiesta"), ("Energico","Ejercicio"),
        ("Tranquilo","Casa"), ("Romantico","Casa"),
        ("Triste","Casa"),
    ],
    "Urbano":     [
        ("Tranquilo","Casa"), ("Tranquilo","Descanso"),
        ("Romantico","Casa"), ("Romantico","Descanso"),
        ("Alegre","Fiesta"), ("Alegre","Casa"),
        ("Triste","Casa"), ("Triste","Descanso"),
        ("Estresado","Casa"),
    ],
    "Indie":      [
        ("Tranquilo","Estudio"), ("Tranquilo","Casa"), ("Tranquilo","Descanso"),
        ("Triste","Casa"), ("Triste","Descanso"), ("Triste","Estudio"),
        ("Alegre","Casa"),
    ],
    "LoFi":       [
        ("Tranquilo","Estudio"), ("Tranquilo","Trabajo"), ("Tranquilo","Descanso"),
        ("Estresado","Estudio"), ("Estresado","Descanso"),
        ("Triste","Estudio"),
    ],
    "Salsa":      [
        ("Alegre","Fiesta"), ("Alegre","Casa"),
        ("Energico","Fiesta"), ("Energico","Ejercicio"),
        ("Romantico","Fiesta"),
    ],
    "Metal":      [
        ("Energico","Ejercicio"), ("Energico","Trabajo"),
        ("Estresado","Ejercicio"), ("Estresado","Casa"),
    ],
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

# Contador global para distribuir las combinaciones de forma round-robin
_combo_counter = {}

def infer_mood_context(genre_mm, artist_name, track_name):
    """
    Infiere estado de ánimo y contexto.
    Primero intenta detectar palabras clave en el título.
    Si no hay coincidencia, distribuye en round-robin sobre todas las
    combinaciones válidas del género para garantizar cobertura uniforme.
    """
    import random
    pairs = GENRE_MOOD_CONTEXT.get(genre_mm, [("Alegre", "Casa")])

    title_lower = track_name.lower()

    # Palabras clave -> pares preferidos
    keyword_pairs = [
        (["sad","cry","tear","alone","hurt","pain","triste","lloro","dolor","sin ti"],
         [p for p in pairs if p[0] == "Triste"] or [("Triste","Casa")]),
        (["happy","joy","feliz","alegr","party","fiesta","celebrate"],
         [p for p in pairs if p[0] == "Alegre"] or [("Alegre","Fiesta")]),
        (["chill","relax","sleep","dream","sueño","calma","tranquil","night","noche","lofi","lo-fi"],
         [p for p in pairs if p[0] == "Tranquilo"] or [("Tranquilo","Descanso")]),
        (["power","run","fire","push","fuerza","energia","beast","hype"],
         [p for p in pairs if p[0] == "Energico"] or [("Energico","Ejercicio")]),
        (["love","heart","kiss","amor","corazon","beso","romance","together","darling"],
         [p for p in pairs if p[0] == "Romantico"] or [("Romantico","Casa")]),
        (["stress","anxiety","worry","breath","overwhelm"],
         [p for p in pairs if p[0] == "Estresado"] or [("Estresado","Descanso")]),
        (["study","estudia","focus","concentr","work","trabaj","office"],
         [p for p in pairs if p[1] in ("Estudio","Trabajo")] or [pairs[0]]),
        (["gym","workout","ejercicio","training","run","corr"],
         [p for p in pairs if p[1] == "Ejercicio"] or [pairs[0]]),
        (["party","fiesta","dance","bailar","club"],
         [p for p in pairs if p[1] == "Fiesta"] or [pairs[0]]),
    ]

    for keywords, candidates in keyword_pairs:
        if any(w in title_lower for w in keywords):
            chosen = random.choice(candidates)
            return chosen[0], chosen[1]

    # Round-robin para cubrir todas las combinaciones del género
    global _combo_counter
    idx = _combo_counter.get(genre_mm, 0)
    chosen = pairs[idx % len(pairs)]
    _combo_counter[genre_mm] = idx + 1
    return chosen[0], chosen[1]
    
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
        
        semantic_pairs = GENRE_MOOD_CONTEXT.get(song["genre"], [(song["mood"], song["context"])])
        moods = list(set([m for m,c in semantic_pairs]))
        contexts = list(set([c for m,c in semantic_pairs]))

        mood_lines = " ;\n    ".join([f"mm:aptoParaAnimo mm:{m}" for m in moods[:3]])
        context_lines = " ;\n    ".join([f"mm:aptoParaContexto mm:{c}" for c in contexts[:3]])

        part = f"""{cancion_id} a mm:Cancion ;
    {mood_lines} ;
    {context_lines} ;
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

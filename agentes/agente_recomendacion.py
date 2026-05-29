# ==================== AGENTE DE RECOMENDACIÓN ====================
# Responsabilidad: generar recomendaciones personalizadas desde el grafo RDF.
# Mejorado: scoring por perfil de usuario (géneros/artistas favoritos vs rechazados).

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, XSD
import os
import urllib.request
import urllib.parse
import json

MM = Namespace("http://www.semanticweb.org/moodmusic#")

GRAFO_PATH = os.path.join(os.path.dirname(__file__), "..", "datos", "grafo.ttl")

# Todos los géneros que maneja el sistema
ALL_GENRES = [
    "Pop", "Rock", "LoFi", "Electronic", "Jazz", "RnB", "Classical",
    "HipHop", "Reggaeton", "Urbano", "Latin", "Indie", "Salsa", "Metal",
]


class AgenteRecomendacion:
    def _normalizar(self, texto):
        return str(texto).strip().lower().replace("_", " ")

    """
    Agente que genera recomendaciones de canciones.
    
    Algoritmo de scoring:
    1. Base: coincidencia de estado de ánimo (requerido) y contexto (+2 puntos).
    2. Personalización: género favorito del usuario (+2), artista favorito (+3).
    3. Penalización: género rechazado (-5), canción no gustada (excluida).
    4. Calificación de la canción normalizada como desempate.
    
    Verificación de Deezer: cuando la búsqueda retorna múltiples resultados
    para el mismo título, se prefiere el que coincida exactamente con el artista
    registrado en el grafo (evita confusión entre artista y canción homónima).
    """

    def __init__(self):
        self.grafo_path = GRAFO_PATH
        self._cache_grafo = None
        self._cache_mtime = None

    # ──────────────────────────────────────────────
    # Carga del grafo con caché
    # ──────────────────────────────────────────────

    def _grafo(self):
        mtime = os.path.getmtime(self.grafo_path) if os.path.exists(self.grafo_path) else 0
        if self._cache_grafo is None or mtime != self._cache_mtime:
            g = Graph()
            if os.path.exists(self.grafo_path):
                g.parse(self.grafo_path, format="turtle")
            self._cache_grafo = g
            self._cache_mtime = mtime
        return self._cache_grafo

    # ──────────────────────────────────────────────
    # Serialización de una canción
    # ──────────────────────────────────────────────

    def _cancion_dict(self, g, cancion_uri):
        local = str(cancion_uri).split("#")[-1]
        titulo = str(g.value(cancion_uri, MM.titulo) or "")
        artista = str(g.value(cancion_uri, MM.artista) or "")
        genero_uri = g.value(cancion_uri, MM.perteneceAGenero)
        genero = str(genero_uri).split("#")[-1] if genero_uri else ""
        calificacion = float(g.value(cancion_uri, MM.calificacion) or 0)
        duracion = str(g.value(cancion_uri, MM.duracion) or "")
        animos = [str(x).split("#")[-1] for x in g.objects(cancion_uri, MM.aptoParaAnimo)]
        contextos = [str(x).split("#")[-1] for x in g.objects(cancion_uri, MM.aptoParaContexto)]

        return {
            "id": local,
            "titulo": titulo,
            "artista": artista,
            "genero": genero,
            "calificacion": calificacion,
            "duracion": duracion,
            "animos": animos,
            "contextos": contextos,
            # Valores singulares por defecto (el primero de la lista)
            # recomendar() los sobreescribe con el valor que pidió el usuario
            "animo": animos[0] if animos else "",
            "contexto": contextos[0] if contextos else "",
        }

    # ──────────────────────────────────────────────
    # Recomendación principal
    # ──────────────────────────────────────────────

    def recomendar(
        self,
        usuario_id: str,
        estado_animo: str,
        contexto: str,
        canciones_no_gustadas: list = None,
        generos_favoritos: list = None,
        artistas_favoritos: list = None,
        generos_rechazados: list = None,
        limite: int = 10,
    ) -> list:
        """
        Genera recomendaciones con fallback escalonado:
          Nivel 1 — ánimo + contexto exactos          (score alto)
          Nivel 2 — solo ánimo, sin contexto exacto   (score medio)
          Nivel 3 — cualquier canción no excluida     (relleno si grafo muy pequeño)

        Estrategia: usar consultas SPARQL para reducir candidatos (mejor rendimiento)
        sin cambiar el scoring ni la semántica del resultado.
        """
        g = self._grafo()
        excluidas = set(canciones_no_gustadas or [])
        favs_g = set(generos_favoritos or [])
        favs_a = set(artistas_favoritos or [])
        rech_g = set(generos_rechazados or [])

        def _score(c: dict, contexto_match: bool) -> float:
            score = 0.0
            if contexto_match:
                score += 10.0
            if c["genero"] in favs_g:
                score += 4.0
            if c["artista"] in favs_a:
                score += 6.0
            import random
            score += c["calificacion"] * 0.5
            score += random.uniform(0, 1.5)
            return score

        # Preparar URIs para filtros SPARQL
        excluidas_uris = [str(MM[s]) for s in excluidas]
        rech_g_uris = [str(MM[g]) for g in rech_g]

        prefixes = """
PREFIX mm: <http://www.semanticweb.org/moodmusic#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""

        def _build_where(animo=None, ctx=None):
            where = ["?s rdf:type mm:Cancion ."]
            if animo:
                where.append(f"?s mm:aptoParaAnimo mm:{animo} .")
            if ctx:
                where.append(f"?s mm:aptoParaContexto mm:{ctx} .")
            if rech_g_uris:
                uris = ", ".join(f"<{u}>" for u in rech_g_uris)
                where.append(f"FILTER NOT EXISTS {{ ?s mm:perteneceAGenero ?g . FILTER(?g IN ({uris})) }} .")
            if excluidas_uris:
                excl = ", ".join(f"<{u}>" for u in excluidas_uris)
                where.append(f"FILTER (?s NOT IN ({excl})) .")
            return where

        def _query_song_uris(animo=None, ctx=None, limit=200):
            where = _build_where(animo, ctx)
            q = prefixes + "SELECT DISTINCT ?s WHERE { " + " ".join(where) + " } LIMIT %d" % limit
            try:
                res = g.query(q)
                return [row.s for row in res]
            except Exception:
                # Fallback a recorrido clásico si SPARQL falla
                return list(g.subjects(RDF.type, MM.Cancion))

        nivel1_uris = _query_song_uris(animo=estado_animo, ctx=contexto, limit=300)
        nivel2_uris = _query_song_uris(animo=estado_animo, ctx=None, limit=500)
        nivel3_uris = _query_song_uris(animo=None, ctx=None, limit=1000)

        seen = set()
        nivel1, nivel2, nivel3 = [], [], []

        for uri in nivel1_uris:
            local = str(uri).split('#')[-1]
            if local in seen:
                continue
            c = self._cancion_dict(g, uri)
            if c['id'] in excluidas:
                continue
            if c['genero'] in rech_g:
                continue
            seen.add(c['id'])
            nivel1.append((_score(c, True), c))

        for uri in nivel2_uris:
            local = str(uri).split('#')[-1]
            if local in seen:
                continue
            c = self._cancion_dict(g, uri)
            if c['id'] in excluidas:
                continue
            if c['genero'] in rech_g:
                continue
            if estado_animo in c.get('animos', []):
                seen.add(c['id'])
                nivel2.append((_score(c, False), c))

        for uri in nivel3_uris:
            local = str(uri).split('#')[-1]
            if local in seen:
                continue
            c = self._cancion_dict(g, uri)
            if c['id'] in excluidas:
                continue
            if c['genero'] in rech_g:
                continue
            if estado_animo not in c.get('animos', []):
                seen.add(c['id'])
                nivel3.append((_score(c, False), c))

        for nivel in (nivel1, nivel2, nivel3):
            nivel.sort(key=lambda x: x[0], reverse=True)

        def _with_match(c, animo_val, ctx_val):
            out = dict(c)
            out['animo'] = animo_val
            out['contexto'] = ctx_val
            return out

        resultado = []
        for _, c in nivel1:
            resultado.append(_with_match(c, estado_animo, contexto))
            if len(resultado) >= limite:
                return resultado

        for _, c in nivel2:
            resultado.append(_with_match(c, estado_animo, contexto))
            if len(resultado) >= limite:
                return resultado

        for _, c in nivel3:
            resultado.append(_with_match(c, estado_animo, contexto))
            if len(resultado) >= limite:
                return resultado

        return resultado

    # ──────────────────────────────────────────────
    # Recomendación por género
    # ──────────────────────────────────────────────

    def recomendar_por_genero(self, genero: str, limite: int = 10) -> list:
        g = self._grafo()
        canciones = []
        for cancion_uri in g.subjects(RDF.type, MM.Cancion):
            genero_uri = g.value(cancion_uri, MM.perteneceAGenero)
            genero_local = str(genero_uri).split("#")[-1] if genero_uri else ""
            if self._normalizar(genero_local) == self._normalizar(genero):
                c = self._cancion_dict(g, cancion_uri)
                canciones.append(c)
        canciones.sort(key=lambda x: x["calificacion"], reverse=True)
        return canciones[:limite]

    # ──────────────────────────────────────────────
    # Mejor valoradas
    # ──────────────────────────────────────────────

    def obtener_mejor_valoradas(self, limite: int = 5) -> list:
        g = self._grafo()
        canciones = []
        for cancion_uri in g.subjects(RDF.type, MM.Cancion):
            c = self._cancion_dict(g, cancion_uri)
            canciones.append(c)
        canciones.sort(key=lambda x: x["calificacion"], reverse=True)
        return canciones[:limite]

    # ──────────────────────────────────────────────
    # Géneros disponibles en el grafo
    # ──────────────────────────────────────────────

    def generos_disponibles(self) -> list:
        """Retorna los géneros que realmente tienen canciones en el grafo."""
        g = self._grafo()
        generos = set()
        for cancion_uri in g.subjects(RDF.type, MM.Cancion):
            genero_uri = g.value(cancion_uri, MM.perteneceAGenero)
            if genero_uri:
                generos.add(str(genero_uri).split("#")[-1])
        return sorted(generos)

    # ──────────────────────────────────────────────
    # Búsqueda de preview en Deezer con verificación de artista
    # ──────────────────────────────────────────────

    @staticmethod
    def buscar_preview_deezer(titulo: str, artista: str) -> str | None:
        """
        Busca en Deezer el preview de 30s.
        Si hay varios resultados con el mismo título, prioriza el que coincide
        exactamente con el artista registrado (evita homonimias artista/canción).
        """
        query = urllib.parse.quote(f"{titulo} {artista}")
        url = f"https://api.deezer.com/search?q={query}&limit=10"
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                data = json.loads(r.read())
            results = data.get("data", [])
            if not results:
                return None

            # Exacto: título y artista coinciden (case-insensitive)
            for item in results:
                t = item.get("title_short") or item.get("title", "")
                a = item.get("artist", {}).get("name", "")
                if (t.lower() == titulo.lower() and
                        a.lower() == artista.lower() and
                        item.get("preview")):
                    return item["preview"]

            # Fallback: mismo título, cualquier artista
            for item in results:
                t = item.get("title_short") or item.get("title", "")
                if t.lower() == titulo.lower() and item.get("preview"):
                    return item["preview"]

            # Último recurso: primer resultado con preview
            for item in results:
                if item.get("preview"):
                    return item["preview"]

            return None
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # Canciones por artista
    # ──────────────────────────────────────────────

    def canciones_por_artista(self, artista: str, limite: int = 50) -> list:
        """Retorna todas las canciones de un artista en el grafo."""
        g = self._grafo()
        canciones = []
        for cancion_uri in g.subjects(RDF.type, MM.Cancion):
            artista_grafo = str(g.value(cancion_uri, MM.artista) or "")
            if artista_grafo.lower() == artista.lower():
                c = self._cancion_dict(g, cancion_uri)
                canciones.append(c)
        canciones.sort(key=lambda x: x["calificacion"], reverse=True)
        return canciones[:limite]

    # ──────────────────────────────────────────────
    # Info del artista
    # ──────────────────────────────────────────────

    def buscar_info_artista(self, nombre_artista: str) -> dict:
        """
        Busca canciones del artista en el grafo RDF y enriquece con
        foto y bio desde la API de Deezer.
        """
        canciones = self.canciones_por_artista(nombre_artista)
        foto, bio, seguidores, nb_fans = None, None, None, None

        try:
            query = urllib.parse.quote(nombre_artista)
            url = f"https://api.deezer.com/search/artist?q={query}&limit=5"
            with urllib.request.urlopen(url, timeout=6) as r:
                data = json.loads(r.read())
            results = data.get("data", [])
            # Buscar coincidencia exacta (case-insensitive)
            artista_obj = None
            for item in results:
                if item.get("name", "").lower() == nombre_artista.lower():
                    artista_obj = item
                    break
            if artista_obj is None and results:
                artista_obj = results[0]

            if artista_obj:
                artista_id = artista_obj.get("id")
                foto = artista_obj.get("picture_xl") or artista_obj.get("picture_big") or artista_obj.get("picture")
                nb_fans = artista_obj.get("nb_fan")

                # Obtener bio desde endpoint de detalle del artista
                if artista_id:
                    detail_url = f"https://api.deezer.com/artist/{artista_id}"
                    with urllib.request.urlopen(detail_url, timeout=6) as r2:
                        detail = json.loads(r2.read())
                    # Deezer no da bio directamente, pero sí nb_fan y tracklist count
                    nb_fans = detail.get("nb_fan", nb_fans)
                    # Generar bio básica con datos disponibles
                    nb_album = detail.get("nb_album", 0)
                    radio = detail.get("radio", False)
                    bio = f"{nombre_artista} tiene {nb_fans:,} seguidores en Deezer y {nb_album} álbumes disponibles." if nb_fans else None
        except Exception:
            pass

        # Contar géneros para mostrar estadísticas
        generos_conteo = {}
        for c in canciones:
            g = c.get("genero", "")
            if g:
                generos_conteo[g] = generos_conteo.get(g, 0) + 1
        generos_top = sorted(generos_conteo.items(), key=lambda x: x[1], reverse=True)

        return {
            "nombre": nombre_artista,
            "foto": foto,
            "bio": bio,
            "nb_fans": nb_fans,
            "generos": generos_top,
            "canciones": canciones,
        }

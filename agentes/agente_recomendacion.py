# ==================== AGENTE DE RECOMENDACIÓN ====================
# Responsabilidad: consultar el grafo RDF mediante SPARQL y generar
# una lista de canciones recomendadas según el perfil del usuario.

from rdflib import Graph, Namespace
import os

# ==================== CONFIGURACIÓN ====================

MM = Namespace("http://www.semanticweb.org/moodmusic#")
RUTA_GRAFO = os.path.join(os.path.dirname(__file__), "..", "datos", "grafo.ttl")


# ==================== CLASE PRINCIPAL ====================

class AgenteRecomendacion:
    """
    Agente encargado de generar recomendaciones musicales
    personalizadas consultando el grafo RDF con SPARQL.
    """

    def __init__(self):
        self.grafo = Graph()
        self.grafo.bind("mm", MM)
        self._cargar_grafo()

    # ==================== CARGA ====================

    def _cargar_grafo(self):
        """Carga el grafo RDF desde el archivo .ttl."""
        if os.path.exists(RUTA_GRAFO):
            self.grafo.parse(RUTA_GRAFO, format="turtle")

    def recargar_grafo(self):
        """
        Recarga el grafo desde el archivo .ttl.
        Se llama cada vez que el Agente de Perfil actualiza el grafo,
        para garantizar que las recomendaciones usen datos frescos.
        """
        self.grafo = Graph()
        self.grafo.bind("mm", MM)
        self._cargar_grafo()

    # ==================== CONSULTAS SPARQL ====================

    def _construir_query(self, estado_animo, contexto, canciones_excluidas):
        """
        Construye la consulta SPARQL según el perfil del usuario.

        Args:
            estado_animo (str): Estado de ánimo del usuario. Ej: 'Alegre'
            contexto (str): Contexto del usuario. Ej: 'Estudio'
            canciones_excluidas (list): Canciones que no le gustan al usuario.

        Returns:
            str: Consulta SPARQL lista para ejecutarse.
        """
        # Construir filtro de exclusión dinámicamente
        if canciones_excluidas:
            filtros = " && ".join([
                f'?cancion != mm:{c}' for c in canciones_excluidas
            ])
            bloque_filtro = f"FILTER ({filtros})"
        else:
            bloque_filtro = ""

        query = f"""
            PREFIX mm: <http://www.semanticweb.org/moodmusic#>

            SELECT ?cancion ?titulo ?artista ?duracion ?calificacion ?genero
            WHERE {{
                ?cancion a mm:Cancion ;
                         mm:titulo ?titulo ;
                         mm:artista ?artista ;
                         mm:duracion ?duracion ;
                         mm:calificacion ?calificacion ;
                         mm:perteneceAGenero ?generoUri ;
                         mm:aptoParaAnimo mm:{estado_animo} ;
                         mm:aptoParaContexto mm:{contexto} .

                BIND(STRAFTER(STR(?generoUri), "#") AS ?genero)

                {bloque_filtro}
            }}
            ORDER BY DESC(?calificacion)
        """
        return query

    # ==================== RECOMENDACIONES ====================

    def recomendar(self, usuario_id, estado_animo, contexto, canciones_no_gustadas=None):
        """
        Genera una lista de canciones recomendadas para el usuario.

        Args:
            usuario_id (str): Identificador del usuario.
            estado_animo (str): Estado de ánimo actual del usuario.
            contexto (str): Contexto actual del usuario.
            canciones_no_gustadas (list): Canciones a excluir. Por defecto None.

        Returns:
            list: Lista de diccionarios con la información de cada canción recomendada.
        """
        # Recargar grafo para tener datos actualizados
        self.recargar_grafo()

        if canciones_no_gustadas is None:
            canciones_no_gustadas = []

        query = self._construir_query(estado_animo, contexto, canciones_no_gustadas)

        resultados = []
        for fila in self.grafo.query(query):
            cancion_id = str(fila.cancion).split("#")[-1]
            resultados.append({
                "id": cancion_id,
                "titulo": str(fila.titulo),
                "artista": str(fila.artista),
                "duracion": str(fila.duracion),
                "calificacion": float(fila.calificacion),
                "genero": str(fila.genero),
            })

        return resultados

    def recomendar_por_genero(self, genero, limite=5):
        """
        Genera recomendaciones filtradas únicamente por género musical.
        Útil para el dashboard cuando el usuario quiere explorar un género.

        Args:
            genero (str): Género musical. Ej: 'Jazz', 'LoFi', 'Rock'
            limite (int): Cantidad máxima de canciones a retornar.

        Returns:
            list: Lista de diccionarios con la información de cada canción.
        """
        self.recargar_grafo()

        query = f"""
            PREFIX mm: <http://www.semanticweb.org/moodmusic#>

            SELECT ?cancion ?titulo ?artista ?duracion ?calificacion
            WHERE {{
                ?cancion a mm:Cancion ;
                         mm:titulo ?titulo ;
                         mm:artista ?artista ;
                         mm:duracion ?duracion ;
                         mm:calificacion ?calificacion ;
                         mm:perteneceAGenero mm:{genero} .
            }}
            ORDER BY DESC(?calificacion)
            LIMIT {limite}
        """

        resultados = []
        for fila in self.grafo.query(query):
            cancion_id = str(fila.cancion).split("#")[-1]
            resultados.append({
                "id": cancion_id,
                "titulo": str(fila.titulo),
                "artista": str(fila.artista),
                "duracion": str(fila.duracion),
                "calificacion": float(fila.calificacion),
                "genero": genero,
            })

        return resultados

    def obtener_mejor_valoradas(self, limite=5):
        """
        Retorna las canciones mejor valoradas del grafo.
        Útil para mostrar en el dashboard como sección destacada.

        Args:
            limite (int): Cantidad máxima de canciones a retornar.

        Returns:
            list: Lista de diccionarios con la información de cada canción.
        """
        self.recargar_grafo()

        query = f"""
            PREFIX mm: <http://www.semanticweb.org/moodmusic#>

            SELECT ?cancion ?titulo ?artista ?duracion ?calificacion ?genero
            WHERE {{
                ?cancion a mm:Cancion ;
                         mm:titulo ?titulo ;
                         mm:artista ?artista ;
                         mm:duracion ?duracion ;
                         mm:calificacion ?calificacion ;
                         mm:perteneceAGenero ?generoUri .

                BIND(STRAFTER(STR(?generoUri), "#") AS ?genero)
            }}
            ORDER BY DESC(?calificacion)
            LIMIT {limite}
        """

        resultados = []
        for fila in self.grafo.query(query):
            cancion_id = str(fila.cancion).split("#")[-1]
            resultados.append({
                "id": cancion_id,
                "titulo": str(fila.titulo),
                "artista": str(fila.artista),
                "duracion": str(fila.duracion),
                "calificacion": float(fila.calificacion),
                "genero": str(fila.genero),
            })

        return resultados
# ==================== AGENTE DE PERFIL DE USUARIO ====================
# Responsabilidad: gestionar perfiles de usuario en el grafo RDF.
# Mejorado: tracking de géneros y artistas favoritos para personalización.

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD
import os
import threading

MM = Namespace("http://www.semanticweb.org/moodmusic#")

# Ruta al grafo principal
GRAFO_PATH = os.path.join(os.path.dirname(__file__), "..", "datos", "grafo.ttl")

# Lock para evitar escrituras concurrentes
_lock = threading.Lock()


class AgentePerfilUsuario:
    """
    Agente que gestiona el perfil del usuario en el grafo RDF.
    
    Mantiene:
    - Estado de ánimo actual y contexto
    - Canciones gustadas y no gustadas
    - Géneros y artistas favoritos (inferidos de gustos)
    - Géneros y artistas rechazados
    """

    def __init__(self):
        self.grafo_path = GRAFO_PATH

    # ──────────────────────────────────────────────
    # Carga y guardado
    # ──────────────────────────────────────────────

    def _cargar_grafo(self):
        g = Graph()
        if os.path.exists(self.grafo_path):
            g.parse(self.grafo_path, format="turtle")
        return g

    def _guardar_grafo(self, g):
        with _lock:
            g.serialize(destination=self.grafo_path, format="turtle")

    # ──────────────────────────────────────────────
    # Gestión de usuarios
    # ──────────────────────────────────────────────

    def usuario_existe(self, usuario_id: str) -> bool:
        g = self._cargar_grafo()
        u = MM[usuario_id]
        return (u, RDF.type, MM.Usuario) in g

    def registrar_usuario(self, usuario_id: str, nombre: str, email: str):
        g = self._cargar_grafo()
        u = MM[usuario_id]
        g.add((u, RDF.type, MM.Usuario))
        g.add((u, MM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((u, MM.email, Literal(email, datatype=XSD.string)))
        self._guardar_grafo(g)

    def obtener_perfil(self, usuario_id: str) -> dict:
        g = self._cargar_grafo()
        u = MM[usuario_id]

        nombre = str(g.value(u, MM.nombre) or "")
        email = str(g.value(u, MM.email) or "")
        estado_animo = self._local(g.value(u, MM.tieneEstadoDeAnimo))
        contexto = self._local(g.value(u, MM.estaEnContexto))

        canciones_gustadas = [
            self._local(c) for c in g.objects(u, MM.leGusta)
        ]
        canciones_no_gustadas = [
            self._local(c) for c in g.objects(u, MM.noLeGusta)
        ]

        # Géneros favoritos (inferidos de canciones gustadas)
        generos_favoritos = list(
            {self._local(g.value(MM[c], MM.perteneceAGenero)) for c in canciones_gustadas
             if g.value(MM[c], MM.perteneceAGenero)}
        )
        # Artistas favoritos
        artistas_favoritos = list(
            {str(g.value(MM[c], MM.artista) or "") for c in canciones_gustadas
             if g.value(MM[c], MM.artista)}
        )
        # Géneros rechazados
        generos_rechazados = list(
            {self._local(g.value(MM[c], MM.perteneceAGenero)) for c in canciones_no_gustadas
             if g.value(MM[c], MM.perteneceAGenero)}
        )

        return {
            "usuario_id": usuario_id,
            "nombre": nombre,
            "email": email,
            "estado_animo": estado_animo,
            "contexto": contexto,
            "canciones_gustadas": canciones_gustadas,
            "canciones_no_gustadas": canciones_no_gustadas,
            "generos_favoritos": [g for g in generos_favoritos if g],
            "artistas_favoritos": [a for a in artistas_favoritos if a],
            "generos_rechazados": [g for g in generos_rechazados if g],
        }

    def actualizar_estado_animo(self, usuario_id: str, estado_animo: str):
        g = self._cargar_grafo()
        u = MM[usuario_id]
        g.remove((u, MM.tieneEstadoDeAnimo, None))
        g.add((u, MM.tieneEstadoDeAnimo, MM[estado_animo]))
        self._guardar_grafo(g)

    def actualizar_contexto(self, usuario_id: str, contexto: str):
        g = self._cargar_grafo()
        u = MM[usuario_id]
        g.remove((u, MM.estaEnContexto, None))
        g.add((u, MM.estaEnContexto, MM[contexto]))
        self._guardar_grafo(g)

    def agregar_cancion_gustada(self, usuario_id: str, cancion_id: str):
        g = self._cargar_grafo()
        u = MM[usuario_id]
        c = MM[cancion_id]
        # Quitar de no_gustadas si estaba
        g.remove((u, MM.noLeGusta, c))
        if (u, MM.leGusta, c) not in g:
            g.add((u, MM.leGusta, c))
        self._guardar_grafo(g)

    def agregar_cancion_no_gustada(self, usuario_id: str, cancion_id: str):
        g = self._cargar_grafo()
        u = MM[usuario_id]
        c = MM[cancion_id]
        # Quitar de gustadas si estaba
        g.remove((u, MM.leGusta, c))
        if (u, MM.noLeGusta, c) not in g:
            g.add((u, MM.noLeGusta, c))
        self._guardar_grafo(g)

    # ──────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────

    @staticmethod
    def _local(uri):
        """Extrae la parte local de una URI o retorna '' si es None."""
        if uri is None:
            return ""
        s = str(uri)
        return s.split("#")[-1] if "#" in s else s.split("/")[-1]

# ==================== AGENTE DE PERFIL DE USUARIO ====================
# Responsabilidad: recolectar, registrar y actualizar la información
# del usuario (estado de ánimo, contexto, gustos y disgustos) en el grafo RDF.

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, XSD
import os

# ==================== CONFIGURACIÓN ====================

MM = Namespace("http://www.semanticweb.org/moodmusic#")
RUTA_GRAFO = os.path.join(os.path.dirname(__file__), "..", "datos", "grafo.ttl")


# ==================== CLASE PRINCIPAL ====================

class AgentePerfilUsuario:
    """
    Agente encargado de mantener actualizado el perfil
    de cada usuario dentro del grafo RDF de MoodMusic.
    """

    def __init__(self):
        self.grafo = Graph()
        self.grafo.bind("mm", MM)
        self._cargar_grafo()

    # ==================== CARGA Y GUARDADO ====================

    def _cargar_grafo(self):
        """Carga el grafo RDF desde el archivo .ttl."""
        if os.path.exists(RUTA_GRAFO):
            self.grafo.parse(RUTA_GRAFO, format="turtle")

    def _guardar_grafo(self):
        """Guarda el estado actual del grafo en el archivo .ttl."""
        self.grafo.serialize(destination=RUTA_GRAFO, format="turtle")

    # ==================== GESTIÓN DE USUARIOS ====================

    def registrar_usuario(self, usuario_id, nombre, email):
        """
        Registra un nuevo usuario en el grafo RDF.

        Args:
            usuario_id (str): Identificador único del usuario. Ej: 'Usuario1'
            nombre (str): Nombre del usuario.
            email (str): Correo electrónico del usuario.
        """
        usuario = MM[usuario_id]

        # Evitar duplicados
        if (usuario, RDF.type, MM.Usuario) in self.grafo:
            return

        self.grafo.add((usuario, RDF.type, MM.Usuario))
        self.grafo.add((usuario, MM.nombre, Literal(nombre, datatype=XSD.string)))
        self.grafo.add((usuario, MM.email, Literal(email, datatype=XSD.string)))
        self._guardar_grafo()

    def usuario_existe(self, usuario_id):
        """
        Verifica si un usuario ya está registrado en el grafo.

        Args:
            usuario_id (str): Identificador del usuario.

        Returns:
            bool: True si existe, False si no.
        """
        usuario = MM[usuario_id]
        return (usuario, RDF.type, MM.Usuario) in self.grafo

    # ==================== ESTADO DE ÁNIMO ====================

    def actualizar_estado_animo(self, usuario_id, estado):
        """
        Actualiza el estado de ánimo actual del usuario en el grafo.

        Args:
            usuario_id (str): Identificador del usuario.
            estado (str): Estado de ánimo. Ej: 'Alegre', 'Triste', 'Tranquilo'.
        """
        usuario = MM[usuario_id]
        estado_uri = MM[estado]

        # Eliminar estado de ánimo anterior si existe
        self.grafo.remove((usuario, MM.tieneEstadoDeAnimo, None))

        # Registrar nuevo estado de ánimo
        self.grafo.add((usuario, MM.tieneEstadoDeAnimo, estado_uri))
        self._guardar_grafo()

    def obtener_estado_animo(self, usuario_id):
        """
        Obtiene el estado de ánimo actual del usuario.

        Args:
            usuario_id (str): Identificador del usuario.

        Returns:
            str | None: Nombre del estado de ánimo o None si no tiene.
        """
        usuario = MM[usuario_id]
        for _, _, estado in self.grafo.triples((usuario, MM.tieneEstadoDeAnimo, None)):
            return str(estado).split("#")[-1]
        return None

    # ==================== CONTEXTO ====================

    def actualizar_contexto(self, usuario_id, contexto):
        """
        Actualiza el contexto actual del usuario en el grafo.

        Args:
            usuario_id (str): Identificador del usuario.
            contexto (str): Contexto. Ej: 'Estudio', 'Ejercicio', 'Casa'.
        """
        usuario = MM[usuario_id]
        contexto_uri = MM[contexto]

        # Eliminar contexto anterior si existe
        self.grafo.remove((usuario, MM.estaEnContexto, None))

        # Registrar nuevo contexto
        self.grafo.add((usuario, MM.estaEnContexto, contexto_uri))
        self._guardar_grafo()

    def obtener_contexto(self, usuario_id):
        """
        Obtiene el contexto actual del usuario.

        Args:
            usuario_id (str): Identificador del usuario.

        Returns:
            str | None: Nombre del contexto o None si no tiene.
        """
        usuario = MM[usuario_id]
        for _, _, contexto in self.grafo.triples((usuario, MM.estaEnContexto, None)):
            return str(contexto).split("#")[-1]
        return None

    # ==================== GUSTOS Y DISGUSTOS ====================

    def agregar_cancion_gustada(self, usuario_id, cancion_id):
        """
        Registra que al usuario le gusta una canción.

        Args:
            usuario_id (str): Identificador del usuario.
            cancion_id (str): Identificador de la canción. Ej: 'Cancion1'.
        """
        usuario = MM[usuario_id]
        cancion = MM[cancion_id]

        # Si estaba en no le gusta, eliminarla de ahí
        self.grafo.remove((usuario, MM.noLeGusta, cancion))

        # Agregar a le gusta si no estaba ya
        if (usuario, MM.leGusta, cancion) not in self.grafo:
            self.grafo.add((usuario, MM.leGusta, cancion))
            self._guardar_grafo()

    def agregar_cancion_no_gustada(self, usuario_id, cancion_id):
        """
        Registra que al usuario no le gusta una canción.

        Args:
            usuario_id (str): Identificador del usuario.
            cancion_id (str): Identificador de la canción. Ej: 'Cancion1'.
        """
        usuario = MM[usuario_id]
        cancion = MM[cancion_id]

        # Si estaba en le gusta, eliminarla de ahí
        self.grafo.remove((usuario, MM.leGusta, cancion))

        # Agregar a no le gusta si no estaba ya
        if (usuario, MM.noLeGusta, cancion) not in self.grafo:
            self.grafo.add((usuario, MM.noLeGusta, cancion))
            self._guardar_grafo()

    def obtener_canciones_gustadas(self, usuario_id):
        """
        Obtiene la lista de canciones que le gustan al usuario
        con su título y artista reales.

        Returns:
            list: Lista de diccionarios con id, titulo y artista.
        """
        usuario = MM[usuario_id]
        canciones = []
        for _, _, cancion in self.grafo.triples((usuario, MM.leGusta, None)):
            cancion_id = str(cancion).split("#")[-1]
            titulo = self.grafo.value(cancion, MM.titulo) or cancion_id
            artista = self.grafo.value(cancion, MM.artista) or ""
            canciones.append({
                "id": cancion_id,
                "titulo": str(titulo),
                "artista": str(artista),
            })
        return canciones

    def obtener_canciones_no_gustadas(self, usuario_id):
        """
        Obtiene la lista de canciones descartadas por el usuario
        con su título y artista reales.

        Returns:
            list: Lista de diccionarios con id, titulo y artista.
        """
        usuario = MM[usuario_id]
        canciones = []
        for _, _, cancion in self.grafo.triples((usuario, MM.noLeGusta, None)):
            cancion_id = str(cancion).split("#")[-1]
            titulo = self.grafo.value(cancion, MM.titulo) or cancion_id
            artista = self.grafo.value(cancion, MM.artista) or ""
            canciones.append({
                "id": cancion_id,
                "titulo": str(titulo),
                "artista": str(artista),
            })
        return canciones
    # ==================== PERFIL COMPLETO ====================

    def obtener_perfil(self, usuario_id):
        """
        Retorna el perfil completo del usuario.

        Returns:
            dict: Diccionario con toda la información del perfil.
        """
        return {
            "usuario_id": usuario_id,
            "estado_animo": self.obtener_estado_animo(usuario_id),
            "contexto": self.obtener_contexto(usuario_id),
            "canciones_gustadas": self.obtener_canciones_gustadas(usuario_id),
            "canciones_no_gustadas": self.obtener_canciones_no_gustadas(usuario_id),
        }
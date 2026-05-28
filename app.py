# ==================== APP PRINCIPAL - MOODMUSIC ====================
# Responsabilidad: arrancar Flask, gestionar rutas y conectar
# el Agente de Perfil de Usuario con el Agente de Recomendación.

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from agentes.agente_perfil import AgentePerfilUsuario
from agentes.agente_recomendacion import AgenteRecomendacion
import os

# ==================== CONFIGURACIÓN ====================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "moodmusic_dev_key")

# Instancias de los agentes
agente_perfil = AgentePerfilUsuario()
agente_recomendacion = AgenteRecomendacion()

# Opciones disponibles en el sistema
ESTADOS_ANIMO = ["Alegre", "Triste", "Tranquilo", "Energico", "Estresado", "Romantico"]
CONTEXTOS = ["Ejercicio", "Estudio", "Casa", "Trabajo", "Fiesta", "Descanso"]
GENEROS = ["Pop", "Rock", "LoFi", "Electronic", "Jazz", "RnB", "Classical"]


# ==================== HELPERS ====================

def usuario_autenticado():
    """Verifica si hay un usuario en sesión."""
    return "usuario_id" in session


def obtener_usuario_sesion():
    """Retorna el usuario_id de la sesión activa."""
    return session.get("usuario_id")


# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route("/")
def inicio():
    """Redirige al dashboard si hay sesión, si no al login."""
    if usuario_autenticado():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET: Muestra el formulario de login.
    POST: Valida el usuario y crea la sesión.
    """
    if usuario_autenticado():
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        usuario_id = request.form.get("usuario_id", "").strip()
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()

        if not usuario_id or not nombre or not email:
            error = "Todos los campos son obligatorios."
        else:
            # Registrar usuario si no existe
            if not agente_perfil.usuario_existe(usuario_id):
                agente_perfil.registrar_usuario(usuario_id, nombre, email)

            # Crear sesión
            session["usuario_id"] = usuario_id
            session["nombre"] = nombre
            return redirect(url_for("dashboard"))

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    return redirect(url_for("login"))


# ==================== RUTAS PRINCIPALES ====================

@app.route("/dashboard")
def dashboard():
    """
    Muestra el dashboard principal con:
    - Perfil del usuario
    - Canciones mejor valoradas
    - Últimas recomendaciones si ya tiene estado de ánimo y contexto
    """
    if not usuario_autenticado():
        return redirect(url_for("login"))

    usuario_id = obtener_usuario_sesion()
    perfil = agente_perfil.obtener_perfil(usuario_id)
    mejor_valoradas = agente_recomendacion.obtener_mejor_valoradas(limite=5)

    # Si el usuario ya tiene estado de ánimo y contexto, mostrar recomendaciones
    recomendaciones = []
    if perfil["estado_animo"] and perfil["contexto"]:
        recomendaciones = agente_recomendacion.recomendar(
            usuario_id=usuario_id,
            estado_animo=perfil["estado_animo"],
            contexto=perfil["contexto"],
            canciones_no_gustadas=perfil["canciones_no_gustadas"]
        )

    return render_template(
        "dashboard.html",
        perfil=perfil,
        nombre=session.get("nombre"),
        mejor_valoradas=mejor_valoradas,
        recomendaciones=recomendaciones,
        estados_animo=ESTADOS_ANIMO,
        contextos=CONTEXTOS,
        generos=GENEROS
    )


@app.route("/recomendar", methods=["POST"])
def recomendar():
    """
    Recibe el estado de ánimo y contexto del usuario,
    actualiza su perfil en el grafo RDF y retorna
    las recomendaciones en formato JSON.
    """
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    usuario_id = obtener_usuario_sesion()
    estado_animo = request.form.get("estado_animo", "").strip()
    contexto = request.form.get("contexto", "").strip()

    if not estado_animo or not contexto:
        return jsonify({"error": "Estado de ánimo y contexto son obligatorios."}), 400

    if estado_animo not in ESTADOS_ANIMO:
        return jsonify({"error": "Estado de ánimo no válido."}), 400

    if contexto not in CONTEXTOS:
        return jsonify({"error": "Contexto no válido."}), 400

    # Actualizar perfil del usuario en el grafo RDF
    agente_perfil.actualizar_estado_animo(usuario_id, estado_animo)
    agente_perfil.actualizar_contexto(usuario_id, contexto)

    # Obtener canciones excluidas
    perfil = agente_perfil.obtener_perfil(usuario_id)

    # Generar recomendaciones
    recomendaciones = agente_recomendacion.recomendar(
        usuario_id=usuario_id,
        estado_animo=estado_animo,
        contexto=contexto,
        canciones_no_gustadas=perfil["canciones_no_gustadas"]
    )

    return jsonify({"recomendaciones": recomendaciones})


@app.route("/me_gusta", methods=["POST"])
def me_gusta():
    """
    Registra que al usuario le gusta una canción
    y actualiza el grafo RDF.
    """
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    usuario_id = obtener_usuario_sesion()
    cancion_id = request.form.get("cancion_id", "").strip()

    if not cancion_id:
        return jsonify({"error": "Canción no especificada."}), 400

    agente_perfil.agregar_cancion_gustada(usuario_id, cancion_id)
    return jsonify({"mensaje": f"{cancion_id} agregada a favoritos."})


@app.route("/no_me_gusta", methods=["POST"])
def no_me_gusta():
    """
    Registra que al usuario no le gusta una canción,
    la excluye de futuras recomendaciones y actualiza el grafo RDF.
    """
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    usuario_id = obtener_usuario_sesion()
    cancion_id = request.form.get("cancion_id", "").strip()

    if not cancion_id:
        return jsonify({"error": "Canción no especificada."}), 400

    agente_perfil.agregar_cancion_no_gustada(usuario_id, cancion_id)
    return jsonify({"mensaje": f"{cancion_id} excluida de recomendaciones."})


@app.route("/explorar/<genero>")
def explorar_genero(genero):
    """
    Retorna canciones filtradas por género musical.
    Útil para la sección de exploración del dashboard.

    Args:
        genero (str): Género musical a explorar.
    """
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    if genero not in GENEROS:
        return jsonify({"error": "Género no válido."}), 400

    canciones = agente_recomendacion.recomendar_por_genero(genero, limite=5)
    return jsonify({"canciones": canciones})


@app.route("/perfil")
def perfil():
    """Muestra el perfil completo del usuario."""
    if not usuario_autenticado():
        return redirect(url_for("login"))

    usuario_id = obtener_usuario_sesion()
    perfil_data = agente_perfil.obtener_perfil(usuario_id)

    return render_template(
        "perfil.html",
        perfil=perfil_data,
        nombre=session.get("nombre")
    )


# ==================== ARRANQUE ====================

if __name__ == "__main__":
    app.run(debug=True)
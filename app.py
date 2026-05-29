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

agente_perfil = AgentePerfilUsuario()
agente_recomendacion = AgenteRecomendacion()

ESTADOS_ANIMO = ["Alegre", "Triste", "Tranquilo", "Energico", "Estresado", "Romantico"]
CONTEXTOS = ["Ejercicio", "Estudio", "Casa", "Trabajo", "Fiesta", "Descanso"]

def _generos():
    """Géneros derivados del grafo (siempre actualizados)."""
    return agente_recomendacion.generos_disponibles()

# ==================== HELPERS ====================

def usuario_autenticado():
    return "usuario_id" in session

def obtener_usuario_sesion():
    return session.get("usuario_id")

# ==================== AUTENTICACIÓN ====================

@app.route("/")
def inicio():
    if usuario_autenticado():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
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
            if not agente_perfil.usuario_existe(usuario_id):
                agente_perfil.registrar_usuario(usuario_id, nombre, email)
            session["usuario_id"] = usuario_id
            session["nombre"] = nombre
            return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================== RUTAS PRINCIPALES ====================

@app.route("/dashboard")
def dashboard():
    if not usuario_autenticado():
        return redirect(url_for("login"))

    usuario_id = obtener_usuario_sesion()
    perfil = agente_perfil.obtener_perfil(usuario_id)
    mejor_valoradas = agente_recomendacion.obtener_mejor_valoradas(limite=5)
    generos = _generos()

    recomendaciones = []
    if perfil["estado_animo"] and perfil["contexto"]:
        recomendaciones = agente_recomendacion.recomendar(
            usuario_id=usuario_id,
            estado_animo=perfil["estado_animo"],
            contexto=perfil["contexto"],
            canciones_no_gustadas=perfil["canciones_no_gustadas"],
            generos_favoritos=perfil["generos_favoritos"],
            artistas_favoritos=perfil["artistas_favoritos"],
            generos_rechazados=perfil["generos_rechazados"],
        )

    return render_template(
        "dashboard.html",
        perfil=perfil,
        nombre=session.get("nombre"),
        mejor_valoradas=mejor_valoradas,
        recomendaciones=recomendaciones,
        estados_animo=ESTADOS_ANIMO,
        contextos=CONTEXTOS,
        generos=generos,
    )


@app.route("/recomendar", methods=["POST"])
def recomendar():
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

    agente_perfil.actualizar_estado_animo(usuario_id, estado_animo)
    agente_perfil.actualizar_contexto(usuario_id, contexto)

    perfil = agente_perfil.obtener_perfil(usuario_id)

    recomendaciones = agente_recomendacion.recomendar(
        usuario_id=usuario_id,
        estado_animo=estado_animo,
        contexto=contexto,
        canciones_no_gustadas=perfil["canciones_no_gustadas"],
        generos_favoritos=perfil["generos_favoritos"],
        artistas_favoritos=perfil["artistas_favoritos"],
        generos_rechazados=perfil["generos_rechazados"],
    )

    return jsonify({"recomendaciones": recomendaciones})


@app.route("/me_gusta", methods=["POST"])
def me_gusta():
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
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    generos_disponibles = _generos()
    if genero not in generos_disponibles:
        return jsonify({"error": f"Género '{genero}' no disponible."}), 400

    canciones = agente_recomendacion.recomendar_por_genero(genero, limite=10)
    return jsonify({"canciones": canciones})


@app.route("/perfil")
def perfil():
    if not usuario_autenticado():
        return redirect(url_for("login"))

    usuario_id = obtener_usuario_sesion()
    perfil_data = agente_perfil.obtener_perfil(usuario_id)
    return render_template(
        "perfil.html",
        perfil=perfil_data,
        nombre=session.get("nombre"),
        estados_animo=ESTADOS_ANIMO,
        contextos=CONTEXTOS,
    )


@app.route("/preview/<titulo>/<artista>")
def preview(titulo, artista):
    """
    Busca en Deezer el preview de 30 segundos.
    Usa la lógica mejorada que prioriza coincidencia artista+título.
    """
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    preview_url = AgenteRecomendacion.buscar_preview_deezer(titulo, artista)
    if preview_url:
        return jsonify({"preview_url": preview_url})
    return jsonify({"error": "Preview no disponible"}), 404

@app.route("/artista/<nombre_artista>")
def artista(nombre_artista):
    """Muestra información y canciones de un artista."""
    if not usuario_autenticado():
        return redirect(url_for("login"))

    # Nota: usa la INSTANCIA, no la clase
    info = agente_recomendacion.buscar_info_artista(nombre_artista)

    return render_template(
        "artista.html",
        artista=info,
        nombre=session.get("nombre")
    )

@app.route("/genero/<nombre_genero>")
def genero(nombre_genero):
    """Vista de género con todas sus canciones."""
    if not usuario_autenticado():
        return redirect(url_for("login"))

    canciones = agente_recomendacion.recomendar_por_genero(nombre_genero, limite=50)

    return render_template(
        "genero.html",
        genero=nombre_genero,
        canciones=canciones,
        nombre=session.get("nombre"),
    )


@app.route("/quitar_favorita", methods=["POST"])
def quitar_favorita():
    """Quita una canción de favoritas."""
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    usuario_id = obtener_usuario_sesion()
    cancion_id = request.form.get("cancion_id", "").strip()
    if not cancion_id:
        return jsonify({"error": "Canción no especificada."}), 400

    agente_perfil.quitar_cancion_gustada(usuario_id, cancion_id)
    return jsonify({"mensaje": "Canción quitada de favoritas."})


@app.route("/quitar_no_gusta", methods=["POST"])
def quitar_no_gusta():
    """Quita una canción de no me gustan."""
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    usuario_id = obtener_usuario_sesion()
    cancion_id = request.form.get("cancion_id", "").strip()
    if not cancion_id:
        return jsonify({"error": "Canción no especificada."}), 400

    agente_perfil.quitar_cancion_no_gustada(usuario_id, cancion_id)
    return jsonify({"mensaje": "Canción quitada de no me gustan."})



# ──────────────────────────────────────────────
# ARRANQUE
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)

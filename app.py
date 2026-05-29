# ==================== APP PRINCIPAL - MOODMUSIC ====================
# Responsabilidad: arrancar Flask, gestionar rutas y conectar
# el Agente de Perfil de Usuario con el Agente de Recomendación.

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from agentes.agente_perfil import AgentePerfilUsuario
from agentes.agente_recomendacion import AgenteRecomendacion
import os
from urllib import error, parse, request as urlrequest

# ==================== CONFIGURACIÓN ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "moodmusic_dev_key")

FUSEKI_HOST = os.environ.get("FUSEKI_HOST")
FUSEKI_DATASET = os.environ.get("FUSEKI_DATASET", "moodmusic")
AUTO_LOAD_FUSEKI = os.environ.get("AUTO_LOAD_FUSEKI")

if not FUSEKI_HOST:
    sparql_endpoint = os.environ.get("SPARQL_ENDPOINT") or os.environ.get("FUSEKI_ENDPOINT")
    if sparql_endpoint:
        parsed = parse.urlparse(sparql_endpoint)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[-1].lower() == "query":
            FUSEKI_HOST = f"{parsed.scheme}://{parsed.netloc}"
            FUSEKI_DATASET = FUSEKI_DATASET or parts[-2]

if FUSEKI_HOST and not os.environ.get("SPARQL_ENDPOINT") and not os.environ.get("FUSEKI_ENDPOINT"):
    os.environ["SPARQL_ENDPOINT"] = f"{FUSEKI_HOST.rstrip('/')}/{FUSEKI_DATASET}/query"

if AUTO_LOAD_FUSEKI is None:
    AUTO_LOAD_FUSEKI = bool(FUSEKI_HOST)
else:
    AUTO_LOAD_FUSEKI = AUTO_LOAD_FUSEKI.lower() in ("1", "true", "yes")


def _fuseki_url(path: str) -> str:
    return f"{FUSEKI_HOST.rstrip('/')}/{path.lstrip('/')}"


def _create_fuseki_dataset() -> None:
    create_url = _fuseki_url("$/datasets")
    data = parse.urlencode({"dbName": FUSEKI_DATASET, "dbType": "mem"}).encode("utf-8")
    req = urlrequest.Request(create_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            if resp.status in (200, 201, 202):
                print(f"[Fuseki] Dataset '{FUSEKI_DATASET}' creado o ya existente.")
    except error.HTTPError as exc:
        if exc.code == 400:
            print(f"[Fuseki] Dataset '{FUSEKI_DATASET}' ya existe.")
        else:
            print(f"[Fuseki] Error creando dataset: {exc}")
    except Exception as exc:
        print(f"[Fuseki] Error creando dataset: {exc}")


def _upload_grafo_to_fuseki() -> None:
    upload_url = _fuseki_url(f"{FUSEKI_DATASET}/data")
    ttl_path = os.path.join(os.path.dirname(__file__), "datos", "grafo.ttl")
    if not os.path.exists(ttl_path):
        print(f"[Fuseki] No se encontró {ttl_path}")
        return
    try:
        with open(ttl_path, "rb") as f:
            body = f.read()
        req = urlrequest.Request(upload_url, data=body, headers={"Content-Type": "text/turtle"})
        with urlrequest.urlopen(req, timeout=120) as resp:
            print(f"[Fuseki] Grafo subido correctamente a '{upload_url}' ({resp.status}).")
    except error.HTTPError as exc:
        print(f"[Fuseki] Error subiendo grafo: {exc.code} {exc.reason}")
    except Exception as exc:
        print(f"[Fuseki] Error subiendo grafo: {exc}")


def _ensure_fuseki_graph_loaded() -> None:
    if not AUTO_LOAD_FUSEKI or not FUSEKI_HOST or not FUSEKI_DATASET:
        return
    print(f"[Fuseki] Auto-carga habilitada: host={FUSEKI_HOST}, dataset={FUSEKI_DATASET}")
    _create_fuseki_dataset()
    _upload_grafo_to_fuseki()

agente_perfil = AgentePerfilUsuario()
agente_recomendacion = AgenteRecomendacion()

ESTADOS_ANIMO = ["Alegre", "Triste", "Tranquilo", "Energico", "Estresado", "Romantico", "Melancolico", "Motivado", "Relajado"]
CONTEXTOS = ["Ejercicio", "Estudio", "Casa", "Trabajo", "Fiesta", "Descanso", "Viaje", "Noche", "Gaming"]

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
            canciones_no_gustadas=perfil.get("canciones_no_gustadas_ids", []),
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
        canciones_no_gustadas=perfil.get("canciones_no_gustadas_ids", []),
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
    _ensure_fuseki_graph_loaded()
    app.run(debug=True)

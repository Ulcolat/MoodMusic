// ==================== MOODMUSIC - MAIN.JS ====================
// Responsabilidad: manejar toda la interactividad del dashboard,
// las llamadas a la API de Flask y las actualizaciones del DOM.

// ==================== UTILIDADES ====================

/**
 * Muestra una notificación toast temporal.
 * @param {string} mensaje - Texto a mostrar.
 * @param {string} tipo - 'success' o 'error'.
 */
function mostrarToast(mensaje, tipo = "success") {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = mensaje;
    toast.className = `toast toast-visible toast-${tipo}`;

    setTimeout(() => {
        toast.className = "toast";
    }, 3000);
}

/**
 * Realiza una petición POST con FormData a una ruta de Flask.
 * @param {string} url - Ruta destino.
 * @param {Object} datos - Datos a enviar.
 * @returns {Promise<Object>} Respuesta JSON del servidor.
 */
async function postFormData(url, datos) {
    const formData = new FormData();
    for (const [clave, valor] of Object.entries(datos)) {
        formData.append(clave, valor);
    }

    const respuesta = await fetch(url, {
        method: "POST",
        body: formData,
    });

    return respuesta.json();
}

// ==================== CHIPS (ESTADO DE ÁNIMO Y CONTEXTO) ====================

/**
 * Inicializa los chips de selección de estado de ánimo y contexto.
 * Al hacer clic en un chip, lo marca como activo y actualiza
 * el input hidden correspondiente.
 */
function inicializarChips() {
    const chips = document.querySelectorAll(".chip[data-tipo]");

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const tipo = chip.dataset.tipo;
            const valor = chip.dataset.valor;

            // Desactivar todos los chips del mismo tipo
            document.querySelectorAll(`.chip[data-tipo="${tipo}"]`).forEach((c) => {
                c.classList.remove("chip-active");
            });

            // Activar el chip seleccionado
            chip.classList.add("chip-active");

            // Actualizar el input hidden
            const input = document.getElementById(tipo === "estado_animo" ? "estado_animo" : "contexto");
            if (input) input.value = valor;
        });
    });
}

// ==================== FORMULARIO DE RECOMENDACIÓN ====================

/**
 * Construye el HTML de una tarjeta de canción.
 * @param {Object} cancion - Datos de la canción.
 * @returns {string} HTML de la tarjeta.
 */
function construirTarjetaCancion(cancion, mostrarAcciones = true) {
    const acciones = mostrarAcciones ? `
        <div class="cancion-acciones">
            <button
                class="btn-accion btn-preview"
                data-titulo="${cancion.titulo}"
                data-artista="${cancion.artista}"
                title="Preview 30s">
                ▶
            </button>
            <button
                class="btn-accion btn-gusta"
                data-cancion="${cancion.id}"
                title="Me gusta">
                ♥
            </button>
            <button
                class="btn-accion btn-no-gusta"
                data-cancion="${cancion.id}"
                title="No me gusta">
                ✕
            </button>
        </div>
    ` : `
        <div class="cancion-acciones">
            <button
                class="btn-accion btn-preview"
                data-titulo="${cancion.titulo}"
                data-artista="${cancion.artista}"
                title="Preview 30s">
                ▶
            </button>
        </div>
    `;

    return `
        <div class="cancion-card">
            <div class="cancion-info">
                <span class="cancion-titulo">${cancion.titulo}</span>
                <span class="cancion-artista">${cancion.artista}</span>
                <div class="cancion-meta">
                    <span class="tag">${cancion.genero}</span>
                    <span class="cancion-duracion">${cancion.duracion}</span>
                    <span class="cancion-calificacion">★ ${cancion.calificacion}</span>
                </div>
            </div>
            ${acciones}
        </div>
    `;
}

/**
 * Inicializa el formulario de recomendación.
 * Al enviarlo, llama a /recomendar y actualiza el grid de canciones.
 */
function inicializarFormRecomendacion() {
    const form = document.getElementById("form-recomendar");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const estadoAnimo = document.getElementById("estado_animo")?.value;
        const contexto = document.getElementById("contexto")?.value;

        if (!estadoAnimo) {
            mostrarToast("Selecciona un estado de ánimo.", "error");
            return;
        }

        if (!contexto) {
            mostrarToast("Selecciona un contexto.", "error");
            return;
        }

        const btnRecomendar = document.getElementById("btn-recomendar");
        if (btnRecomendar) {
            btnRecomendar.disabled = true;
            btnRecomendar.querySelector("span").textContent = "Buscando...";
        }

        try {
            const datos = await postFormData("/recomendar", {
                estado_animo: estadoAnimo,
                contexto: contexto,
            });

            const grid = document.getElementById("grid-recomendaciones");
            if (!grid) return;

            if (datos.error) {
                mostrarToast(datos.error, "error");
                return;
            }

            if (datos.recomendaciones.length === 0) {
                grid.innerHTML = `
                    <p class="empty-state">
                        No hay canciones disponibles para ese estado de ánimo y contexto.
                    </p>
                `;
                mostrarToast("Sin resultados para esa combinación.", "error");
                return;
            }

            // Renderizar canciones
            grid.innerHTML = datos.recomendaciones
                .map((cancion) => construirTarjetaCancion(cancion))
                .join("");

            // Inicializar botones de las nuevas tarjetas
            inicializarBotonesAccion();

            mostrarToast(`${datos.recomendaciones.length} canciones encontradas.`, "success");

            // Hacer scroll suave a las recomendaciones
            document.getElementById("seccion-recomendaciones")?.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });

        } catch (error) {
            mostrarToast("Error al conectar con el servidor.", "error");
        } finally {
            if (btnRecomendar) {
                btnRecomendar.disabled = false;
                btnRecomendar.querySelector("span").textContent = "Recomendar música";
            }
        }
    });
}

// ==================== BOTONES ME GUSTA / NO ME GUSTA ====================

/**
 * Inicializa los botones de acción (me gusta / no me gusta)
 * dentro de las tarjetas de canciones.
 * Se llama también después de renderizar nuevas tarjetas dinámicamente.
 */
function inicializarBotonesAccion() {
    // Botones "me gusta"
    document.querySelectorAll(".btn-gusta").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const cancionId = btn.dataset.cancion;

            try {
                const datos = await postFormData("/me_gusta", { cancion_id: cancionId });

                if (datos.error) {
                    mostrarToast(datos.error, "error");
                    return;
                }

                btn.style.color = "#ff4d6d";
                btn.style.borderColor = "#ff4d6d";
                mostrarToast("Agregada a favoritos ♥", "success");

            } catch {
                mostrarToast("Error al registrar preferencia.", "error");
            }
        });
    });

    // Botones "no me gusta"
    document.querySelectorAll(".btn-no-gusta").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const cancionId = btn.dataset.cancion;

            try {
                const datos = await postFormData("/no_me_gusta", { cancion_id: cancionId });

                if (datos.error) {
                    mostrarToast(datos.error, "error");
                    return;
                }

                // Remover la tarjeta del DOM con animación
                const tarjeta = btn.closest(".cancion-card");
                if (tarjeta) {
                    tarjeta.style.opacity = "0";
                    tarjeta.style.transform = "scale(0.95)";
                    tarjeta.style.transition = "all 0.25s ease";
                    setTimeout(() => tarjeta.remove(), 250);
                }

                mostrarToast("Canción descartada.", "success");

            } catch {
                mostrarToast("Error al registrar preferencia.", "error");
            }
        });
    });

    // Botones preview
    document.querySelectorAll(".btn-preview").forEach((btn) => {
        btn.addEventListener("click", () => {
            const titulo = btn.dataset.titulo;
            const artista = btn.dataset.artista;
            reproducirPreview(titulo, artista, btn);
        });
    });
}

// ==================== EXPLORAR POR GÉNERO ====================

/**
 * Inicializa los chips de género para explorar canciones
 * filtrando por género musical.
 */
function inicializarExplorarGenero() {
    const chipsGenero = document.querySelectorAll(".chip-genero");
    if (!chipsGenero.length) return;

    chipsGenero.forEach((chip) => {
        chip.addEventListener("click", async () => {
            const genero = chip.dataset.genero;

            // Marcar chip activo
            chipsGenero.forEach((c) => c.classList.remove("chip-active"));
            chip.classList.add("chip-active");

            const grid = document.getElementById("grid-genero");
            if (!grid) return;

            grid.innerHTML = `<p class="empty-state">Cargando...</p>`;

            try {
                const respuesta = await fetch(`/explorar/${genero}`);
                const datos = await respuesta.json();

                if (datos.error) {
                    mostrarToast(datos.error, "error");
                    return;
                }

                if (datos.canciones.length === 0) {
                    grid.innerHTML = `
                        <p class="empty-state">No hay canciones disponibles en este género.</p>
                    `;
                    return;
                }

                grid.innerHTML = datos.canciones
                    .map((cancion) => construirTarjetaCancion(cancion, false))
                    .join("");

            } catch {
                mostrarToast("Error al cargar el género.", "error");
                grid.innerHTML = `<p class="empty-state">Error al cargar canciones.</p>`;
            }
        });
    });
}

// ==================== PREVIEW DE CANCIÓN ====================

let audioActual = null;

/**
 * Busca y reproduce el preview de 30 segundos de una canción.
 * Si hay uno reproduciéndose, lo detiene primero.
 * @param {string} titulo - Título de la canción.
 * @param {string} artista - Artista de la canción.
 * @param {HTMLElement} boton - Botón que disparó la acción.
 */
async function reproducirPreview(titulo, artista, boton) {
    // Si el mismo botón está activo, detener
    if (boton.classList.contains("preview-activo")) {
        audioActual.pause();
        audioActual = null;
        boton.textContent = "▶";
        boton.classList.remove("preview-activo");
        return;
    }

    // Detener cualquier audio previo
    if (audioActual) {
        audioActual.pause();
        audioActual = null;
        document.querySelectorAll(".btn-preview").forEach((b) => {
            b.textContent = "▶";
            b.classList.remove("preview-activo");
        });
    }

    boton.textContent = "...";

    try {
        const respuesta = await fetch(
            `/preview/${encodeURIComponent(titulo)}/${encodeURIComponent(artista)}`
        );
        const datos = await respuesta.json();

        if (datos.error) {
            mostrarToast("Preview no disponible para esta canción.", "error");
            boton.textContent = "▶";
            return;
        }

        audioActual = new Audio(datos.preview_url);
        audioActual.volume = 0.7;
        audioActual.play();
        boton.textContent = "■";
        boton.classList.add("preview-activo");

        // Al terminar los 30 segundos
        audioActual.addEventListener("ended", () => {
            boton.textContent = "▶";
            boton.classList.remove("preview-activo");
            audioActual = null;
        });

    } catch {
        mostrarToast("Error al cargar el preview.", "error");
        boton.textContent = "▶";
    }
}

// ==================== INICIALIZACIÓN ====================

/**
 * Punto de entrada principal.
 * Se ejecuta cuando el DOM está completamente cargado.
 */
document.addEventListener("DOMContentLoaded", () => {
    inicializarChips();
    inicializarFormRecomendacion();
    inicializarBotonesAccion();
    inicializarExplorarGenero();
});
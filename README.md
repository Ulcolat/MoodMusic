# MoodMusic 🎵

Sistema de recomendación musical basado en estado de ánimo y contexto, implementado con Flask, RDF/OWL y la API de Deezer. Usa Apache Jena Fuseki como triplestore SPARQL para almacenar y consultar el grafo de conocimiento.

## Estructura del proyecto

```
MoodMusic/
├── app.py                          ← App Flask principal
├── requirements.txt                ← Dependencias Python
├── docker-compose.yml              ← Levanta Fuseki con Docker Compose
├── diagnostics_agent.py            ← Diagnóstico del agente
├── agentes/
│   ├── agente_perfil.py            ← Gestión de perfiles de usuario en RDF
│   └── agente_recomendacion.py     ← Motor de recomendación personalizado
├── datos/
│   ├── grafo.ttl                   ← Grafo RDF con canciones y usuarios
│   ├── populate_songs.py           ← Script para añadir ~2000 canciones desde Deezer
│   └── apache-jena-fuseki-6.1.0/   ← Servidor Fuseki embebido (alternativa a Docker)
├── ontologia/
│   └── moodmusic.owl               ← Ontología del sistema (Protégé)
├── scripts/
│   └── upload_grafo.ps1            ← Script PowerShell para cargar el grafo a Fuseki
├── static/
│   ├── css/main.css
│   └── js/app.js
└── templates/
    ├── login.html
    ├── dashboard.html
    ├── perfil.html
    ├── artista.html
    ├── genero.html
    └── partials/
        ├── _song_card.html
        └── _song_card_simple.html
```

## Dependencias

```
Flask
rdflib>=6.0.0
SPARQLWrapper>=1.8.5
```

Instalación:

```bash
pip install -r requirements.txt
```

> **Requisito adicional:** Java 11 o superior (necesario para ejecutar Apache Jena Fuseki).

## Ejecución

El sistema requiere **dos terminales** corriendo simultáneamente: una para el servidor SPARQL (Fuseki) y otra para la aplicación Flask.

---

### Terminal 1 — Apache Jena Fuseki

Desde la raíz del proyecto, levanta el servidor Fuseki embebido:

```bash
java -jar datos/apache-jena-fuseki-6.1.0/fuseki-server.jar --update --mem /moodmusic
```

Esto arranca Fuseki en `http://localhost:3030` con un dataset en memoria llamado `moodmusic`.

Una vez corriendo, carga el grafo RDF:

```bash
# Linux / macOS
curl -X POST -H "Content-Type: text/turtle" \
  --data-binary @datos/grafo.ttl \
  http://localhost:3030/moodmusic/data

# Windows (PowerShell)
.\scripts\upload_grafo.ps1
```

También puedes crear el dataset y subir el grafo desde la interfaz web en `http://localhost:3030`.

> **Alternativa con Docker:** si prefieres no usar el Fuseki embebido, puedes levantar el contenedor con `docker-compose up -d` (requiere Docker instalado).

---

### Terminal 2 — Flask

Con Fuseki ya corriendo, lanza la aplicación:

```bash
python app.py
```

Abre `http://127.0.0.1:5000` en tu navegador.

> La app detecta automáticamente el endpoint SPARQL. Si necesitas apuntarla a un host diferente, exporta la variable de entorno antes de ejecutar:
>
> ```bash
> # Linux / macOS
> export SPARQL_ENDPOINT="http://localhost:3030/moodmusic/query"
>
> # Windows PowerShell
> $env:SPARQL_ENDPOINT = "http://localhost:3030/moodmusic/query"
> ```

---

### (Opcional) Poblar el grafo con canciones

Si el grafo está vacío o quieres agregar más canciones, ejecuta este script una sola vez:

```bash
python datos/populate_songs.py
```

Consulta la API pública de Deezer y agrega ≈2000 canciones al archivo `datos/grafo.ttl`. Es idempotente: no duplica canciones ya existentes.

---

## Funcionalidades

- **Login**: diseño con panel de branding, sin contraseña (el ID es el identificador).
- **Recomendaciones personalizadas**: el motor pondera géneros favoritos (+2), artistas favoritos (+3) y penaliza géneros rechazados (−5), aprendiendo con cada ♥ / ✕.
- **Explorar por género**: muestra únicamente los géneros que tienen canciones reales en el grafo.
- **Reproductor global**: previews de 30 s vía Deezer, disponible en recomendadas, explorar por género y mejor valoradas.
- **Verificación de artista en Deezer**: cuando hay varios resultados con el mismo título, se prioriza el que coincide exactamente con el artista del grafo, evitando homonimias.
- **Perfil**: muestra géneros favoritos, artistas favoritos, géneros rechazados y estadísticas.
- **Triplestore SPARQL**: integración con Apache Jena Fuseki para consultas semánticas sobre el grafo RDF.

## Géneros soportados

Pop, Rock, LoFi, Electronic, Jazz, RnB, Classical, HipHop, Reggaeton, Urbano, Latin, Indie, Salsa, Metal

## Video demostrativo:

https://github.com/user-attachments/assets/67ec9bb5-a410-4d3c-be24-e910fca486e3



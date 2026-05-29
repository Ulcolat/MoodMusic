# MoodMusic 🎵

Sistema de recomendación musical basado en estado de ánimo y contexto, implementado con Flask, RDF/OWL y la API de Deezer.

## Estructura del proyecto

```
MoodMusic/
├── app.py                     ← App Flask principal
├── agentes/
│   ├── agente_perfil.py       ← Gestión de perfiles de usuario en RDF
│   └── agente_recomendacion.py← Motor de recomendación personalizado
├── datos/
│   ├── grafo.ttl              ← Grafo RDF con canciones y usuarios
│   └── populate_songs.py      ← Script para añadir ~2000 canciones desde Deezer
├── ontologia/                 ← Archivos de ontología adicionales (Protégé)
├── static/
│   ├── css/main.css
│   └── js/app.js
└── templates/
    ├── login.html
    ├── dashboard.html
    ├── perfil.html
    └── partials/
        ├── _song_card.html
        └── _song_card_simple.html
```

## Instalación

```bash
pip install flask rdflib
```

## Uso

### 1. Poblar el grafo con canciones (recomendado, una sola vez)

```bash
cd MoodMusic
python datos/populate_songs.py
```

Esto agrega ≈2000 canciones al archivo `datos/grafo.ttl` consultando la API pública de Deezer. El script es idempotente: no duplica canciones ya existentes.

### 2. Arrancar la app

```bash
python app.py
```

Abre http://127.0.0.1:5000

## Funcionalidades

- **Login mejorado**: diseño con panel de branding, sin contraseña (el ID es el identificador).
- **Recomendaciones personalizadas**: el motor pondera géneros favoritos (+2), artistas favoritos (+3) y penaliza géneros rechazados (-5), aprendiendo con cada ♥ / ✕.
- **Explorar por género**: todos los géneros que realmente tienen canciones en el grafo (sin géneros vacíos).
- **Reproductor global**: previews de 30s via Deezer. Funciona en la sección de recomendadas, explorar por género y mejor valoradas.
- **Verificación de artista en Deezer**: si hay varios resultados con el mismo título, se prioriza el que coincide exactamente con el artista del grafo, evitando homonimias.
- **Perfil**: muestra géneros favoritos, artistas favoritos, géneros rechazados y estadísticas.
- **Bug fix – volver del perfil**: el reproductor y los controles funcionan correctamente en todas las páginas.

## Géneros soportados

Pop, Rock, LoFi, Electronic, Jazz, RnB, Classical, HipHop, Reggaeton, Urbano, Latin, Indie, Salsa, Metal

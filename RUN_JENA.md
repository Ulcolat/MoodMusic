Levantar Apache Jena Fuseki (Docker)

1) Arrancar Fuseki en Docker (dataset `moodmusic` en memoria):

```bash
# Ejecuta en el root del proyecto
docker run --rm -p 3030:3030 -v $(pwd)/datos:/data stain/jena-fuseki
```

2) Crear dataset `moodmusic` (desde el UI: http://localhost:3030) o con curl:

```bash
# Crear dataset en memoria llamado 'moodmusic'
curl -X POST \
  --data 'dbName=moodmusic&dbType=mem' \
  http://localhost:3030/$/datasets

# Subir el grafo TTL al dataset
curl -X POST -H "Content-Type: text/turtle" --data-binary @datos/grafo.ttl \
  http://localhost:3030/moodmusic/data
```

3) Configurar la app para usar el endpoint SPARQL:

Exportar la variable de entorno (Windows PowerShell):

```powershell
$env:SPARQL_ENDPOINT = "http://localhost:3030/moodmusic/query"
python app.py
```

4) Notas:
- Si prefieres `docker-compose` puedo generar un archivo `docker-compose.yml` para automatizar el arranque y la carga.
- El endpoint de consulta SPARQL es `http://host:3030/<dataset>/query` y el endpoint para actualizar datos es `http://host:3030/<dataset>/data`.

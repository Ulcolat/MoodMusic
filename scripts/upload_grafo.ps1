# Script para crear dataset 'moodmusic' y subir datos/grafo.ttl a Fuseki
param(
    [string]$Host = 'http://localhost:3030',
    [string]$Dataset = 'moodmusic'
)

Write-Host "Creando dataset '$Dataset' en $Host"
$createUrl = "$Host/$/datasets"
$body = "dbName=$Dataset&dbType=mem"
try {
    Invoke-RestMethod -Method Post -Uri $createUrl -Body $body -ContentType 'application/x-www-form-urlencoded'
    Write-Host "Dataset creado (o ya existente)."
} catch {
    Write-Warning "Fallo creando dataset: $_"
}

$uploadUrl = "$Host/$Dataset/data"
$ttlPath = Join-Path $PSScriptRoot "..\datos\grafo.ttl"
if (-Not (Test-Path $ttlPath)) {
    Write-Error "No se encontró $ttlPath"
    exit 1
}

Write-Host "Subiendo grafo desde $ttlPath a $uploadUrl"
try {
    Invoke-RestMethod -Method Post -Uri $uploadUrl -InFile $ttlPath -ContentType 'text/turtle'
    Write-Host "Grafo subido correctamente."
} catch {
    Write-Warning "Fallo subiendo grafo: $_"
}

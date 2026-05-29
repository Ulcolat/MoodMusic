from agentes.agente_recomendacion import AgenteRecomendacion

if __name__ == '__main__':
    ar = AgenteRecomendacion()
    print('SPARQL endpoint:', ar.sparql_endpoint)
    print('Mejor valoradas:', ar.obtener_mejor_valoradas(5))
    print('Generos disponibles:', ar.generos_disponibles())
    print('Recom_por_genero Pop:', ar.recomendar_por_genero('Pop', limite=5))

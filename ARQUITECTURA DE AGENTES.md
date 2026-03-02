El "Cerebro" de la Arquitectura: Los 4 Agentes Maestros

Para que el sistema funcione como un equipo de expertos curriculares, propongo este esquema:
A. Agente Orquestador (Manager)

    Función: Recibe la petición de la maestra ("Quiero planificar una clase de 45 min sobre fracciones para 2do año").

    Tarea: Descompone el pedido y decide qué información falta. Es el único que habla con el usuario final.

B. Agente Bibliotecario de Grafos (Graph Specialist)

    Función: Es el único con acceso directo a Neo4j.

    Tarea: Traduce la intención del usuario a consultas Cypher. Su misión es extraer el "Contexto de Verdad": qué competencia, qué contenido y qué criterio de logro aplican exactamente a ese Tramo y Unidad.

    Valor: Elimina las "alucinaciones" porque solo entrega datos reales del grafo.

C. Agente Diseñador Pedagógico (Planner)

    Función: Experto en didáctica y metodologías (ABP, Aula Invertida, Gamificación).

    Tarea: Toma los datos fríos del bibliotecario y los convierte en una secuencia de clase atractiva, tiempos, materiales y consignas.

    Valor: Aporta la creatividad que el grafo no tiene por sí solo.

D. Agente de Auditoría y Cumplimiento (Compliance Officer)

    Función: Es el "abogado" del programa oficial.

    Tarea: Compara la planificación generada por el Diseñador contra los Criterios de Logro originales. Si el Diseñador se desvió del programa, rechaza la respuesta y pide una corrección.

    Valor: Garantiza que la planificación sea 100% legal y válida para inspección.
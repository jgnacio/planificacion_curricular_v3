Dado que los Criterios de Logro son la unidad mínima de la cual los docentes parten para crear sus propias metas y planificaciones, estos deben ser los nodos "hoja" o finales de la cadena principal.
La mejor jerarquía de nodos (Ontología del Grafo)

Esta estructura organiza la información desde lo macro (Ciclo) hasta lo micro (Criterio), permitiendo consultas transversales por competencias generales (MCN) o ejes temáticos.
1. Nodos de Estructura (Jerarquía Principal)

    Ciclo: (Ej: 1er Ciclo, 2do Ciclo). Es el nodo raíz.

    Espacio: (Ej: Espacio de Comunicación). Agrupa las unidades.

    UnidadCurricular: (Ej: Lengua Española, Matemática). La disciplina específica.

    Tramo: (Ej: Tramo 1, Tramo 2). Define la etapa del alumno.

2. Nodos de Propósito (El "Saber Hacer")

    CompetenciaEspecifica (CE): El corazón pedagógico.

        Relación recursiva: Una CE puede ser HIJA_DE otra CE (como CE1.1 de CE1).

    MCN (Competencia General): (Ej: Pensamiento Crítico, Comunicación). Nodos centrales que conectan diferentes materias.

    EjeTematico: (Ej: Capital Cultural, Numeración). Dimensiones que agrupan contenidos.

3. Nodos de Implementación (La "Clase Diaria")

    Contenido: El tema técnico o conceptual que se dicta.

    CriterioLogro: El estándar de evaluación. Es el nodo más granular.

Mapa de Relaciones (Los "Arcos")

Para que el grafo sea útil en una aplicación de búsqueda o generación de planificaciones, las flechas deben conectar los conceptos de la siguiente manera:

    Navegación Administrativa:

        (Ciclo)-[:CONTIENE]->(Espacio)

        (Espacio)-[:CONTIENE]->(UnidadCurricular)

        (UnidadCurricular)-[:SE_DIVIDE_EN]->(Tramo)

    Vinculación Pedagógica:

        (Tramo)-[:DESARROLLA]->(CompetenciaEspecifica)

        (CompetenciaEspecifica)-[:CONTRIBUYE_A]->(MCN)

        (CompetenciaEspecifica)-[:SE_ENMARCA_EN]->(EjeTematico)

    Planificación Operativa:

        (CompetenciaEspecifica)-[:VINCULA_CON]->(Contenido)

        (Contenido)-[:EVALUADO_POR]->(CriterioLogro)
"""
Seed completo para usuario Ignacio.
- Borra grupos, proyectos, secuencias, actividades, alumnos y chat_sessions.
- Crea 4 grupos; el primero lleno a tope.
- Conserva users_profile intacto.

Uso:
    uv run python scripts/seed_ignacio.py
"""

import json
import sqlite3
import uuid
from datetime import date, timedelta, datetime

DB_PATH = "ebi.db"
NOW = datetime.utcnow().isoformat()
USER_ID = "user_3Bi4BfcIA20dD13HQ0h7jir8dJF"

BASE = date(2026, 3, 2)  # inicio del año lectivo Uruguay 2026


def uid() -> str:
    return str(uuid.uuid4())


def d(offset_weeks: int = 0) -> str:
    return (BASE + timedelta(weeks=offset_weeks)).isoformat()


# ── IDs fijos para el grupo principal ────────────────────────────────────────
G1 = uid()  # 4.to A 2026 — grupo lleno
G2 = uid()  # 3.er B 2026
G3 = uid()  # 5.to C 2026
G4 = uid()  # 6.to A 2026


def purge(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute("DELETE FROM chat_sessions WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM activities WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM activity_sequences WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM integrative_projects WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM students WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM groups WHERE user_id = ?", (USER_ID,))
    c.execute("DELETE FROM educational_centers WHERE user_id = ?", (USER_ID,))
    conn.commit()
    print("✓ Datos anteriores borrados")


def seed_groups(c: sqlite3.Cursor):
    groups = [
        (G1, USER_ID, None, "4.to A 2026", "Tramo 4", "4.to grado",
         d(0), d(40), "Grupo principal del año lectivo 2026.", NOW, NOW),
        (G2, USER_ID, None, "3.er B 2026", "Tramo 3", "3.er grado",
         d(0), d(40), None, NOW, NOW),
        (G3, USER_ID, None, "5.to C 2026", "Tramo 4", "5.to grado",
         d(0), d(40), None, NOW, NOW),
        (G4, USER_ID, None, "6.to A 2025", "Tramo 4", "6.to grado",
         d(-52), d(-12), None, NOW, NOW),
    ]
    c.executemany("""
        INSERT OR IGNORE INTO groups
        (id, user_id, educational_center_id, name, stage, level,
         start_date, end_date, description, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, groups)
    print(f"✓ {len(groups)} grupos creados")


def seed_students(c: sqlite3.Cursor):
    alumnos = [
        (USER_ID, G1, "Ana García",           "2015-04-12", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Bruno Rodríguez",       "2015-07-23", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Camila Fernández",      "2015-02-05", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Diego López",           "2015-11-18", "Primaria", "4.to grado", "Requiere apoyo en lectoescritura."),
        (USER_ID, G1, "Valentina Martínez",    "2015-08-30", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Facundo Pérez",         "2015-03-14", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Lucía González",        "2015-06-09", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Mateo Álvarez",         "2015-09-27", "Primaria", "4.to grado", "Muy activo, destaca en ciencias."),
        (USER_ID, G1, "Sofía Hernández",       "2015-01-15", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Tomás Díaz",            "2015-12-03", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Isabella Romero",       "2015-05-20", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Nicolás Torres",        "2015-10-08", "Primaria", "4.to grado", "Asistencia irregular."),
        (USER_ID, G1, "Martina Castro",        "2015-04-25", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Agustín Vargas",        "2015-07-11", "Primaria", "4.to grado", None),
        (USER_ID, G1, "Florencia Morales",     "2015-02-28", "Primaria", "4.to grado", None),
    ]
    rows = [(USER_ID, a[1], a[2], a[3], a[4], a[5], a[6], NOW)
            for a in alumnos]
    c.executemany("""
        INSERT INTO students
        (user_id, group_id, nombre_completo, fecha_nacimiento, nivel, grado, notas, created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    print(f"✓ {len(rows)} alumnos creados")


def seed_projects_and_content(c: sqlite3.Cursor):
    # ── IDs de proyectos ──────────────────────────────────────────────────────
    p1 = uid()  # La alimentación saludable         (semanas  0-8, DONE)
    p2 = uid()  # El barrio que somos               (semanas  8-14, IN PROGRESS)
    p3 = uid()  # Energías renovables               (semanas 14-21, PENDING)
    p4 = uid()  # Matemática en la economía         (semanas 21-26, PENDING)

    projects = [
        (p1, G1, USER_ID,
         "La alimentación saludable en nuestra escuela",
         "Investigar los hábitos alimenticios del grupo y diseñar una propuesta de alimentación saludable para la escuela.",
         8, "Feria de la alimentación + folleto informativo para familias",
         json.dumps(["espacio_cientifico_matematico", "espacio_comunicacion_artistica"]),
         json.dumps(["CE1", "CE2", "CE3"]),
         d(0), d(8), NOW, NOW),
        (p2, G1, USER_ID,
         "El barrio que somos: historia y territorio",
         "Explorar la historia y el espacio geográfico del barrio a través de testimonios, mapas y producciones colectivas.",
         6, "Mural histórico del barrio + maqueta a escala",
         json.dumps(["espacio_social_ciudadano", "espacio_comunicacion_artistica"]),
         json.dumps(["CE2", "CE4"]),
         d(8), d(14), NOW, NOW),
        (p3, G1, USER_ID,
         "Energías renovables: el futuro es hoy",
         "Comprender las fuentes de energía, el impacto ambiental y las alternativas renovables disponibles en Uruguay.",
         7, "Maqueta de vivienda sustentable + presentación ante la comunidad escolar",
         json.dumps(["espacio_cientifico_matematico", "espacio_social_ciudadano"]),
         json.dumps(["CE1", "CE3", "CE5"]),
         d(14), d(21), NOW, NOW),
        (p4, G1, USER_ID,
         "La matemática en la economía cotidiana",
         "Aplicar conceptos de porcentaje, proporcionalidad y presupuesto en un emprendimiento escolar real.",
         5, "Mercado escolar: venta de productos elaborados por los estudiantes",
         json.dumps(["espacio_cientifico_matematico"]),
         json.dumps(["CE1", "CE2", "CE5"]),
         d(21), d(26), NOW, NOW),
    ]

    c.executemany("""
        INSERT OR IGNORE INTO integrative_projects
        (id, group_id, user_id, name, purpose, duration_weeks, final_product,
         curriculum_space_ids, competency_ids, start_date, end_date, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, projects)

    # ── Secuencias ────────────────────────────────────────────────────────────
    # Proyecto 1 (semanas 0-8, done)
    s1a = uid(); s1b = uid(); s1c = uid()
    # Proyecto 2 (semanas 8-14, in progress)
    s2a = uid(); s2b = uid(); s2c = uid()
    # Proyecto 3 (semanas 14-21, pending)
    s3a = uid(); s3b = uid(); s3c = uid()
    # Proyecto 4 (semanas 21-26, pending)
    s4a = uid(); s4b = uid(); s4c = uid()

    sequences = [
        # P1
        (s1a, p1, USER_ID, "¿Qué comemos y por qué?",
         "Explorar los hábitos alimenticios del grupo y comprender la pirámide nutricional.", 1, d(0), d(3), NOW, NOW),
        (s1b, p1, USER_ID, "El cuerpo y los nutrientes",
         "Investigar la función de los macronutrientes y micronutrientes en el organismo.", 2, d(3), d(6), NOW, NOW),
        (s1c, p1, USER_ID, "Nuestra feria de la salud",
         "Organizar y ejecutar la feria de la alimentación saludable para la comunidad escolar.", 3, d(6), d(8), NOW, NOW),
        # P2
        (s2a, p2, USER_ID, "Orígenes e historia del barrio",
         "Indagar en los orígenes del barrio a través de fuentes primarias y secundarias.", 1, d(8), d(10), NOW, NOW),
        (s2b, p2, USER_ID, "El espacio y sus transformaciones",
         "Analizar cómo cambió el uso del suelo y el paisaje urbano a lo largo del tiempo.", 2, d(10), d(12), NOW, NOW),
        (s2c, p2, USER_ID, "Voces del barrio: entrevistas y mural",
         "Recoger testimonios de vecinos y elaborar el mural colectivo del barrio.", 3, d(12), d(14), NOW, NOW),
        # P3
        (s3a, p3, USER_ID, "Fuentes de energía: origen y uso",
         "Clasificar las fuentes de energía y comprender sus ventajas y desventajas.", 1, d(14), d(17), NOW, NOW),
        (s3b, p3, USER_ID, "Energías renovables en Uruguay",
         "Investigar el avance de la energía eólica y solar en Uruguay y su impacto ambiental.", 2, d(17), d(19), NOW, NOW),
        (s3c, p3, USER_ID, "Diseñamos nuestra casa del futuro",
         "Planificar y construir una maqueta de vivienda que integre al menos dos fuentes renovables.", 3, d(19), d(21), NOW, NOW),
        # P4
        (s4a, p4, USER_ID, "Porcentajes, descuentos y aumentos",
         "Resolver situaciones de compra-venta aplicando porcentajes en contextos reales.", 1, d(21), d(23), NOW, NOW),
        (s4b, p4, USER_ID, "Presupuesto y planificación del mercado",
         "Elaborar un presupuesto real para el mercado escolar aplicando proporcionalidad.", 2, d(23), d(25), NOW, NOW),
        (s4c, p4, USER_ID, "El mercado escolar en acción",
         "Ejecutar el mercado, registrar ventas y analizar los resultados económicos.", 3, d(25), d(26), NOW, NOW),
    ]

    c.executemany("""
        INSERT OR IGNORE INTO activity_sequences
        (id, project_id, user_id, name, learning_goal, "order", start_date, end_date, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, sequences)

    # ── Actividades ───────────────────────────────────────────────────────────
    def act(pid, sid, order, title, atype, space, unit, comp_code, comp,
            content, criterion, goal, method, competencies, start, end, status):
        return (
            uid(), USER_ID, pid, sid, G1, order, title,
            atype, space, unit, 4,
            comp_code, comp, content, criterion, goal,
            method, competencies,
            d(start), d(end), status, NOW, NOW,
        )

    acts = [
        # ── s1a: ¿Qué comemos y por qué? ─────────────────────────────────────
        act(p1, s1a, 1,
            "Encuesta sobre hábitos alimenticios del grupo",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE2", "Diseña y aplica una encuesta sencilla y organiza los datos en tablas de frecuencia.",
            "Estadística: diseño de encuesta, tablas de frecuencia, gráficas de barra.",
            "Elabora una encuesta con al menos 5 preguntas y tabula correctamente las respuestas.",
            "Recolectar datos reales sobre los hábitos alimenticios del grupo para el proyecto.",
            "Diseño colectivo de la encuesta + aplicación + tabulación + presentación de resultados.",
            "Pensamiento matemático,Trabajo colaborativo",
            0, 1, "done"),

        act(p1, s1a, 2,
            "La pirámide alimenticia: ¿qué lugar ocupa lo que comemos?",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE1", "Clasifica alimentos según los grupos de la pirámide nutricional.",
            "Pirámide alimenticia. Grupos de alimentos: cereales, proteínas, grasas, vitaminas.",
            "Clasifica correctamente al menos 10 alimentos en los grupos correspondientes de la pirámide.",
            "Comprender la estructura de una alimentación equilibrada usando la pirámide como referencia.",
            "Análisis de la pirámide + clasificación individual + corrección grupal + debate.",
            "Pensamiento científico,Comunicación",
            1, 2, "done"),

        act(p1, s1a, 3,
            "Comparamos nuestros resultados: ¿comemos bien?",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE3", "Analiza críticamente los datos de la encuesta en relación con la pirámide alimenticia.",
            "Análisis de datos. Comparación. Argumentación basada en evidencia.",
            "Identifica al menos dos grupos alimenticios subrepresentados en la dieta del grupo y argumenta por qué.",
            "Contrastar los hábitos reales del grupo con las recomendaciones nutricionales.",
            "Análisis grupal de los datos de la encuesta + conclusiones + presentación oral.",
            "Pensamiento crítico,Comunicación",
            2, 3, "done"),

        # ── s1b: El cuerpo y los nutrientes ──────────────────────────────────
        act(p1, s1b, 1,
            "¿Para qué sirven los nutrientes? Investigación por grupos",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE1", "Describe la función de los principales nutrientes en el organismo.",
            "Macronutrientes: carbohidratos, proteínas, grasas. Micronutrientes: vitaminas y minerales.",
            "Explica con sus palabras la función de al menos tres nutrientes con ejemplos de alimentos fuente.",
            "Comprender el rol de los nutrientes para fundamentar las propuestas del proyecto.",
            "Investigación en grupos + síntesis en cuadro comparativo + exposición al grupo.",
            "Pensamiento científico,Trabajo colaborativo",
            3, 4, "done"),

        act(p1, s1b, 2,
            "Etiquetas nutricionales: ¿sabemos leer lo que comemos?",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE2", "Interpreta la información nutricional de etiquetas de alimentos.",
            "Información nutricional: porciones, calorías, porcentajes de valor diario.",
            "Lee correctamente una etiqueta e identifica los tres nutrientes de mayor presencia.",
            "Desarrollar la capacidad de lectura crítica de información nutricional en productos reales.",
            "Análisis de etiquetas reales traídas de casa + comparación entre productos + conclusiones.",
            "Pensamiento crítico,Resolución de problemas",
            4, 5, "done"),

        act(p1, s1b, 3,
            "Menú saludable para la escuela: propuesta grupal",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE3", "Elabora una propuesta de menú equilibrado aplicando los conocimientos sobre nutrientes.",
            "Planificación de menú. Equilibrio nutricional. Variedad y estacionalidad.",
            "Diseña un menú semanal que contemple todos los grupos alimenticios con justificación nutricional.",
            "Integrar los aprendizajes sobre nutrientes en una propuesta concreta y aplicable.",
            "Diseño grupal de menú + revisión cruzada entre grupos + ajustes + presentación.",
            "Pensamiento científico,Comunicación,Resolución de problemas",
            5, 6, "done"),

        # ── s1c: Nuestra feria de la salud ────────────────────────────────────
        act(p1, s1c, 1,
            "Planificamos la feria: roles, stands y materiales",
            "planificacion", "Espacio Comunicación Artística", "Lengua",
            "CE2", "Organiza la información de la feria en un texto planificador colectivo.",
            "Texto instructivo y planificador. Organización de eventos. Trabajo en equipo.",
            "Redacta una lista de tareas con responsables, fechas y materiales necesarios.",
            "Coordinar la organización de la feria asignando roles y recursos de forma eficiente.",
            "Asamblea de planificación + asignación de roles + redacción del plan de acción.",
            "Comunicación,Trabajo colaborativo,Ciudadanía",
            6, 7, "done"),

        act(p1, s1c, 2,
            "Elaboramos el folleto informativo para las familias",
            "planificacion", "Espacio Comunicación Artística", "Lengua",
            "CE3", "Produce un texto informativo con vocabulario técnico y propósito comunicativo claro.",
            "Texto informativo. Vocabulario específico. Diseño gráfico básico.",
            "Escribe un folleto con título, subtítulos, información nutricional y recomendaciones.",
            "Comunicar los aprendizajes del proyecto a la comunidad escolar de forma accesible.",
            "Borrador grupal + revisión entre pares + diagramación + impresión.",
            "Comunicación,Creatividad",
            7, 7, "done"),

        act(p1, s1c, 3,
            "La feria de la alimentación: montaje y presentación",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE1", "Presenta de forma oral y visual los aprendizajes del proyecto a la comunidad.",
            "Presentación oral. Diseño de stands. Interacción con el público.",
            "Explica de forma clara y fluida el stand a al menos tres visitantes externos.",
            "Compartir con la comunidad los resultados del proyecto de manera atractiva y fundamentada.",
            "Montaje de stands + presentación a familias y otros grupos + reflexión final.",
            "Comunicación,Creatividad,Ciudadanía",
            7, 8, "done"),

        # ── s2a: Orígenes e historia del barrio ──────────────────────────────
        act(p2, s2a, 1,
            "¿Cómo era nuestro barrio antes? Exploración de fuentes",
            "planificacion", "Espacio Social y Ciudadano", "Historia",
            "CE4", "Analiza fuentes primarias y secundarias para reconstruir la historia local.",
            "Fuentes históricas: fotografías antiguas, testimonios, documentos. Barrio y comunidad.",
            "Compara al menos dos fuentes y extrae información relevante sobre el origen del barrio.",
            "Desarrollar el pensamiento histórico mediante el análisis de fuentes diversas.",
            "Observación de fotografías antiguas + lectura de textos + cuadro comparativo.",
            "Pensamiento histórico,Comunicación",
            8, 9, "done"),

        act(p2, s2a, 2,
            "Entrevistamos a vecinos del barrio",
            "planificacion", "Espacio Social y Ciudadano", "Historia",
            "CE2", "Diseña y realiza una entrevista como herramienta de investigación histórica.",
            "Entrevista como fuente oral. Historia local. Patrimonio cultural.",
            "Elabora un guión de entrevista y registra al menos cinco respuestas significativas.",
            "Recoger la memoria oral del barrio como fuente histórica complementaria.",
            "Diseño del guión + entrevistas a vecinos o familiares + sistematización de respuestas.",
            "Comunicación,Ciudadanía,Pensamiento histórico",
            9, 10, "done"),

        act(p2, s2a, 3,
            "Línea de tiempo del barrio",
            "planificacion", "Espacio Social y Ciudadano", "Historia",
            "CE4", "Elabora una línea de tiempo con hitos relevantes de la historia barrial.",
            "Línea de tiempo. Cronología. Hitos históricos locales y nacionales relacionados.",
            "Ubica correctamente al menos seis hitos con fecha, nombre y breve descripción.",
            "Sintetizar la historia del barrio en una representación temporal visual y colectiva.",
            "Trabajo grupal + materiales de historia local + construcción de la línea de tiempo.",
            "Pensamiento histórico,Trabajo colaborativo",
            9, 10, "done"),

        # ── s2b: El espacio y sus transformaciones ────────────────────────────
        act(p2, s2b, 1,
            "Mapa del barrio: lectura e interpretación",
            "planificacion", "Espacio Social y Ciudadano", "Geografía",
            "CE4", "Lee e interpreta un mapa urbano identificando referencias y escala.",
            "Plano urbano. Escala. Referencias cartográficas. Orientación.",
            "Localiza correctamente cinco lugares del barrio en el mapa usando referencias.",
            "Desarrollar habilidades cartográficas para analizar el espacio geográfico local.",
            "Trabajo con mapa impreso + identificación de puntos + medición de distancias.",
            "Pensamiento espacial,Pensamiento matemático",
            10, 11, "in_progress"),

        act(p2, s2b, 2,
            "Antes y ahora: cambios en el uso del suelo",
            "planificacion", "Espacio Social y Ciudadano", "Geografía",
            "CE4", "Compara el uso del suelo en distintos momentos históricos del barrio.",
            "Uso del suelo: residencial, comercial, industrial, verde. Cambio urbano.",
            "Identifica al menos tres cambios en el uso del suelo y los relaciona con factores históricos.",
            "Analizar cómo las decisiones humanas transforman el espacio urbano a lo largo del tiempo.",
            "Comparación de mapas históricos y actuales + discusión grupal + cuadro de cambios.",
            "Pensamiento espacial,Pensamiento crítico",
            11, 12, "pending"),

        act(p2, s2b, 3,
            "La maqueta del barrio: planificación y materiales",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE2", "Planifica la construcción de una maqueta a escala del barrio.",
            "Maqueta. Escala. Materiales reciclados. Representación espacial.",
            "Elabora un plano de la maqueta con medidas proporcionales y lista de materiales.",
            "Integrar los conocimientos geográficos en una producción tridimensional colectiva.",
            "Diseño del plano de la maqueta + selección de materiales + asignación de sectores.",
            "Creatividad,Pensamiento espacial,Trabajo colaborativo",
            11, 12, "pending"),

        # ── s2c: Voces del barrio: entrevistas y mural ─────────────────────────
        act(p2, s2c, 1,
            "Procesamos las entrevistas: selección de testimonios",
            "planificacion", "Espacio Comunicación Artística", "Lengua",
            "CE3", "Selecciona y organiza fragmentos de entrevistas para incluir en el mural.",
            "Selección de información. Cita textual. Criterios de relevancia.",
            "Elige al menos tres testimonios con justificación de su relevancia para el mural.",
            "Transformar los datos recolectados en contenido narrativo para el producto final.",
            "Revisión de registros de entrevistas + selección grupal + justificación escrita.",
            "Comunicación,Pensamiento crítico",
            12, 13, "pending"),

        act(p2, s2c, 2,
            "Construcción del mural histórico del barrio",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE2", "Produce una obra colectiva que integra imágenes, textos y datos históricos.",
            "Mural. Composición visual. Texto e imagen. Trabajo colectivo.",
            "Participa en el diseño y elaboración de al menos una sección del mural con coherencia visual.",
            "Comunicar la historia del barrio de forma artística, visual y colectiva.",
            "Diseño del boceto general + elaboración por sectores + integración final.",
            "Creatividad,Comunicación,Trabajo colaborativo",
            13, 14, "pending"),

        act(p2, s2c, 3,
            "Presentación del mural y la maqueta a la comunidad",
            "planificacion", "Espacio Social y Ciudadano", "Derecho y Ciudadanía",
            "CE2", "Presenta oralmente los resultados del proyecto ante la comunidad escolar.",
            "Presentación oral. Argumento. Escucha activa. Participación ciudadana.",
            "Expone al menos un aspecto del proyecto con claridad y responde preguntas del público.",
            "Compartir con la comunidad el resultado del trabajo de investigación e integración.",
            "Preparación de la presentación + evento de muestra + reflexión grupal posterior.",
            "Comunicación,Ciudadanía,Trabajo colaborativo",
            13, 14, "pending"),

        # ── s3a: Fuentes de energía ───────────────────────────────────────────
        act(p3, s3a, 1,
            "¿De dónde viene la energía que usamos?",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE1", "Clasifica las fuentes de energía en renovables y no renovables con ejemplos.",
            "Energía: definición y tipos. Fuentes renovables y no renovables. Impacto ambiental.",
            "Clasifica correctamente al menos seis fuentes de energía y menciona un impacto de cada una.",
            "Establecer la base conceptual sobre energía para desarrollar el proyecto.",
            "Video introductorio + organizador gráfico + debate sobre ventajas y desventajas.",
            "Pensamiento científico,Pensamiento crítico",
            14, 15, "pending"),

        act(p3, s3a, 2,
            "Experimento: el sol como fuente de energía",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE1", "Observa y registra la capacidad del sol para calentar materiales distintos.",
            "Energía solar. Absorción de calor. Variables y control en experimentos.",
            "Registra los datos del experimento y concluye cuál material absorbió más calor y por qué.",
            "Vivenciar el potencial de la energía solar como fuente renovable.",
            "Experimento con cajas de colores bajo el sol + medición de temperatura + conclusiones.",
            "Pensamiento científico,Resolución de problemas",
            15, 16, "pending"),

        act(p3, s3a, 3,
            "Informe: ventajas y desventajas de las energías renovables",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza",
            "CE3", "Elabora un informe comparativo sobre fuentes de energía renovable.",
            "Informe científico. Comparación. Argumentación basada en datos.",
            "Escribe un informe con introducción, desarrollo comparativo y conclusión fundamentada.",
            "Sistematizar la investigación sobre energías renovables en un texto científico.",
            "Investigación guiada + redacción individual + revisión entre pares.",
            "Pensamiento científico,Comunicación",
            16, 17, "pending"),

        # ── s3b: Energías renovables en Uruguay ────────────────────────────────
        act(p3, s3b, 1,
            "Uruguay y las energías renovables: investigación",
            "planificacion", "Espacio Social y Ciudadano", "Geografía",
            "CE3", "Investiga el rol de Uruguay como referente regional en energías renovables.",
            "Política energética uruguaya. Parques eólicos. Energía hidroeléctrica.",
            "Identifica al menos tres datos específicos del sistema energético uruguayo con fuentes.",
            "Contextualizar el proyecto en la realidad energética nacional.",
            "Lectura de artículos + búsqueda guiada + síntesis en ficha informativa.",
            "Pensamiento social,Comunicación",
            17, 18, "pending"),

        act(p3, s3b, 2,
            "Cálculo de consumo energético del hogar",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE5", "Aplica operaciones con números naturales y decimales para calcular el consumo eléctrico.",
            "Consumo eléctrico: vatios, kilowatts/hora. Lectura de facturas. Proporcionalidad.",
            "Calcula correctamente el consumo semanal de al menos tres artefactos del hogar.",
            "Aplicar matemática en un contexto real de sostenibilidad energética.",
            "Tabla de artefactos + cálculo de consumo + comparación entre hogares.",
            "Pensamiento matemático,Resolución de problemas",
            18, 19, "pending"),

        act(p3, s3b, 3,
            "Debate: ¿debemos seguir usando energías no renovables?",
            "planificacion", "Espacio Social y Ciudadano", "Derecho y Ciudadanía",
            "CE3", "Argumenta una posición sobre el uso de energías no renovables con fundamentos.",
            "Debate. Argumentación. Contraargumentación. Ciudadanía ambiental.",
            "Expone al menos dos argumentos y responde al menos una objeción del equipo contrario.",
            "Desarrollar la capacidad argumentativa y la conciencia ciudadana ambiental.",
            "Preparación de argumentos en grupos + debate estructurado + reflexión final.",
            "Pensamiento crítico,Comunicación,Ciudadanía",
            18, 19, "pending"),

        # ── s3c: Diseñamos nuestra casa del futuro ─────────────────────────────
        act(p3, s3c, 1,
            "Diseño de la vivienda sustentable: boceto y planificación",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE1", "Diseña el plano y la estructura de una vivienda sustentable en equipo.",
            "Diseño arquitectónico básico. Plano. Integración de fuentes renovables.",
            "Elabora un boceto con al menos dos fuentes de energía renovable integradas y justificadas.",
            "Planificar la maqueta integrando los aprendizajes sobre energías renovables.",
            "Lluvia de ideas + boceto grupal + selección de diseño + lista de materiales.",
            "Creatividad,Pensamiento científico,Trabajo colaborativo",
            19, 20, "pending"),

        act(p3, s3c, 2,
            "Construcción de la maqueta de vivienda sustentable",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE2", "Construye la maqueta aplicando los principios de diseño sustentable planificados.",
            "Construcción de maqueta. Materiales reciclados. Escala.",
            "Construye la sección asignada con coherencia al diseño grupal y materiales acordados.",
            "Materializar el diseño de la vivienda sustentable como producto final del proyecto.",
            "Construcción por roles + supervisión docente + ajustes finales + preparación exposición.",
            "Creatividad,Trabajo colaborativo,Resolución de problemas",
            20, 21, "pending"),

        act(p3, s3c, 3,
            "Presentación de la vivienda sustentable ante la comunidad",
            "planificacion", "Espacio Comunicación Artística", "Lengua",
            "CE3", "Presenta el proyecto de vivienda sustentable con argumentos técnicos y ambientales.",
            "Presentación oral técnica. Argumentación. Uso de vocabulario específico.",
            "Presenta el proyecto de forma fluida, menciona las fuentes renovables integradas y su justificación.",
            "Comunicar los aprendizajes del proyecto a la comunidad escolar.",
            "Preparación de la exposición + presentación ante familias y autoridades + Q&A.",
            "Comunicación,Ciudadanía,Creatividad",
            20, 21, "pending"),

        # ── s4a: Porcentajes, descuentos y aumentos ────────────────────────────
        act(p4, s4a, 1,
            "¿Qué es un porcentaje? Situaciones reales",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE1", "Comprende el concepto de porcentaje y lo aplica en situaciones de descuento y aumento.",
            "Porcentaje: definición, cálculo, representación. Descuento. Aumento.",
            "Calcula correctamente el porcentaje de al menos cinco situaciones con contexto real.",
            "Construir el concepto de porcentaje desde situaciones de la vida cotidiana.",
            "Situaciones de descuento en folletos + cálculo + verificación + puesta en común.",
            "Pensamiento matemático,Resolución de problemas",
            21, 22, "pending"),

        act(p4, s4a, 2,
            "Ofertas y precios: simulamos una compra",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE2", "Resuelve situaciones de compra-venta aplicando descuentos y aumentos porcentuales.",
            "Precio de costo, precio de venta, ganancia. Descuento porcentual. IVA.",
            "Calcula el precio final con descuento e IVA en al menos tres productos distintos.",
            "Aplicar el porcentaje en una simulación de mercado que anticipa el producto final.",
            "Simulación de compra con catálogos + cálculo por equipos + corrección grupal.",
            "Pensamiento matemático,Resolución de problemas,Trabajo colaborativo",
            22, 23, "pending"),

        act(p4, s4a, 3,
            "Registro de datos: tablas y gráficas del mercado",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE1", "Organiza y representa datos del mercado escolar en tablas y gráficas.",
            "Tabla de datos. Gráfica de barras y circular. Interpretación.",
            "Elabora una gráfica de barras y una circular con datos reales del mercado planificado.",
            "Desarrollar habilidades de estadística descriptiva en un contexto de proyecto real.",
            "Recolección de datos de ventas simuladas + tabulación + graficación + análisis.",
            "Pensamiento matemático,Comunicación",
            22, 23, "pending"),

        # ── s4b: Presupuesto y planificación ───────────────────────────────────
        act(p4, s4b, 1,
            "¿Cuánto cuesta hacer nuestros productos?",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE2", "Calcula el costo de producción de cada producto del mercado.",
            "Costo de producción: materiales, insumos. Precio de costo. Margen de ganancia.",
            "Calcula correctamente el costo de producción de al menos dos productos del grupo.",
            "Aplicar el concepto de costo de producción como base para fijar precios de venta.",
            "Investigación de precios reales + cálculo por equipos + comparación entre grupos.",
            "Pensamiento matemático,Resolución de problemas",
            23, 24, "pending"),

        act(p4, s4b, 2,
            "Definimos precios y presupuesto del mercado",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE5", "Elabora un presupuesto completo para el mercado escolar con precios justificados.",
            "Presupuesto. Precio de venta. Ganancia esperada. Registro contable básico.",
            "Elabora un presupuesto con ingresos esperados, costos y ganancia proyectada.",
            "Integrar los conceptos de costo, precio y ganancia en una planificación financiera real.",
            "Elaboración del presupuesto grupal + revisión docente + ajustes + versión final.",
            "Pensamiento matemático,Resolución de problemas,Trabajo colaborativo",
            24, 25, "pending"),

        act(p4, s4b, 3,
            "Producimos los artículos para el mercado",
            "planificacion", "Espacio Comunicación Artística", "Educación Artística",
            "CE1", "Elabora los productos para el mercado siguiendo el plan de producción acordado.",
            "Producción artesanal. Planificación. Control de calidad básico.",
            "Produce la cantidad acordada de su producto con los estándares de calidad definidos.",
            "Materializar los productos del emprendimiento como paso previo al mercado.",
            "Producción por equipos + control de calidad + empaque + etiquetado.",
            "Creatividad,Trabajo colaborativo,Resolución de problemas",
            24, 25, "pending"),

        # ── s4c: El mercado escolar en acción ─────────────────────────────────
        act(p4, s4c, 1,
            "Montaje y apertura del mercado escolar",
            "planificacion", "Espacio Social y Ciudadano", "Derecho y Ciudadanía",
            "CE2", "Organiza y ejecuta la apertura del mercado escolar asumiendo su rol de forma responsable.",
            "Organización de eventos. Rol del vendedor. Atención al cliente. Trabajo en equipo.",
            "Asume su rol, atiende al menos tres clientes y registra las ventas realizadas.",
            "Poner en práctica el emprendimiento escolar como experiencia de economía real.",
            "Montaje de stands + apertura al público + venta y registro + cierre del evento.",
            "Ciudadanía,Comunicación,Trabajo colaborativo",
            25, 26, "pending"),

        act(p4, s4c, 2,
            "Balance del mercado: ¿ganamos o perdimos?",
            "planificacion", "Espacio Científico-Matemático", "Matemática",
            "CE5", "Calcula el resultado económico del mercado y lo compara con el presupuesto proyectado.",
            "Balance financiero. Ingresos reales vs. proyectados. Variación porcentual.",
            "Calcula la ganancia o pérdida real y la compara con la proyectada con variación porcentual.",
            "Reflexionar sobre el resultado del emprendimiento desde el pensamiento matemático.",
            "Registro de ventas + cálculo del balance + comparación con presupuesto + conclusiones.",
            "Pensamiento matemático,Resolución de problemas,Comunicación",
            25, 26, "pending"),

        act(p4, s4c, 3,
            "Reflexión final: ¿qué aprendimos con el mercado?",
            "planificacion", "Espacio Comunicación Artística", "Lengua",
            "CE3", "Produce un texto reflexivo sobre los aprendizajes del proyecto de emprendimiento.",
            "Texto reflexivo. Metacognición. Autoevaluación del proceso.",
            "Escribe un párrafo reflexivo que menciona al menos tres aprendizajes concretos del proyecto.",
            "Cerrar el proyecto con una instancia de metacognición individual y colectiva.",
            "Reflexión individual escrita + puesta en común grupal + cierre del proyecto.",
            "Comunicación,Pensamiento crítico",
            25, 26, "pending"),
    ]

    c.executemany("""
        INSERT OR IGNORE INTO activities
        (id, user_id, project_id, sequence_id, group_id, "order", title,
         activity_type, curriculum_space, curriculum_unit, stage,
         specific_competency_code, specific_competency,
         curriculum_content, achievement_criterion, learning_goal,
         methodology, general_competencies, period_start, period_end, status,
         created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, acts)

    proj_count = len(projects)
    seq_count = len(sequences)
    act_count = len(acts)
    print(f"✓ {proj_count} proyectos, {seq_count} secuencias, {act_count} actividades creadas")


def seed(conn: sqlite3.Connection):
    c = conn.cursor()
    seed_groups(c)
    seed_students(c)
    seed_projects_and_content(c)
    conn.commit()
    print("✓ Seed completado exitosamente")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    try:
        purge(conn)
        seed(conn)
    finally:
        conn.close()

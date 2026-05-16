"""
Seed de datos de desarrollo para Facilitador Docente EBI.
Carga datos realistas bajo el usuario y grupo ya existentes en ebi.db.

Uso:
    uv run python scripts/seed_dev.py
"""

import json
import sqlite3
import uuid
from datetime import date, timedelta, datetime

DB_PATH = "ebi.db"
NOW = datetime.utcnow().isoformat()
USER_ID = "user_3Bi4BfcIA20dD13HQ0h7jir8dJF"
GROUP_ID = "7c8c4546-d545-4578-823a-69f33027696a"

# Tramo 4, 5.to grado — grupo "Colegio 01", año lectivo 2026


def uid() -> str:
    return str(uuid.uuid4())


def d(offset_weeks: int = 0) -> str:
    return (date(2026, 3, 11) + timedelta(weeks=offset_weeks)).isoformat()


def seed(conn: sqlite3.Connection):
    c = conn.cursor()

    # ── Proyectos integrados ──────────────────────────────────────────────────
    p1 = uid()
    p2 = uid()
    p3 = uid()

    projects = [
        (p1, GROUP_ID, USER_ID,
         "El agua como recurso vital",
         "Comprender el ciclo del agua, su importancia para los seres vivos y las acciones humanas que afectan su disponibilidad.",
         8, "Mural colectivo + campaña de ahorro de agua para la escuela",
         json.dumps(["espacio_cientifico_matematico", "espacio_comunicacion_artistica"]),
         json.dumps(["CE1", "CE3"]),
         d(0), d(8), NOW, NOW),
        (p2, GROUP_ID, USER_ID,
         "Somos ciudadanos: derechos y responsabilidades",
         "Reflexionar sobre los derechos y deberes de los niños en la comunidad escolar y barrial.",
         6, "Fanzine de derechos elaborado por los estudiantes",
         json.dumps(["espacio_social_ciudadano", "espacio_comunicacion_artistica"]),
         json.dumps(["CE2", "CE4"]),
         d(8), d(14), NOW, NOW),
        (p3, GROUP_ID, USER_ID,
         "Matemática en la vida cotidiana",
         "Resolver situaciones problemáticas reales usando números racionales, proporcionalidad y medidas.",
         6, "Feria de productos con presupuesto real y registro de ganancias",
         json.dumps(["espacio_cientifico_matematico"]),
         json.dumps(["CE1", "CE2", "CE5"]),
         d(14), d(20), NOW, NOW),
    ]

    c.executemany("""
        INSERT OR IGNORE INTO integrative_projects
        (id, group_id, user_id, name, purpose, duration_weeks, final_product,
         curriculum_space_ids, competency_ids, start_date, end_date, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, projects)

    # ── Secuencias de actividades ─────────────────────────────────────────────
    s1a = uid(); s1b = uid(); s1c = uid()
    s2a = uid(); s2b = uid()
    s3a = uid(); s3b = uid()

    sequences = [
        # Proyecto 1
        (s1a, p1, USER_ID, "Exploración del ciclo del agua", "Identificar y describir las etapas del ciclo hidrológico mediante observación directa y experimentación.", 1, d(0), d(2), NOW, NOW),
        (s1b, p1, USER_ID, "Impacto humano en el agua", "Analizar causas y consecuencias de la contaminación y el uso excesivo del agua, proponiendo acciones de cuidado.", 2, d(2), d(5), NOW, NOW),
        (s1c, p1, USER_ID, "Campaña escolar de ahorro de agua", "Diseñar y ejecutar una campaña de concientización sobre el uso responsable del agua en la comunidad escolar.", 3, d(5), d(8), NOW, NOW),
        # Proyecto 2
        (s2a, p2, USER_ID, "¿Qué son los derechos?", "Explorar el concepto de derecho, su origen histórico y los organismos que los garantizan.", 1, d(8), d(11), NOW, NOW),
        (s2b, p2, USER_ID, "Mis derechos en la escuela y el barrio", "Identificar situaciones cotidianas donde se ejercen o vulneran derechos y proponer respuestas ciudadanas.", 2, d(11), d(14), NOW, NOW),
        # Proyecto 3
        (s3a, p3, USER_ID, "Números racionales en contexto", "Operar con fracciones y decimales en situaciones de compra-venta, escalas y recetas.", 1, d(14), d(17), NOW, NOW),
        (s3b, p3, USER_ID, "Proporcionalidad y porcentaje", "Resolver problemas de proporcionalidad directa e inversa y calcular porcentajes en contextos de descuentos y aumentos.", 2, d(17), d(20), NOW, NOW),
    ]

    c.executemany("""
        INSERT OR IGNORE INTO activity_sequences
        (id, project_id, user_id, name, learning_goal, "order", start_date, end_date, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, sequences)

    # ── Actividades ───────────────────────────────────────────────────────────
    def act(
        project_id, sequence_id, order, title,
        activity_type, curriculum_space, curriculum_unit, stage,
        competency_code, competency, content, criterion,
        goal, methodology, general_competencies,
        start, end, status,
    ):
        return (
            uid(), USER_ID, project_id, sequence_id, GROUP_ID, order, title,
            activity_type, curriculum_space, curriculum_unit, stage,
            competency_code, competency, content, criterion,
            goal, methodology, general_competencies,
            start, end, status, NOW, NOW,
        )

    acts = [
        # s1a — Ciclo del agua
        act(p1, s1a, 1, "El agua en la naturaleza — observación y registro",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza", 4,
            "CE1", "Identifica y describe los estados del agua y sus transformaciones en la naturaleza.",
            "Ciclo hidrológico: evaporación, condensación, precipitación y escorrentía.",
            "Describe correctamente al menos tres etapas del ciclo del agua con ejemplos del entorno local.",
            "Observar el entorno escolar y registrar fuentes de agua visibles.",
            "Observación directa + lectura de texto informativo + puesta en común grupal.",
            "Pensamiento crítico,Comunicación", d(0), d(1), "done"),

        act(p1, s1a, 2, "Experimento: el ciclo del agua en una bolsa",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza", 4,
            "CE1", "Reproducir el ciclo del agua de forma experimental y registrar los cambios observados.",
            "Estados del agua. Evaporación y condensación. Registro científico.",
            "Registra con precisión los cambios de estado observados durante el experimento.",
            "Reproducir el ciclo en una bolsa ziploc con agua coloreada expuesta al sol.",
            "Experimento guiado + registro en tabla + socialización de observaciones.",
            "Pensamiento científico,Trabajo colaborativo", d(1), d(2), "done"),

        act(p1, s1a, 3, "Infografía: el ciclo del agua paso a paso",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza", 4,
            "CE1", "Comunicar de forma visual el ciclo del agua integrando vocabulario científico aprendido.",
            "Ciclo hidrológico. Vocabulario específico: evaporación, condensación, precipitación.",
            "Elabora una infografía que incluye todas las etapas del ciclo con vocabulario correcto.",
            "Representar visualmente el ciclo del agua con vocabulario técnico adecuado.",
            "Diseño grupal de infografía + revisión entre pares + exposición al grupo.",
            "Comunicación,Creatividad", d(2), d(2), "done"),

        # s1b — Impacto humano
        act(p1, s1b, 1, "Noticias sobre el agua: análisis de fuentes",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza", 4,
            "CE3", "Analizar noticias reales sobre escasez y contaminación del agua.",
            "Contaminación del agua. Escasez hídrica. Acción humana sobre el ambiente.",
            "Identifica al menos dos causas de contaminación y propone una acción concreta de mejora.",
            "Analizar críticamente fuentes periodísticas sobre el agua como recurso amenazado.",
            "Lectura de noticias + debate guiado + cuadro comparativo causas/consecuencias.",
            "Pensamiento crítico,Ciudadanía", d(2), d(3), "done"),

        act(p1, s1b, 2, "El agua en mi ciudad: encuesta a la comunidad",
            "planificacion", "Espacio Científico-Matemático", "Matemática", 4,
            "CE2", "Recolectar y organizar datos sobre el uso doméstico del agua.",
            "Estadística: tablas de frecuencia, gráficas de barras. Diseño de encuesta.",
            "Diseña una encuesta, tabula los resultados y elabora una gráfica de barras correctamente.",
            "Aplicar herramientas estadísticas para analizar el consumo de agua en el entorno familiar.",
            "Diseño de encuesta grupal + recolección domiciliaria + tabulación + graficación.",
            "Pensamiento matemático,Trabajo colaborativo", d(3), d(4), "in_progress"),

        act(p1, s1b, 3, "Manifiesto por el agua",
            "planificacion", "Espacio Comunicación Artística", "Lengua", 4,
            "CE3", "Producir un texto argumentativo colectivo sobre el cuidado del agua.",
            "Texto argumentativo. Recursos retóricos. Propósito comunicativo.",
            "Escribe un párrafo argumentativo con tesis, argumentos y conclusión coherente.",
            "Producir colectivamente un texto que convenza sobre la importancia de cuidar el agua.",
            "Taller de escritura cooperativa + revisión de borradores + lectura final en voz alta.",
            "Comunicación,Ciudadanía", d(4), d(5), "pending"),

        # s2a — ¿Qué son los derechos?
        act(p2, s2a, 1, "La Convención sobre los Derechos del Niño — lectura comentada",
            "planificacion", "Espacio Social y Ciudadano", "Derecho y Ciudadanía", 4,
            "CE2", "Conocer los derechos fundamentales de los niños y vincularlos con la vida cotidiana.",
            "Convención sobre los Derechos del Niño (CDN). Derechos civiles, sociales y culturales.",
            "Identifica y explica al menos cuatro derechos del niño con ejemplos propios.",
            "Comprender el alcance y significado de los derechos reconocidos internacionalmente.",
            "Lectura fragmentada de la CDN + análisis grupal + cuadro de síntesis + plenaria.",
            "Ciudadanía,Comunicación", d(8), d(9), "done"),

        act(p2, s2a, 2, "Historia de los derechos humanos — línea de tiempo",
            "planificacion", "Espacio Social y Ciudadano", "Historia", 4,
            "CE4", "Ubicar los hitos históricos más relevantes en la construcción de los derechos humanos.",
            "Declaración Universal de los Derechos Humanos (1948). Constitución uruguaya. ONU.",
            "Elabora una línea de tiempo con al menos cinco hitos correctamente ubicados y descritos.",
            "Situar históricamente el surgimiento y evolución de los derechos humanos.",
            "Investigación guiada con fuentes seleccionadas + línea de tiempo grupal + presentación.",
            "Pensamiento histórico,Trabajo colaborativo", d(9), d(11), "in_progress"),

        # s3a — Números racionales
        act(p3, s3a, 1, "Fracciones en la cocina — recetas con proporciones",
            "planificacion", "Espacio Científico-Matemático", "Matemática", 4,
            "CE1", "Operar con fracciones ajustando cantidades de recetas para distintas porciones.",
            "Fracciones: equivalencia, suma, resta y multiplicación por entero. Proporcionalidad.",
            "Calcula correctamente las cantidades de una receta para el doble y la mitad de porciones.",
            "Usar fracciones para resolver problemas de proporcionalidad en contextos reales.",
            "Análisis de recetas reales + cálculo de ajuste de porciones + socialización de resultados.",
            "Pensamiento matemático,Resolución de problemas", d(14), d(15), "done"),

        act(p3, s3a, 2, "Decimales en el supermercado",
            "planificacion", "Espacio Científico-Matemático", "Matemática", 4,
            "CE2", "Resolver situaciones de compra-venta con números decimales.",
            "Números decimales: operaciones y comparación. Estimación. Redondeo.",
            "Resuelve correctamente situaciones de compra con vuelto usando estimación y cálculo exacto.",
            "Aplicar operaciones con decimales en contextos económicos cotidianos.",
            "Simulación de compra con folletos de supermercado reales + verificación grupal.",
            "Pensamiento matemático,Resolución de problemas", d(15), d(16), "done"),

        act(p3, s3a, 3, "Escalas en mapas de Montevideo",
            "planificacion", "Espacio Científico-Matemático", "Matemática", 4,
            "CE5", "Interpretar y usar escalas en mapas para calcular distancias reales.",
            "Escala: razón entre medida representada y medida real. Conversión de unidades.",
            "Calcula correctamente al menos tres distancias reales a partir de la escala del mapa.",
            "Usar la proporcionalidad para interpretar representaciones cartográficas.",
            "Trabajo con mapa impreso de Montevideo + medición con regla + aplicación de escala.",
            "Pensamiento matemático,Espacialidad", d(16), d(17), "pending"),

        # Actividades sueltas (sin secuencia)
        act(p1, None, 1, "Visita al arroyo Miguelete — registro de campo",
            "planificacion", "Espacio Científico-Matemático", "Ciencias de la Naturaleza", 4,
            "CE3", "Observar el estado real de un curso de agua urbano e identificar indicadores de contaminación.",
            "Indicadores de calidad del agua. Biodiversidad acuática. Registro científico de campo.",
            "Completa una ficha de campo con observaciones y conclusiones fundamentadas.",
            "Conectar el conocimiento sobre el ciclo del agua con una realidad ambiental local.",
            "Salida de campo + ficha estructurada + entrevista a referente ambiental + análisis posterior.",
            "Pensamiento científico,Ciudadanía", d(4), d(5), "pending"),

        act(p2, None, 1, "Juego de roles: el parlamento de los derechos",
            "planificacion", "Espacio Social y Ciudadano", "Derecho y Ciudadanía", 4,
            "CE2", "Vivenciar el proceso democrático de elaboración de normas mediante simulación.",
            "Democracia representativa. Elaboración de leyes. Roles: legisladores, ciudadanos, prensa.",
            "Participa activamente en el rol asignado argumentando con fundamentos su posición.",
            "Comprender el funcionamiento del sistema democrático desde la experiencia directa.",
            "Asignación de roles + preparación de argumentos + debate parlamentario + reflexión final.",
            "Ciudadanía,Comunicación,Trabajo colaborativo", d(11), d(12), "pending"),
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

    conn.commit()
    seq_acts = [a for a in acts if a[3] is not None]
    isolated_acts = [a for a in acts if a[3] is None]
    print("✓ Seed completado:")
    print(f"  {len(projects)} proyectos integrados")
    print(f"  {len(sequences)} secuencias de actividades")
    print(f"  {len(seq_acts)} actividades en secuencias")
    print(f"  {len(isolated_acts)} actividades sueltas")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn)
    finally:
        conn.close()

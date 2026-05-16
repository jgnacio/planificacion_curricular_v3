"""
Seed raw_content for activities that don't have it yet.
Run from planificacion_curricular_v3/ with: python scripts/seed_raw_content.py
"""
import json
import sqlite3

DB_PATH = "./ebi.db"

ACTIVITIES = [
    {
        "id": "aee94666-bf34-463e-82b7-d6a1f087ff5c",
        "raw_content": {
            "titulo": "El agua en la naturaleza — observación y registro",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Esta propuesta conecta el conocimiento científico con la observación directa del entorno escolar, permitiendo que los estudiantes identifiquen manifestaciones reales del ciclo del agua. Trabajar desde lo concreto y cercano favorece la apropiación del vocabulario específico (CE1) y promueve la curiosidad científica como punto de partida del proyecto integrador sobre el agua.",
            "metodologia": "Observación directa",
            "metodologia_descripcion": "Los estudiantes exploran el entorno escolar con una mirada científica estructurada. A partir de la observación guiada y el registro sistemático, construyen conocimiento desde la experiencia directa antes de acceder al texto informativo.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Activar conocimientos previos sobre el agua y sus formas en la naturaleza.",
                    "actividad": "Se proyectan tres imágenes: una nube de tormenta sobre Montevideo, el Río Santa Lucía y el rocío sobre el pasto una mañana de invierno. Se pregunta: '¿Qué tienen en común estas tres imágenes? ¿De dónde viene esa agua?' Los estudiantes comparten sus ideas en voz alta mientras el docente las anota en el pizarrón sin corregir aún.",
                    "rol_docente": "Presenta las imágenes, lanza la pregunta disparadora y registra las hipótesis iniciales sin valorarlas todavía.",
                    "recursos": "Proyector o imágenes impresas A4 de nube de tormenta, río y rocío; pizarrón y marcadores."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Observar el entorno escolar, identificar fuentes de agua visibles y registrarlas con vocabulario científico.",
                    "actividad": "En grupos de tres, los estudiantes realizan un recorrido por el patio y el jardín de la escuela con una 'guía de observación' impresa. Deben identificar y registrar: superficies con agua acumulada, plantas con humedad, zonas donde el sol evapora agua visible, canales de desagüe. Cada hallazgo se anota con un dibujo esquemático y una descripción breve. Al regresar al aula, completan una tabla de doble entrada: tipo de agua observada / etapa del ciclo a la que creen que pertenece.",
                    "rol_docente": "Acompaña el recorrido haciendo preguntas orientadoras ('¿Por qué creen que hay humedad acá?', '¿Hacia dónde va esa agua?'). En el aula, circula por los grupos durante el completado de la tabla.",
                    "recursos": "Guías de observación impresas (una por grupo), lápices, tabla de doble entrada en hoja A3, tablets o libros de consulta disponibles."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Describir al menos tres etapas del ciclo del agua con ejemplos del entorno observado.",
                    "actividad": "Cada grupo comparte un hallazgo de su tabla. El docente va construyendo en el pizarrón un esquema colectivo del ciclo del agua vinculando cada aporte con la etapa correspondiente (evaporación, condensación, precipitación, escorrentía). Al finalizar, cada estudiante copia el esquema en su cuaderno y agrega al menos un ejemplo propio observado en la jornada.",
                    "rol_docente": "Sistematiza los aportes grupales construyendo el esquema del ciclo, introduce el vocabulario científico correcto y cierra con una pregunta de conexión hacia la próxima actividad.",
                    "recursos": "Pizarrón, marcadores de colores, cuadernos de los estudiantes."
                }
            ],
            "ce_codigo": "CE1",
            "ce_texto": "Identifica y describe los estados del agua y sus transformaciones en la naturaleza.",
            "contenido": "Ciclo hidrológico: evaporación, condensación, precipitación y escorrentía.",
            "criterio_de_logro": "Describe correctamente al menos tres etapas del ciclo del agua con ejemplos del entorno local.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Ciencias de la Naturaleza",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento crítico", "Comunicación"]
        }
    },
    {
        "id": "3e9e1caf-2865-4cfc-9cf3-3ad0546ae841",
        "raw_content": {
            "titulo": "Experimento: el ciclo del agua en una bolsa",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "El experimento de la bolsa ziploc permite que los estudiantes observen en tiempo real los procesos de evaporación y condensación en un sistema cerrado, haciendo visible lo que normalmente ocurre a escala planetaria. Esta experiencia concreta fortalece la comprensión del ciclo del agua (CE1) y entrena habilidades clave del pensamiento científico: hipótesis, registro y análisis de evidencia.",
            "metodologia": "Experimento guiado",
            "metodologia_descripcion": "Los estudiantes formulan una hipótesis antes del experimento, observan y registran los cambios durante la exposición al sol, y los contrastan con su predicción inicial. El rol docente es de facilitador: guía sin revelar el resultado.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Formular una hipótesis sobre qué ocurrirá con el agua dentro de una bolsa sellada al sol.",
                    "actividad": "Se muestra una bolsa ziploc transparente con agua coloreada (azul con colorante alimentario) ya sellada. Se pregunta: '¿Qué creen que va a pasar con esta bolsa si la pegamos en la ventana donde le da el sol durante la clase?' Cada estudiante escribe su hipótesis en el cuaderno: qué espera ver, dónde y por qué.",
                    "rol_docente": "Presenta el material, formula la pregunta generadora y da tiempo para que cada uno escriba sin intervenir en las hipótesis.",
                    "recursos": "Bolsa ziploc 1L con agua coloreada (preparada previamente), cinta adhesiva para ventana, cuadernos."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Registrar en una tabla los cambios de estado observados en el experimento.",
                    "actividad": "Se pega la bolsa en la ventana con mayor exposición solar. Los estudiantes trabajan en parejas: cada 8 minutos observan la bolsa y completan una fila de su tabla de registro (columnas: tiempo transcurrido / zona inferior / zona superior / temperatura percibida al tacto). Guiados por el docente, identifican las gotas que aparecen en la parte superior (condensación) y la disminución visible del nivel de agua en la base (evaporación). Al terminar, comparan sus registros con la hipótesis inicial.",
                    "rol_docente": "Marca el tiempo, guía las observaciones con preguntas ('¿Dónde apareció el agua? ¿De dónde salió?') y ayuda a completar la tabla sin dar las respuestas.",
                    "recursos": "Tabla de registro impresa (una por pareja), lápices, reloj o timer visible, bolsa pegada en ventana."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Contrastar los resultados con la hipótesis inicial y explicar los procesos de evaporación y condensación.",
                    "actividad": "En plenaria, tres parejas comparten su tabla de registro. El docente sistematiza en el pizarrón los procesos identificados: evaporación (agua líquida → vapor por calor) y condensación (vapor → líquido al enfriarse en la parte superior). Se conecta explícitamente con el ciclo del agua: la bolsa es un modelo del ciclo. Cada estudiante corrige o confirma su hipótesis inicial con una oración fundamentada.",
                    "rol_docente": "Sistematiza y formaliza el vocabulario científico, conecta el modelo con el ciclo real y guía la corrección de hipótesis.",
                    "recursos": "Pizarrón, cuadernos, bolsa del experimento para mostrar en el cierre."
                }
            ],
            "ce_codigo": "CE1",
            "ce_texto": "Reproducir el ciclo del agua de forma experimental y registrar los cambios observados.",
            "contenido": "Estados del agua. Evaporación y condensación. Registro científico.",
            "criterio_de_logro": "Registra con precisión los cambios de estado observados durante el experimento.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Ciencias de la Naturaleza",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento científico", "Trabajo colaborativo"]
        }
    },
    {
        "id": "b9a7125f-8b8d-4ea6-a918-80c246e53b37",
        "raw_content": {
            "titulo": "Infografía: el ciclo del agua paso a paso",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "La creación de una infografía exige que los estudiantes integren y sinteticen lo aprendido en las dos actividades anteriores, organizando el conocimiento de forma visual y comunicable. Esta producción colectiva desarrolla la competencia comunicativa (CE1) y la creatividad, a la vez que genera un material auténtico que puede exponerse en la escuela como parte del proyecto integrador.",
            "metodologia": "Diseño colaborativo",
            "metodologia_descripcion": "Los grupos diseñan su infografía distribuyendo roles (redactor, ilustrador, corrector). Antes de la versión final, realizan una revisión entre pares siguiendo una rúbrica sencilla con tres criterios: vocabulario correcto, secuencia lógica y claridad visual.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Analizar ejemplos de infografías científicas e identificar sus elementos estructurales.",
                    "actividad": "Se proyectan dos infografías sobre temas científicos (una sobre el sistema solar y otra sobre la cadena alimentaria). Se pregunta: '¿Qué tienen en común? ¿Qué elementos usa para explicar sin usar mucho texto?' Se construye colectivamente una lista de características en el pizarrón: título, imágenes, flechas, vocabulario clave, secuencia.",
                    "rol_docente": "Proyecta las infografías, modera la discusión y sistematiza las características identificadas en el pizarrón.",
                    "recursos": "Proyector, dos infografías científicas impresas o digitales, pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Elaborar una infografía que represente todas las etapas del ciclo del agua con vocabulario técnico correcto.",
                    "actividad": "Grupos de cuatro diseñan su infografía en papel afiche. Se asignan roles: un redactor de textos breves, un ilustrador principal, un corrector de vocabulario y un organizador del espacio visual. Deben incluir las cuatro etapas del ciclo (evaporación, condensación, precipitación, escorrentía/infiltración), flechas de dirección y al menos una conexión con el contexto uruguayo (ej. Río de la Plata, lluvia en Montevideo). A mitad del tiempo, cada grupo intercambia su borrador con otro para revisión entre pares con rúbrica.",
                    "rol_docente": "Circula asignando retroalimentación específica, verifica el uso del vocabulario correcto y gestiona los tiempos.",
                    "recursos": "Papel afiche, marcadores de colores, rúbrica de revisión entre pares impresa, libros y apuntes del proyecto como referencia."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Exponer la infografía al grupo explicando las decisiones tomadas en el diseño.",
                    "actividad": "Cada grupo presenta su infografía en 90 segundos: qué incluye, qué conexión hizo con Uruguay y qué corrigió tras la revisión entre pares. Las infografías se cuelgan en el pasillo de la escuela como primera exhibición del proyecto integrador. El docente destaca un acierto específico de cada grupo.",
                    "rol_docente": "Modera las presentaciones, hace devolución constructiva grupal e indica el lugar de exhibición.",
                    "recursos": "Cinta adhesiva para colgar, pared o pasillo de exhibición."
                }
            ],
            "ce_codigo": "CE1",
            "ce_texto": "Comunicar de forma visual el ciclo del agua integrando vocabulario científico aprendido.",
            "contenido": "Ciclo hidrológico. Vocabulario específico: evaporación, condensación, precipitación.",
            "criterio_de_logro": "Elabora una infografía que incluye todas las etapas del ciclo con vocabulario correcto.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Ciencias de la Naturaleza",
            "tramo": 4,
            "competencias_mcn": ["Comunicación", "Creatividad"]
        }
    },
    {
        "id": "7bf5b23e-afbe-43f6-8275-ff360ed8c0b7",
        "raw_content": {
            "titulo": "Noticias sobre el agua: análisis de fuentes",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "El análisis de noticias reales sobre escasez y contaminación del agua sitúa el conocimiento científico en un contexto social y político concreto. Esta actividad desarrolla el pensamiento crítico (CE3) al exigir que los estudiantes distingan hechos de opiniones, identifiquen causas y consecuencias, y propongan acciones. Conecta directamente con la crisis hídrica que afectó a Uruguay en 2023, un hecho cercano y relevante para el grupo.",
            "metodologia": "Lectura crítica de fuentes",
            "metodologia_descripcion": "Cada grupo analiza una noticia diferente (El País, La Diaria, portal del MVOT) sobre el agua en Uruguay. Luego comparten hallazgos en un debate estructurado con roles asignados: vocero, cuestionador y registrador.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Activar conocimientos sobre la crisis del agua en Uruguay y el concepto de fuente periodística.",
                    "actividad": "Se muestra el titular real: 'OSE mezcló agua del Río Santa Lucía con del Río de la Plata por sequía histórica' (julio 2023). Se pregunta: '¿Alguien recuerda esto? ¿Qué pasó? ¿Cómo se enteraron?' Breve intercambio. Luego se introduce la pregunta guía de la actividad: '¿Qué nos dicen los diarios sobre el agua en Uruguay y qué podemos hacer nosotros?'",
                    "rol_docente": "Presenta el titular, modera el intercambio inicial y presenta la pregunta guía de la actividad.",
                    "recursos": "Titular impreso o proyectado, pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Analizar críticamente una noticia real identificando causas, consecuencias y posibles acciones.",
                    "actividad": "Grupos de tres reciben noticias diferentes sobre el agua en Uruguay (escasez de 2023, contaminación del Río Negro, agua potable en zonas rurales). Cada grupo completa un cuadro: ¿Qué ocurrió? / ¿Por qué? (causas humanas y naturales) / ¿Qué consecuencias tuvo? / ¿Qué propone la noticia como solución? / ¿Están de acuerdo? Luego debaten en su grupo: ¿es un problema del gobierno, de las personas, de la naturaleza o de todos?",
                    "rol_docente": "Distribuye las noticias, explica el cuadro de análisis y circula resolviendo dudas de vocabulario o contexto.",
                    "recursos": "Noticias impresas (seleccionadas y adaptadas en extensión), cuadro de análisis impreso, diccionarios disponibles."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Identificar causas de contaminación hídrica y proponer al menos una acción concreta de mejora.",
                    "actividad": "Plenaria: cada grupo comparte la causa principal identificada y la acción propuesta. El docente construye en el pizarrón una lista colectiva de causas (contaminación industrial, uso doméstico, sequía, falta de inversión) y acciones posibles (individuales, colectivas, políticas). Se reflexiona: '¿Cuál de estas acciones está en nuestras manos?' Cada estudiante elige una y la escribe en su cuaderno con una justificación breve.",
                    "rol_docente": "Modera la plenaria, sistematiza causas y acciones en el pizarrón y guía la reflexión ciudadana final.",
                    "recursos": "Pizarrón, cuadernos, cuadros de análisis completados."
                }
            ],
            "ce_codigo": "CE3",
            "ce_texto": "Analiza noticias reales sobre escasez y contaminación del agua.",
            "contenido": "Contaminación del agua. Escasez hídrica. Acción humana sobre el ambiente.",
            "criterio_de_logro": "Identifica al menos dos causas de contaminación y propone una acción concreta de mejora.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Ciencias de la Naturaleza",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento crítico", "Ciudadanía"]
        }
    },
    {
        "id": "2fbd4844-57cd-4ab8-ac00-0c1382ea6dd0",
        "raw_content": {
            "titulo": "El agua en mi ciudad: encuesta a la comunidad",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Esta actividad integra el proyecto del agua con el Espacio Matemático, aplicando herramientas estadísticas reales en un contexto significativo. Los estudiantes diseñan, aplican y analizan una encuesta sobre consumo doméstico de agua, desarrollando la competencia matemática (CE2) y la ciudadanía al conectar datos locales con la problemática global del recurso hídrico.",
            "metodologia": "Investigación estadística aplicada",
            "metodologia_descripcion": "El ciclo completo de investigación estadística: formulación de la pregunta, diseño del instrumento, recolección de datos en el entorno familiar, organización en tabla de frecuencias y representación en gráfica de barras. Los resultados alimentan una conclusión ciudadana sobre el uso del agua en la comunidad.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Identificar qué datos sobre el uso doméstico del agua vale la pena investigar y cómo formular preguntas de encuesta.",
                    "actividad": "Se presenta el dato: 'El uruguayo promedio usa 150 litros de agua por día en su hogar.' Se pregunta: '¿Creen que en sus casas usan más o menos? ¿Cómo podríamos averiguarlo?' Se discute brevemente qué preguntas servirían para una encuesta y cuáles no. El docente introduce la diferencia entre pregunta abierta y de opción múltiple en una encuesta.",
                    "rol_docente": "Presenta el dato disparador, guía la discusión sobre qué investigar y presenta brevemente los tipos de preguntas de encuesta.",
                    "recursos": "Dato impreso o proyectado, pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Diseñar una encuesta de cuatro preguntas sobre uso del agua y completar una tabla de frecuencias con los datos obtenidos.",
                    "actividad": "Grupos de cuatro diseñan su encuesta (4 preguntas de opción múltiple sobre uso del agua en el hogar: ¿cuántas veces por semana se baña? ¿deja la canilla abierta mientras se lava los dientes? etc.). Luego cada integrante encuesta a tres compañeros de otros grupos (12 respuestas por grupo). Con los datos recogidos, completan una tabla de frecuencias y calculan porcentajes simples. Finalmente, grafican los resultados de la pregunta más interesante en una gráfica de barras en papel cuadriculado.",
                    "rol_docente": "Guía el diseño de las preguntas evitando ambigüedades, supervisa la recolección de datos y apoya en la construcción de la tabla y la gráfica.",
                    "recursos": "Hoja de diseño de encuesta impresa, hojas cuadriculadas, reglas, lápices, calculadoras."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Interpretar la gráfica elaborada y formular una conclusión sobre el consumo de agua en la comunidad.",
                    "actividad": "Cada grupo comparte su gráfica y una conclusión de dos oraciones ('En nuestro grupo, el 75% de los encuestados deja la canilla abierta al lavarse los dientes, lo que equivale a X litros desperdiciados por día'). El docente conecta los hallazgos con la problemática hídrica trabajada en actividades anteriores. Se define llevar las encuestas al hogar real como tarea para recoger datos de adultos.",
                    "rol_docente": "Modera las presentaciones, ayuda a interpretar los porcentajes y conecta los datos matemáticos con el contexto ambiental.",
                    "recursos": "Gráficas elaboradas, pizarrón para sistematizar conclusiones grupales."
                }
            ],
            "ce_codigo": "CE2",
            "ce_texto": "Recolecta y organiza datos sobre el uso doméstico del agua.",
            "contenido": "Estadística: tablas de frecuencia, gráficas de barras. Diseño de encuesta.",
            "criterio_de_logro": "Diseña una encuesta, tabula los resultados y elabora una gráfica de barras correctamente.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Matemática",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento matemático", "Trabajo colaborativo"]
        }
    },
    {
        "id": "34045713-329c-4b0c-8648-7b9e614fb5e5",
        "raw_content": {
            "titulo": "Manifiesto por el agua",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "El manifiesto es el producto final del proyecto integrador sobre el agua. Esta actividad convoca todas las competencias desarrolladas en el trayecto: el conocimiento científico, la mirada ciudadana y la capacidad comunicativa. Producir un texto argumentativo colectivo (CE3) que sirva para ser publicado en la revista escolar o leído en acto escolar da autenticidad y propósito real a la escritura.",
            "metodologia": "Taller de escritura cooperativa",
            "metodologia_descripcion": "La clase funciona como un taller de escritura con tres fases: producción de borradores individuales, revisión en pares con protocolo de retroalimentación y escritura cooperativa del manifiesto final. El docente actúa como editor que orienta sin corregir directamente.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Identificar las características del texto argumentativo y el propósito comunicativo del manifiesto.",
                    "actividad": "Se lee en voz alta el comienzo del Manifiesto por el Agua de la UNESCO (adaptado). Se pregunta: '¿Quién habla en este texto? ¿A quién le habla? ¿Qué quiere lograr?' Se construye colectivamente la estructura básica del argumento: TESIS (lo que afirmamos) + ARGUMENTOS (por qué) + LLAMADO A LA ACCIÓN. El docente la escribe en el pizarrón y queda visible durante toda la actividad.",
                    "rol_docente": "Lee el texto modelo, guía el análisis y escribe la estructura argumentativa en el pizarrón.",
                    "recursos": "Manifiesto adaptado impreso (uno por estudiante), pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Escribir un párrafo argumentativo con tesis, argumentos y conclusión, y revisarlo con retroalimentación de un par.",
                    "actividad": "Cada estudiante escribe individualmente (10 min) un párrafo argumentativo sobre por qué debemos cuidar el agua, usando al menos un dato de las actividades anteriores (del experimento, la encuesta o las noticias). Luego intercambia con un compañero (5 min) que completa un protocolo de revisión: ¿se entiende la tesis? ¿hay al menos un argumento con evidencia? ¿hay un llamado a la acción? Con esa devolución, el autor revisa y mejora su párrafo (10 min). Los mejores párrafos serán seleccionados para el manifiesto colectivo.",
                    "rol_docente": "Apoya la escritura circulando por el aula, orienta a quienes tienen dificultades para formular la tesis y asegura el uso del protocolo de revisión.",
                    "recursos": "Hoja de escritura, protocolo de revisión impreso, apuntes y producciones previas del proyecto."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Socializar el manifiesto colectivo y comprometerse con una acción concreta.",
                    "actividad": "El docente lee en voz alta cuatro párrafos seleccionados (uno por grupo) construyendo el manifiesto colectivo. La clase vota el título y acuerda dónde lo publicarán (revista escolar, mural, acto de cierre del proyecto). Cada estudiante firma el manifiesto como compromiso simbólico y propone en una oración qué acción personal tomará en relación al cuidado del agua.",
                    "rol_docente": "Lee el manifiesto integrado, facilita la votación del título y formaliza el compromiso colectivo.",
                    "recursos": "Párrafos seleccionados compilados en una hoja, pizarrón para escribir el título votado."
                }
            ],
            "ce_codigo": "CE3",
            "ce_texto": "Produce un texto argumentativo colectivo sobre el cuidado del agua.",
            "contenido": "Texto argumentativo. Recursos retóricos. Propósito comunicativo.",
            "criterio_de_logro": "Escribe un párrafo argumentativo con tesis, argumentos y conclusión coherente.",
            "espacio": "Espacio Comunicación Artística",
            "unidad": "Lengua",
            "tramo": 4,
            "competencias_mcn": ["Comunicación", "Ciudadanía"]
        }
    },
    {
        "id": "c0a4833c-e89c-454b-9429-8c3ac09db131",
        "raw_content": {
            "titulo": "La Convención sobre los Derechos del Niño — lectura comentada",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "La Convención sobre los Derechos del Niño es el tratado internacional más ratificado de la historia. Conocerla es un derecho en sí mismo. Esta actividad usa la lectura comentada como método para que los estudiantes se apropien del documento de forma activa, vinculando cada artículo con situaciones reales de su vida cotidiana y desarrollando la competencia ciudadana (CE2) desde la experiencia directa.",
            "metodologia": "Lectura comentada",
            "metodologia_descripcion": "Se trabaja con fragmentos seleccionados de la CDN en lectura coral y comentada. Cada fragmento se pausa para que los grupos identifiquen: el derecho enunciado, un ejemplo de cumplimiento y uno de vulneración en contexto uruguayo.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Activar conocimientos previos sobre derechos del niño e introducir el contexto histórico de la CDN.",
                    "actividad": "Se pregunta: '¿Saben qué es la Convención sobre los Derechos del Niño? ¿Cuándo creen que se creó y por qué?' Breve lluvia de ideas. El docente explica brevemente el contexto de 1989 (fin de la Guerra Fría, situación de la infancia en el mundo) y muestra el número de países que la ratificaron (196). Se conecta con Uruguay: fue uno de los primeros en ratificarla en 1990.",
                    "rol_docente": "Modera la lluvia de ideas y presenta el contexto histórico de forma breve y accesible.",
                    "recursos": "Mapa mundial con países que ratificaron la CDN (proyectado o impreso), pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Identificar y explicar al menos cuatro derechos del niño vinculándolos con ejemplos concretos.",
                    "actividad": "Grupos de cuatro reciben cuatro artículos de la CDN (adaptados en lenguaje accesible): derecho a la identidad (art. 8), a la educación (art. 28), a la protección contra la violencia (art. 19) y a expresar su opinión (art. 12). Para cada artículo completan un cuadro: nombre del derecho / ¿qué significa en palabras propias? / ejemplo donde se cumple / ejemplo donde se vulnera. Luego de 15 minutos, cada grupo socializa su análisis ante la clase.",
                    "rol_docente": "Distribuye los artículos, orienta el análisis circulando por grupos y facilita la puesta en común.",
                    "recursos": "Artículos de la CDN adaptados impresos (uno por grupo), cuadro de análisis, cuadernos."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Sintetizar los derechos trabajados y reflexionar sobre el rol del Estado y la familia en su garantía.",
                    "actividad": "Se construye colectivamente en el pizarrón un cuadro de síntesis con los cuatro derechos trabajados. Se reflexiona: '¿Quién tiene la responsabilidad de garantizar estos derechos: el Estado, la familia, la escuela o todos?' Los estudiantes argumentan brevemente. Para cerrar, cada uno elige el derecho que considera más importante para su vida hoy y escribe una oración justificando su elección.",
                    "rol_docente": "Sistematiza el cuadro colectivo, modera la reflexión sobre responsabilidades y cierra con la consigna individual.",
                    "recursos": "Pizarrón, cuadernos."
                }
            ],
            "ce_codigo": "CE2",
            "ce_texto": "Conoce los derechos fundamentales de los niños y los vincula con la vida cotidiana.",
            "contenido": "Convención sobre los Derechos del Niño (CDN). Derechos civiles, sociales y culturales.",
            "criterio_de_logro": "Identifica y explica al menos cuatro derechos del niño con ejemplos propios.",
            "espacio": "Espacio Social y Ciudadano",
            "unidad": "Derecho y Ciudadanía",
            "tramo": 4,
            "competencias_mcn": ["Ciudadanía", "Comunicación"]
        }
    },
    {
        "id": "9f2bc5e9-1b96-4a4c-b77e-37362cad9651",
        "raw_content": {
            "titulo": "Historia de los derechos humanos — línea de tiempo",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Comprender los derechos humanos requiere conocer el proceso histórico por el que fueron conquistados. Esta actividad sitúa la Declaración Universal de 1948 en el contexto de la Segunda Guerra Mundial y permite que los estudiantes visualicen cómo los derechos no son dados sino construidos. La línea de tiempo como producto promueve el pensamiento histórico (CE4) y la organización espacial de la información.",
            "metodologia": "Investigación guiada con fuentes seleccionadas",
            "metodologia_descripcion": "Grupos investigan un hito histórico específico en fuentes provistas (no búsqueda libre en internet), construyen su segmento de la línea de tiempo y lo presentan al resto. La línea de tiempo final es un producto colaborativo del grupo-clase.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Identificar por qué surgió la necesidad de declarar derechos humanos universales.",
                    "actividad": "Se muestra una imagen del campo de concentración de Auschwitz y el texto del primer artículo de la DUDH: 'Todos los seres humanos nacen libres e iguales en dignidad y derechos.' Se pregunta: '¿Por qué creen que después de la guerra se escribió esto?' Breve intercambio. Se introduce el concepto: los derechos humanos son una respuesta histórica a las atrocidades de la Segunda Guerra Mundial.",
                    "rol_docente": "Presenta la imagen y el texto, modera el intercambio inicial y contextualiza históricamente en dos minutos.",
                    "recursos": "Imagen histórica impresa o proyectada, texto del artículo 1 de la DUDH."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Investigar un hito histórico de los derechos humanos y ubicarlo correctamente en la línea de tiempo grupal.",
                    "actividad": "Grupos de tres investigan uno de cinco hitos asignados: Revolución Francesa y Declaración de 1789 / Segunda Guerra Mundial y Holocausto / DUDH 1948 / Convención sobre los Derechos del Niño 1989 / Constitución uruguaya y derechos fundamentales. Con las fuentes provistas, completan una ficha: fecha, qué ocurrió, por qué fue importante, conexión con la vida hoy. Luego ubican su hito en la línea de tiempo mural que se despliega a lo largo de una pared del aula.",
                    "rol_docente": "Distribuye las fuentes y fichas, orienta la investigación y ayuda a ubicar los hitos en la escala temporal correcta.",
                    "recursos": "Fichas informativas por hito (adaptadas de fuentes primarias), ficha de síntesis impresa, línea de tiempo mural en papel kraft, marcadores, cinta adhesiva."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Presentar el hito investigado y reflexionar sobre la evolución histórica de los derechos.",
                    "actividad": "Cada grupo presenta su hito en 60 segundos parado frente a la línea de tiempo mural. Al finalizar, se observa la línea completa y se reflexiona: '¿Qué nos dice la distancia entre estos eventos? ¿Están seguros los derechos hoy?' Se menciona brevemente un caso actual de vulneración de derechos en el mundo para conectar historia y presente.",
                    "rol_docente": "Modera las presentaciones, guía la lectura de la línea de tiempo completa y lanza la reflexión final.",
                    "recursos": "Línea de tiempo mural completada, fichas de investigación."
                }
            ],
            "ce_codigo": "CE4",
            "ce_texto": "Ubica los hitos históricos más relevantes en la construcción de los derechos humanos.",
            "contenido": "Declaración Universal de los Derechos Humanos (1948). Constitución uruguaya. ONU.",
            "criterio_de_logro": "Elabora una línea de tiempo con al menos cinco hitos correctamente ubicados y descritos.",
            "espacio": "Espacio Social y Ciudadano",
            "unidad": "Historia",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento histórico", "Trabajo colaborativo"]
        }
    },
    {
        "id": "020b5f95-289e-449f-81bc-30a0a30c960f",
        "raw_content": {
            "titulo": "Fracciones en la cocina — recetas con proporciones",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Usar recetas reales como contexto matemático hace que las fracciones dejen de ser abstracciones y se conviertan en herramientas concretas. Calcular proporciones para ajustar porciones (CE1) implica equivalencia, suma y multiplicación de fracciones en un problema auténtico con respuesta verificable. La cocina, además, es un contexto culturalmente inclusivo y accesible para todos los estudiantes.",
            "metodologia": "Resolución de problemas en contexto real",
            "metodologia_descripcion": "Los grupos trabajan con una receta auténtica (alfajores, chipa, torta de naranja) y deben resolver problemas escalonados de proporcionalidad: calcular para la mitad, el doble y cinco veces las porciones originales. Los resultados se verifican entre grupos.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Identificar fracciones en el contexto de una receta y plantear el problema de ajuste de porciones.",
                    "actividad": "Se muestra una receta de alfajores para 12 unidades que incluye: 3/4 taza de harina, 1/2 taza de maicena, 1/3 taza de azúcar impalpable. Se pregunta: '¿Si quiero hacer alfajores para toda la escuela (120), cuánta harina necesito?' Los estudiantes intentan estimarlo en voz alta. Se registran las estrategias propuestas sin validarlas aún.",
                    "rol_docente": "Presenta la receta, plantea el problema de escala y registra las estrategias propuestas sin corregir.",
                    "recursos": "Receta de alfajores proyectada o impresa (una por grupo), pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Calcular las cantidades de una receta para la mitad, el doble y cinco veces las porciones usando operaciones con fracciones.",
                    "actividad": "Grupos de tres reciben una receta diferente (alfajores, chipa, torta de naranja). Deben completar una tabla con las cantidades ajustadas para: 1/2 porción, 2 porciones y 5 porciones. Para cada cálculo deben mostrar el proceso paso a paso (no solo el resultado). Luego intercambian la tabla con otro grupo que verifica los cálculos y señala errores con una explicación. Si hay desacuerdo, se discute y se corrige en conjunto.",
                    "rol_docente": "Circula apoyando la comprensión de la multiplicación de fracción por entero, verifica los procesos escritos y gestiona la revisión entre grupos.",
                    "recursos": "Recetas impresas, tabla de cálculo impresa, hojas de borrador, calculadoras para verificar."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Explicar la estrategia utilizada para ajustar proporciones y generalizar el procedimiento.",
                    "actividad": "Un integrante de cada grupo explica al resto cómo calculó una de las cantidades. El docente sintetiza en el pizarrón la regla general: para n veces las porciones, multiplico cada fracción por n. Se resuelve colectivamente el problema inicial (alfajores para 120): 3/4 × 10 = 7,5 tazas. Se conecta con el concepto de proporcionalidad directa.",
                    "rol_docente": "Modera las explicaciones, sintetiza la regla general y resuelve el problema inicial con la clase.",
                    "recursos": "Pizarrón, tablas completadas, recetas originales."
                }
            ],
            "ce_codigo": "CE1",
            "ce_texto": "Opera con fracciones ajustando cantidades de recetas para distintas porciones.",
            "contenido": "Fracciones: equivalencia, suma, resta y multiplicación por entero. Proporcionalidad.",
            "criterio_de_logro": "Calcula correctamente las cantidades de una receta para el doble y la mitad de porciones.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Matemática",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento matemático", "Resolución de problemas"]
        }
    },
    {
        "id": "d0338211-0782-42d1-b0c3-1a84a72ec7da",
        "raw_content": {
            "titulo": "Decimales en el supermercado",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Resolver situaciones de compra-venta con números decimales en el contexto del supermercado (CE2) conecta la matemática con la vida cotidiana de los estudiantes y sus familias. El uso de folletos reales de supermercados uruguayos hace que los problemas sean auténticos y verificables, y desarrolla además habilidades de estimación y control del cálculo que tienen aplicación directa en la vida.",
            "metodologia": "Simulación en contexto real",
            "metodologia_descripcion": "La clase simula un escenario de compra con folletos reales de supermercados (Tienda Inglesa, Disco, Ta-Ta). Los estudiantes 'compran' dentro de un presupuesto dado, calculan el total, el vuelto y verifican si sus estimaciones fueron correctas.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Revisar la lectura de precios decimales y la estimación de totales.",
                    "actividad": "Se muestran tres precios reales de un folleto de supermercado: $89,90 / $145,50 / $32,99. Se pregunta: '¿Cuánto costaría comprar los tres? Estímenlo sin hacer cuentas exactas.' Los estudiantes dan estimaciones en voz alta y explican cómo las hicieron (redondeo al diez más cercano, al peso más cercano). Se discute: ¿cuándo conviene estimar y cuándo necesitamos el número exacto?",
                    "rol_docente": "Presenta los precios, recoge estimaciones y modera la discusión sobre cuándo estimar y cuándo calcular exacto.",
                    "recursos": "Folleto de supermercado proyectado o impreso, pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Resolver situaciones de compra con vuelto usando estimación y cálculo exacto con decimales.",
                    "actividad": "Grupos de tres reciben: un folleto de supermercado, una 'lista de compras' con 5 productos a comprar y un 'billete' de $500. Deben: (1) estimar el total antes de calcular, (2) calcular el precio exacto de cada producto, (3) sumar el total, (4) calcular el vuelto. Si el total supera $500, deben decidir qué producto sacar de la lista y justificarlo. Luego intercambian con otro grupo para verificar los cálculos.",
                    "rol_docente": "Distribuye materiales, supervisa el proceso de estimación previa y apoya con el algoritmo de suma de decimales cuando hay dudas.",
                    "recursos": "Folletos de supermercado impresos, listas de compra por grupo, billetes de juguete o fichas de $500, calculadoras para verificación."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Comparar estimación y resultado exacto y reflexionar sobre la utilidad de cada uno.",
                    "actividad": "Cada grupo comparte su estimación original y su resultado exacto. Se construye en el pizarrón una tabla comparativa: estimación / exacto / diferencia. Se reflexiona: '¿Cuándo fue útil estimar? ¿Alguien se pasó del presupuesto?' Se plantea el concepto de margen de error. Para cerrar, se plantea un problema individual: '¿Cuántos alfajores de $28,50 puedo comprar con $200?'",
                    "rol_docente": "Sistematiza la tabla comparativa, guía la reflexión y plantea el problema individual de cierre.",
                    "recursos": "Pizarrón, cuadernos para el problema individual."
                }
            ],
            "ce_codigo": "CE2",
            "ce_texto": "Resuelve situaciones de compra-venta con números decimales.",
            "contenido": "Números decimales: operaciones y comparación. Estimación. Redondeo.",
            "criterio_de_logro": "Resuelve correctamente situaciones de compra con vuelto usando estimación y cálculo exacto.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Matemática",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento matemático", "Resolución de problemas"]
        }
    },
    {
        "id": "928e9f29-6ae8-4671-9e6e-cd3660055903",
        "raw_content": {
            "titulo": "Escalas en mapas de Montevideo",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Interpretar escalas cartográficas es una competencia matemática (CE5) con aplicación directa en geografía, arquitectura y vida cotidiana. Usar el mapa real de Montevideo hace el contexto auténtico y cercano: los estudiantes calculan distancias entre lugares que conocen (su barrio, el estadio Centenario, el Palacio Legislativo). La proporcionalidad matemática se hace visible y útil.",
            "metodologia": "Trabajo con material cartográfico real",
            "metodologia_descripcion": "Cada grupo trabaja con un mapa impreso de Montevideo con escala 1:30.000. Miden con regla, aplican la razón de escala y calculan distancias reales. Los resultados se contrastan con Google Maps al final para verificar.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Comprender qué significa una escala y cómo leerla en un mapa.",
                    "actividad": "Se muestra el mapa de Montevideo y se señala la barra de escala '1:30.000'. Se pregunta: '¿Qué significa este número? Si mido 1 cm en el mapa, ¿cuánto es en la realidad?' Los estudiantes razonan en voz alta. El docente formaliza: 1 cm en el mapa = 30.000 cm = 300 m en la realidad. Se hace un ejemplo simple: si mido 3 cm entre dos puntos, ¿cuántos metros reales son?",
                    "rol_docente": "Presenta el mapa, lanza la pregunta sobre la escala y formaliza el concepto con el ejemplo.",
                    "recursos": "Mapa de Montevideo impreso (uno por grupo, escala 1:30.000), reglas, pizarrón."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Calcular correctamente al menos tres distancias reales a partir de la escala del mapa.",
                    "actividad": "Grupos de tres reciben una hoja con cinco recorridos a calcular (ej. distancia entre Plaza Independencia y el Estadio Centenario / entre la Rambla y el Mercado del Puerto / entre dos barrios dados). Para cada recorrido: (1) marcan los dos puntos en el mapa, (2) miden la distancia en cm con regla, (3) aplican la escala para calcular la distancia real en metros y kilómetros, (4) registran el proceso completo. Si terminan antes, diseñan ellos un recorrido propio y calculan su distancia.",
                    "rol_docente": "Distribuye los mapas y la hoja de recorridos, apoya el uso de la regla y la conversión de unidades.",
                    "recursos": "Mapa impreso, hoja de recorridos, reglas, calculadoras, hojas de borrador."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Verificar los resultados y reflexionar sobre la utilidad de las escalas en la vida real.",
                    "actividad": "Se proyecta Google Maps con los mismos recorridos y se miden las distancias reales. Los grupos comparan sus cálculos con el resultado real y calculan el porcentaje de error. Se reflexiona: '¿Por qué hay diferencia?' (la escala es una aproximación, la regla tiene margen de error). Se conecta con usos reales: arquitectos, ingenieros, GPS. Cada estudiante escribe en su cuaderno la fórmula de escala y un ejemplo propio.",
                    "rol_docente": "Proyecta Google Maps para verificación, guía el análisis del error y conecta con aplicaciones reales.",
                    "recursos": "Proyector con Google Maps, cuadernos."
                }
            ],
            "ce_codigo": "CE5",
            "ce_texto": "Interpreta y usa escalas en mapas para calcular distancias reales.",
            "contenido": "Escala: razón entre medida representada y medida real. Conversión de unidades.",
            "criterio_de_logro": "Calcula correctamente al menos tres distancias reales a partir de la escala del mapa.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Matemática",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento matemático", "Espacialidad"]
        }
    },
    {
        "id": "886efcc3-97d9-4511-8d43-358e9a08f7b0",
        "raw_content": {
            "titulo": "Visita al arroyo Miguelete — registro de campo",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "El arroyo Miguelete es uno de los cursos de agua más contaminados de Uruguay y atraviesa barrios populares de Montevideo. Visitarlo y observarlo con instrumentos científicos conecta el conocimiento sobre el ciclo del agua con una realidad ambiental urgente y local (CE3). Esta salida de campo cierra el proyecto integrador del agua generando una experiencia directa que ningún texto puede reemplazar.",
            "metodologia": "Salida de campo científica",
            "metodologia_descripcion": "Los estudiantes trabajan con una ficha de campo estructurada que guía la observación sistemática. Incluye registro escrito, fotográfico (si hay tablets) y una entrevista breve a un referente ambiental o vecino. La información recogida se analiza en clase al día siguiente.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Preparar la salida de campo identificando qué observar y cómo registrarlo.",
                    "actividad": "Antes de salir al arroyo (esta parte es en el aula), se revisa la ficha de campo: secciones de color del agua, olor, presencia de residuos sólidos, fauna visible, vegetación de la orilla, uso humano del espacio. Se explica que un científico no registra solo lo que le parece importante sino todo lo que observa. Se asignan roles en cada grupo: observador de agua, observador de fauna/flora, observador de residuos, fotógrafo/dibujante.",
                    "rol_docente": "Explica la ficha de campo, asigna roles y da instrucciones de seguridad para la salida.",
                    "recursos": "Fichas de campo impresas (una por estudiante), lápices, tablets (si disponibles), ropa adecuada."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Completar la ficha de campo con observaciones sistemáticas e identificar indicadores de contaminación.",
                    "actividad": "En el arroyo, los grupos observan y registran durante 20 minutos con sus fichas. Cada observador registra su área específica. Si hay un referente ambiental de la IMM o una ONG (coordinado previamente), los grupos le hacen tres preguntas preparadas en el aula: ¿cuál es la causa principal de contaminación? ¿qué mejoras ha habido? ¿qué pueden hacer los vecinos? Los últimos 5 minutos son para completar impresiones generales y preguntas que surgieron.",
                    "rol_docente": "Acompaña la observación en campo, asegura la seguridad, facilita el contacto con el referente y estimula el registro riguroso.",
                    "recursos": "Fichas de campo, lápices, tablets para fotos, referente ambiental (coordinado previamente)."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Formular conclusiones fundamentadas sobre el estado del arroyo a partir de las observaciones registradas.",
                    "actividad": "De regreso al aula (o al día siguiente), cada grupo analiza su ficha y redacta tres conclusiones: una descripción del estado actual del arroyo, una hipótesis sobre sus causas y una propuesta de acción. Las conclusiones se comparten en plenaria y se conectan con el ciclo del agua: ¿cómo afecta la contaminación del Miguelete al ciclo? Las fichas completas se incluyen en el portafolio del proyecto integrador.",
                    "rol_docente": "Facilita el análisis de las fichas, guía la redacción de conclusiones y conecta con el conocimiento previo del ciclo del agua.",
                    "recursos": "Fichas de campo completadas, cuadernos, pizarrón para la plenaria."
                }
            ],
            "ce_codigo": "CE3",
            "ce_texto": "Observa el estado real de un curso de agua urbano e identifica indicadores de contaminación.",
            "contenido": "Indicadores de calidad del agua. Biodiversidad acuática. Registro científico de campo.",
            "criterio_de_logro": "Completa una ficha de campo con observaciones y conclusiones fundamentadas.",
            "espacio": "Espacio Científico-Matemático",
            "unidad": "Ciencias de la Naturaleza",
            "tramo": 4,
            "competencias_mcn": ["Pensamiento científico", "Ciudadanía"]
        }
    },
    {
        "id": "8d4b6d10-c795-42a0-b02e-421e10825519",
        "raw_content": {
            "titulo": "Juego de roles: el parlamento de los derechos",
            "grupo": "Grupo de 5.to grado (Colegio 01)",
            "justificacion": "Simular el proceso parlamentario de elaboración de una ley es la forma más efectiva de que los estudiantes comprendan la democracia representativa desde adentro. Esta actividad desarrolla la competencia ciudadana (CE2) exigiendo argumentación fundamentada, escucha activa y negociación. El tema de la ley simulada (derechos de los niños en la era digital) hace el contenido relevante e inmediato para el grupo.",
            "metodologia": "Simulación parlamentaria",
            "metodologia_descripcion": "La clase se organiza en tres bloques: legisladores (dos partidos con posiciones diferentes), ciudadanos que presentan peticiones y una prensa que registra el debate. Se sigue un protocolo parlamentario simplificado con tiempos fijos para mociones, réplicas y votación.",
            "momentos": [
                {
                    "momento": "Inicio",
                    "duracion": "5 min",
                    "meta_aprendizaje": "Comprender el funcionamiento del parlamento uruguayo y los roles en el proceso legislativo.",
                    "actividad": "Se presenta el escenario: 'El Parlamento de 5.to grado va a debatir y votar un proyecto de ley: La Ley de Derechos Digitales de los Niños. Esta ley propone que ningún niño menor de 13 años pueda tener redes sociales sin supervisión parental.' Se explican los roles asignados: Partido A (a favor), Partido B (con modificaciones), Ciudadanos afectados (niños de 5.to grado), Prensa. Cada estudiante recibe su tarjeta de rol con tres argumentos para usar.",
                    "rol_docente": "Presenta el escenario y la ley simulada, explica los roles y distribuye las tarjetas de rol.",
                    "recursos": "Tarjetas de rol impresas, protocolo parlamentario simplificado impreso, cartel con el proyecto de ley."
                },
                {
                    "momento": "Desarrollo",
                    "duracion": "25 min",
                    "meta_aprendizaje": "Participar activamente en el rol asignado argumentando con fundamentos su posición.",
                    "actividad": "El debate se desarrolla en tres rondas de 7 minutos: (1) cada partido presenta su posición (3 min cada uno), (2) los ciudadanos presentan tres peticiones concretas (2 min cada petición), (3) réplicas y negociación: el Partido A y B deben acordar una versión modificada de la ley. La prensa toma notas y al final presenta un 'resumen de la sesión' de 60 segundos. Finalmente, se vota la ley modificada a mano alzada.",
                    "rol_docente": "Actúa como Presidente de la Cámara: da la palabra, controla los tiempos, evita que el debate se salga del tema y fomenta el uso de los argumentos preparados.",
                    "recursos": "Tarjetas de rol, protocolo impreso, timer visible, pizarrón para registrar las modificaciones a la ley."
                },
                {
                    "momento": "Cierre",
                    "duracion": "10 min",
                    "meta_aprendizaje": "Reflexionar sobre el proceso democrático y el rol del ciudadano en la elaboración de normas.",
                    "actividad": "Saliendo de los roles, el docente guía una reflexión metacognitiva: '¿Qué fue lo más difícil de defender su posición? ¿Cambiaron de opinión en algún momento? ¿Creen que el resultado fue justo?' Se conecta con el sistema real: cómo se hace una ley en Uruguay, qué rol tienen los ciudadanos fuera del parlamento (peticiones, movilizaciones, medios). Cada estudiante escribe en su cuaderno qué aprendió sobre la democracia hoy.",
                    "rol_docente": "Facilita la salida de los roles, guía la reflexión metacognitiva y conecta la simulación con el proceso real.",
                    "recursos": "Cuadernos, pizarrón con la ley modificada visible."
                }
            ],
            "ce_codigo": "CE2",
            "ce_texto": "Vivencia el proceso democrático de elaboración de normas mediante simulación.",
            "contenido": "Democracia representativa. Elaboración de leyes. Roles: legisladores, ciudadanos, prensa.",
            "criterio_de_logro": "Participa activamente en el rol asignado argumentando con fundamentos su posición.",
            "espacio": "Espacio Social y Ciudadano",
            "unidad": "Derecho y Ciudadanía",
            "tramo": 4,
            "competencias_mcn": ["Ciudadanía", "Comunicación", "Trabajo colaborativo"]
        }
    },
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated = 0
    for activity in ACTIVITIES:
        raw_json = json.dumps(activity["raw_content"], ensure_ascii=False)
        cursor.execute(
            "UPDATE activities SET raw_content = ? WHERE id = ? AND (raw_content IS NULL OR raw_content = '')",
            (raw_json, activity["id"])
        )
        if cursor.rowcount > 0:
            updated += 1
            print(f"✓ {activity['raw_content']['titulo'][:60]}")
        else:
            print(f"✗ Skipped (already has content or ID not found): {activity['id'][:8]}...")

    conn.commit()
    conn.close()
    print(f"\n{updated}/{len(ACTIVITIES)} actividades actualizadas.")


if __name__ == "__main__":
    main()

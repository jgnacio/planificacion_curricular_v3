# Ingeniería de Requisitos Funcionales

## Sistema de Planificación de Aprendizaje Personalizado - EBI ANEP

---

## CONTEXTO DEL SISTEMA

Desarrollar una aplicación web/móvil para educadores que facilite la creación de planificaciones de aprendizaje personalizadas, basadas en el Programa de Educación Básica Integral de ANEP (Uruguay), adaptando contenidos a las singularidades de cada alumno y facilitando el diseño didáctico de las clases.

---

## REQUISITOS FUNCIONALES PRINCIPALES

### RF-001: Gestión de Planificaciones

**Descripción:** El sistema debe permitir crear, editar, visualizar y eliminar planificaciones de aprendizaje.

**Criterios de aceptación:**

* La educadora puede crear una nueva planificación seleccionando el nivel educativo (Inicial Nivel 3 a 2° o 3° a 6°)
* Puede duplicar planificaciones existentes para reutilizar estructuras
* Puede archivar planificaciones completadas
* Puede exportar planificaciones en formato PDF o imprimible
* Cada planificación incluye metadatos: fecha de creación, período de implementación, nivel/grado, autor(a)
* Permite asignar etiquetas personalizadas para organizar planificaciones (por proyecto, trimestre, tema integrador, etc.)

---

### RF-002: Estructura de Espacios Curriculares (Basado en documentación ANEP)

**Descripción:** El sistema debe extraer y construir automáticamente la estructura de espacios curriculares a partir de los documentos PDF oficiales de ANEP que el usuario proporcione.

#### **Criterios de aceptación:**

#### **1. Carga de documentación oficial**

* La educadora puede subir uno o varios PDFs de los programas de ANEP (disponibles en [https://www.anep.edu.uy/documentos-curriculares/ebi/programas-ebi-2023-2023](https://www.anep.edu.uy/documentos-curriculares/ebi/programas-ebi-2023-2023))
* El sistema acepta PDFs individuales por unidad curricular o compilaciones completas por ciclo
* Muestra el progreso de procesamiento de cada documento
* Almacena los documentos procesados para consulta futura
* Permite previsualizar el PDF antes de procesarlo

#### **2. Procesamiento automático de estructura**

El sistema debe extraer automáticamente:

**A. Información de ciclos y tramos:**

* Detecta si el documento corresponde a:
  * **1er Ciclo:** Tramo 1 (Nivel 3, 4, 5 años) + Tramo 2 (1° y 2°)
  * **2do Ciclo:** Tramo 3 (3° y 4°) + Tramo 4 (5° y 6°)
  * **3er Ciclo:** Tramo 5 (7° y 8°) + Tramo 6 (9°)
* Identifica automáticamente el grado específico dentro de cada tramo

**B. Componentes curriculares:**

* **Alfabetizaciones fundamentales**
* **Técnico-tecnológico**
* **Autonomía curricular**

**C. Espacios curriculares:**
Según el documento oficial de ANEP, extrae los siguientes espacios:

* Espacio Científico Matemático
* Espacio de Comunicación
* Espacio Ciencias Sociales y Humanidades
* Espacio Creativo-Artístico
* Espacio de Desarrollo Personal y Conciencia Corporal
* Espacio Técnico Tecnológico
* Espacio de Autonomía Curricular

**D. Unidades curriculares por espacio:**
Por ejemplo, para el Espacio Científico Matemático:

* Matemática
* Física y Química
* Ciencias Biológicas
* Ciencias de la Tierra y el Espacio

Y para cada espacio, todas las unidades correspondientes según el programa oficial.

**E. Contenidos estructurantes:**

* Identifica los contenidos estructurantes de cada unidad curricular
* Extrae los contenidos específicos asociados
* Mantiene la jerarquía: Contenido Estructurante → Contenidos Específicos

**F. Competencias específicas:**

* Extrae las competencias específicas definidas para cada unidad curricular
* Las vincula con procesos cognitivos mencionados en el documento
* Las asocia con las 10 competencias generales del Marco Curricular Nacional

**G. Criterios de logro:**

* Extrae los criterios de logro por tramo y por grado
* Los asocia correctamente a cada contenido
* Identifica indicadores de desempeño observable

**H. Orientaciones metodológicas:**

* Extrae sugerencias metodológicas del documento oficial
* Identifica orientaciones para la evaluación
* Captura ejemplos y actividades sugeridas

#### **3. Organización de la información**

* El sistema crea una base de datos estructurada con toda la información extraída
* Permite navegación jerárquica: Ciclo → Tramo → Componente → Espacio → Unidad Curricular → Contenidos → Criterios
* Cada elemento tiene metadatos (fuente, página del PDF, fecha de documento, versión)
* Mantiene referencias al documento original para consulta completa

#### **4. Validación y corrección**

* El sistema muestra un resumen de lo extraído para revisión de la educadora
* Permite editar manualmente cualquier elemento mal interpretado
* Marca elementos que requieren revisión humana (ej: tablas complejas, imágenes)
* Permite agregar notas o aclaraciones a cualquier elemento
* Registra el historial de modificaciones manuales

#### **5. Actualización de documentos**

* Detecta si se sube una versión actualizada de un documento ya procesado
* Compara versiones y muestra cambios detectados (contenidos agregados, modificados o eliminados)
* Permite mantener ambas versiones o actualizar a la nueva
* Notifica a educadoras que tienen planificaciones basadas en versión anterior
* Sugiere revisar planificaciones afectadas por cambios

#### **6. Búsqueda y filtrado**

* Buscador inteligente por palabras clave en todo el contenido extraído
* Filtros por:
  * Nivel/grado específico
  * Espacio curricular
  * Unidad curricular
  * Tipo de contenido (estructurante vs específico)
  * Competencia específica
  * Componente curricular
* Búsqueda avanzada con operadores booleanos (Y, O, NO)

#### **7. Interfaz de usuario**

* Vista de árbol expandible con toda la estructura curricular
* Tarjetas visuales por espacio curricular con colores distintivos (basados en la identidad visual de ANEP)
* Acceso rápido a "Favoritos" (unidades más usadas)
* Vista de "Mi nivel" que filtra automáticamente por el grado seleccionado
* Modo de lectura del documento original PDF integrado

#### **8. Compatibilidad con formatos**

* Procesa PDFs con diferentes estructuras (por unidad curricular, compilaciones por ciclo)
* Maneja documentos con orientaciones transversales (Derechos Humanos, Educación en Sexualidad, Habilidades Socioemocionales, Autonomía Curricular)
* Extrae información de tablas, listas y párrafos descriptivos
* Interpreta diagramas y esquemas cuando sea posible

#### **9. Referencias cruzadas**

* Vincula automáticamente contenidos que aparecen en múltiples espacios
* Identifica conexiones interdisciplinarias mencionadas en los documentos
* Sugiere abordajes integrados cuando detecta temáticas comunes
* Marca contenidos que pueden trabajarse en proyectos transversales

#### **10. Generación de reportes**

* Exporta la estructura extraída en formatos:
  * JSON (para integración con otros sistemas)
  * CSV (para análisis en hojas de cálculo)
  * Documento legible (PDF/Word) con la estructura organizada
* Genera glosario de términos específicos del programa
* Crea mapas conceptuales automáticos de la estructura curricular

---

### RF-003: Gestión de Unidades Curriculares

**Descripción:** Dentro de cada espacio, el sistema debe permitir trabajar con múltiples unidades curriculares extraídas de la documentación oficial.

**Criterios de aceptación:**

* Cada espacio contiene las unidades curriculares definidas por ANEP para ese nivel (extraídas automáticamente)
* La educadora puede seleccionar una o varias unidades curriculares por espacio
* El sistema muestra las unidades curriculares con su descripción oficial
* Se pueden agregar unidades curriculares personalizadas si es necesario (marcadas claramente como "no oficiales")
* Cada unidad curricular muestra:
  * Descripción general
  * Competencias específicas asociadas
  * Contenidos estructurantes
  * Criterios de logro por grado
  * Orientaciones metodológicas
* Cada unidad curricular se puede vincular con contenidos específicos
* Permite marcar unidades como "prioritarias" o "en desarrollo"

---

### RF-004: Definición de Contenidos

**Descripción:** El sistema debe permitir especificar los contenidos a trabajar dentro de cada unidad curricular, utilizando el banco de contenidos extraído de los documentos oficiales.

**Criterios de aceptación:**

* El sistema ofrece un banco de contenidos predefinidos según el programa de ANEP (extraídos automáticamente)
* Diferencia claramente entre contenidos estructurantes y contenidos específicos
* La educadora puede buscar contenidos por palabra clave
* Se pueden agregar contenidos personalizados con descripción libre (marcados como "adaptados")
* Los contenidos pueden vincularse a múltiples unidades curriculares
* Se puede establecer una secuencia temporal de contenidos (orden didáctico)
* Los contenidos incluyen:
  * Campo de descripción detallada (del documento oficial)
  * Relación con contenidos estructurantes
  * Competencias específicas que desarrollan
  * Sugerencias metodológicas asociadas
* Permite anotar el nivel de profundidad con que se abordará cada contenido
* Muestra advertencias si se omiten contenidos estructurantes importantes

---

### RF-005: Establecimiento de Criterios de Logro

**Descripción:** Para cada contenido, el sistema debe permitir definir criterios de logro observables y medibles, basados en los documentos oficiales y personalizables.

**Criterios de aceptación:**

* Se pueden agregar múltiples criterios de logro por contenido
* El sistema sugiere criterios de logro oficiales extraídos del programa según el contenido seleccionado
* Los criterios son redactables en texto libre
* Los criterios oficiales se diferencian visualmente de los personalizados
* Se pueden marcar criterios como "alcanzados/en proceso/no alcanzados" para cada alumno
* Los criterios se pueden categorizar por nivel de complejidad (inicial, en desarrollo, consolidado)
* Permite relacionar criterios de logro con:
  * Contenidos específicos
  * Competencias específicas
  * Progresiones de aprendizaje del MCN
* Se pueden importar criterios de planificaciones anteriores
* Permite agregar evidencias de aprendizaje esperadas para cada criterio

---

### RF-006: Definición de Metas de Aprendizaje

**Descripción:** El sistema debe permitir establecer metas de aprendizaje para la planificación, alineadas con el Marco Curricular Nacional.

**Criterios de aceptación:**

* Se pueden definir metas generales para toda la planificación
* Se pueden definir metas específicas por espacio curricular
* Se pueden definir metas por unidad curricular
* Las metas incluyen:
  * Descripción clara y concisa
  * Tiempo estimado de logro
  * Relación con competencias generales del MCN
  * Relación con perfiles de tramo
* Se pueden vincular metas con contenidos y criterios de logro específicos
* Las metas son editables durante el proceso de implementación
* El sistema sugiere metas tipo según el nivel y los contenidos seleccionados
* Permite establecer indicadores de seguimiento para cada meta
* Se pueden priorizar metas (esenciales, importantes, complementarias)
* Muestra el progreso hacia cada meta de forma visual (%)

---

### RF-007: Gestión de Perfiles de Alumnos

**Descripción:** El sistema debe permitir crear y gestionar perfiles individuales de alumnos con sus singularidades.

**Criterios de aceptación:**

* Se puede crear un perfil por alumno con datos básicos:
  * Nombre completo
  * Edad/fecha de nacimiento
  * Nivel y grado actual
  * Fotografía (opcional)
* Cada perfil incluye sección de "singularidades" con categorías:
  * Estilos de aprendizaje (visual, auditivo, kinestésico, lectoescritor)
  * Necesidades educativas específicas
  * Fortalezas identificadas
  * Áreas que requieren apoyo
  * Intereses personales
  * Contexto familiar relevante
* Se pueden agregar notas y observaciones a cada perfil con fecha
* Los perfiles se pueden vincular a planificaciones específicas
* Se puede crear un grupo/clase y asignar múltiples alumnos
* Permite importar listados de alumnos desde archivos CSV o Excel
* Mantiene historial de observaciones y evolución del alumno
* Protección de datos personales con niveles de acceso
* Permite agregar documentación de apoyo (informes, adecuaciones curriculares oficiales)

---

### RF-008: Personalización por Alumno

**Descripción:** El sistema debe permitir adaptar la planificación a cada alumno según sus singularidades.

**Criterios de aceptación:**

* Desde una planificación base, se pueden crear variantes personalizadas por alumno
* Se pueden ajustar para cada alumno:
  * Contenidos (ampliar, reducir, modificar secuencia)
  * Criterios de logro (adaptar nivel de exigencia)
  * Metas de aprendizaje (personalizar tiempos y alcances)
  * Estrategias didácticas diferenciadas
* Se pueden agregar estrategias didácticas diferenciadas específicas:
  * Apoyos visuales
  * Material manipulativo
  * Tiempos extendidos
  * Evaluaciones alternativas
  * Agrupamientos específicos
* Se pueden establecer adecuaciones curriculares de acceso o de contenido
* El sistema resalta visualmente qué elementos han sido personalizados (ej: badge, color diferente)
* Permite crear diferentes niveles de desafío para el mismo contenido
* Genera vista comparativa: planificación base vs. planificación personalizada
* Sugiere adaptaciones basadas en las singularidades registradas del alumno
* Permite documentar el fundamento de cada adaptación realizada

---

### RF-009: Asistente de Planificación de Clases

**Descripción:** El sistema debe proporcionar sugerencias y estructura para facilitar el pensamiento didáctico de la clase.

**Criterios de aceptación:**

* A partir de la planificación, el sistema sugiere actividades concretas basadas en:
  * Contenidos seleccionados
  * Criterios de logro establecidos
  * Singularidades de los alumnos
  * Recursos disponibles
* Propone secuencias didácticas completas con estructura:
  * Inicio (motivación, activación de conocimientos previos, presentación del objetivo)
  * Desarrollo (exploración, sistematización, práctica guiada, práctica autónoma)
  * Cierre (síntesis, metacognición, evaluación formativa)
* Sugiere recursos y materiales según:
  * El contenido a trabajar
  * Las singularidades de los alumnos
  * El nivel educativo
  * Recursos digitales y analógicos
* Ofrece estrategias de evaluación formativa:
  * Técnicas de observación
  * Instrumentos de registro
  * Preguntas orientadoras
  * Rúbricas y listas de cotejo
* Genera propuestas de actividades con diferentes niveles de andamiaje
* Sugiere agrupamientos según objetivos (individual, parejas, pequeños grupos, gran grupo)
* Permite guardar y reutilizar actividades exitosas en una biblioteca personal
* Ofrece banco de consignas y preguntas según el tipo de contenido
* Integra orientaciones metodológicas del programa oficial
* Sugiere momentos para el trabajo interdisciplinario
* Propone variantes de actividades según estilos de aprendizaje
* Incluye sugerencias para la gestión del tiempo en el aula

---

### RF-010: Seguimiento y Registro

**Descripción:** El sistema debe permitir registrar el avance de cada alumno respecto a la planificación.

**Criterios de aceptación:**

* Se puede marcar el progreso de cada alumno en criterios de logro con estados:
  * No trabajado
  * En proceso inicial
  * En proceso avanzado
  * Alcanzado
  * Superado
* Se pueden agregar observaciones y evidencias de aprendizaje:
  * Notas textuales con fecha
  * Fotografías de producciones
  * Grabaciones de audio/video (opcional)
  * Documentos adjuntos
* Se genera un panel visual del avance:
  * Vista general del grupo
  * Vista individual por alumno
  * Gráficos de progreso por espacio curricular
  * Indicadores de logro por competencias
* Se pueden exportar reportes de seguimiento en formatos:
  * PDF para familias
  * Excel para análisis estadístico
  * Informe narrativo por alumno
* El sistema alerta sobre:
  * Alumnos que requieren mayor apoyo
  * Criterios de logro con bajo porcentaje de alcance grupal
  * Contenidos que requieren replanificación
  * Metas en riesgo de no cumplirse en tiempo
* Permite comparar avances entre diferentes períodos
* Genera informes de evolución individual y grupal
* Incluye sección de autoevaluación del alumno (según edad)
* Permite registrar intervenciones específicas realizadas

---

### RF-011: Base de Conocimiento del Programa ANEP

**Descripción:** El sistema debe integrar y mantener actualizada la información del programa oficial de Educación Básica Integral de ANEP.

**Criterios de aceptación:**

* Contiene la estructura completa del programa para Inicial Nivel 3 a 2° (extraída de PDFs oficiales)
* Contiene la estructura completa del programa para 3° a 6° (extraída de PDFs oficiales)
* Los contenidos están organizados y etiquetados según el documento oficial
* Incluye todos los componentes del sistema curricular:
  * Marco Curricular Nacional (competencias generales)
  * Progresiones de Aprendizaje
  * Plan de Educación Básica Integrada
  * Programas por espacio y unidad curricular
  * Orientaciones transversales
* Se actualiza cuando hay cambios en el programa oficial mediante carga de nuevos PDFs
* Permite búsqueda y filtrado por:
  * Nivel educativo
  * Espacio curricular
  * Unidad curricular
  * Competencia
  * Palabra clave
* Mantiene histórico de versiones anteriores
* Incluye glosario de términos del programa
* Permite acceso directo al documento PDF oficial completo
* Muestra fecha de última actualización de cada documento

---

### RF-012: Colaboración y Compartir

**Descripción:** El sistema debe permitir compartir planificaciones entre educadores respetando la privacidad de los datos de alumnos.

**Criterios de aceptación:**

* Se pueden compartir planificaciones base (sin datos personales de alumnos) con:
  * Otros docentes del centro educativo
  * Docentes de otros centros (mediante código de acceso)
  * La comunidad general de usuarios (modo público)
* Se puede crear una biblioteca de planificaciones del centro educativo:
  * Organizadas por nivel, espacio y tema
  * Con sistema de etiquetado colaborativo
  * Con control de versiones
* Se pueden agregar comentarios y sugerencias a planificaciones compartidas
* Se controlan permisos de:
  * Solo lectura
  * Lectura y comentarios
  * Edición colaborativa
* Sistema de calificación y reseñas de planificaciones compartidas
* Permite clonar planificaciones compartidas para adaptarlas
* Notificaciones cuando alguien comenta o mejora una planificación compartida
* Estadísticas de uso de planificaciones compartidas
* Filtros para encontrar planificaciones por:
  * Nivel educativo
  * Espacio curricular
  * Metodología utilizada
  * Autor
  * Valoración de la comunidad

---

### RF-013: Integración Interdisciplinaria

**Descripción:** El sistema debe facilitar la creación de propuestas integradas que conecten múltiples espacios curriculares.

**Criterios de aceptación:**

* Permite crear "Proyectos Integrados" que vinculan:
  * Contenidos de múltiples espacios curriculares
  * Criterios de logro de diferentes unidades
  * Metas transversales
* Sugiere automáticamente conexiones posibles entre espacios curriculares basándose en:
  * Contenidos con temáticas comunes
  * Competencias transversales
  * Referencias cruzadas del programa oficial
* Muestra mapa visual de las conexiones interdisciplinarias del proyecto
* Permite planificar secuencias didácticas integradas
* Genera cronograma coordinado entre diferentes espacios
* Identifica las competencias generales del MCN que se desarrollan en el proyecto
* Facilita la co-planificación entre docentes de diferentes especialidades
* Incluye plantillas de proyectos integrados exitosos

---

### RF-014: Gestión de Recursos Didácticos

**Descripción:** El sistema debe permitir gestionar y vincular recursos didácticos a las planificaciones.

**Criterios de aceptación:**

* Biblioteca de recursos donde se pueden almacenar:
  * Materiales didácticos (fichas, guías, presentaciones)
  * Recursos digitales (enlaces, videos, aplicaciones)
  * Instrumentos de evaluación (rúbricas, listas de cotejo)
  * Bibliografía y sitios web recomendados
* Cada recurso se puede etiquetar con:
  * Espacio curricular
  * Unidad curricular
  * Contenidos relacionados
  * Nivel educativo
  * Tipo de recurso
* Permite vincular recursos directamente a actividades de la planificación
* Sistema de favoritos y colecciones personales
* Posibilidad de compartir recursos con otros educadores
* Previsualizador integrado de diferentes formatos de archivo
* Permite agregar notas de uso y recomendaciones para cada recurso

---

### RF-015: Calendario y Temporalización

**Descripción:** El sistema debe ayudar a organizar la implementación temporal de la planificación.

**Criterios de aceptación:**

* Vista de calendario donde se pueden ubicar:
  * Contenidos a trabajar
  * Actividades planificadas
  * Evaluaciones
  * Proyectos especiales
* Permite establecer períodos didácticos (trimestres, bimestres, unidades temporales)
* Visualiza la distribución temporal de contenidos por espacio curricular
* Alerta sobre:
  * Sobrecarga de actividades en períodos específicos
  * Contenidos sin asignar temporalmente
  * Desequilibrios en la distribución de espacios curriculares
* Genera cronograma exportable para compartir con familias
* Permite ajustar la temporalización mediante arrastrar y soltar
* Muestra fechas clave del calendario escolar (feriados, recesos, actos)
* Integra eventos especiales del centro educativo

---

### RF-016: Accesibilidad y Diseño Universal del Aprendizaje (DUA)

**Descripción:** El sistema debe incorporar principios del DUA para facilitar la planificación inclusiva.

**Criterios de aceptación:**

* Sugiere múltiples medios de:
  * Representación (cómo se presenta la información)
  * Acción y expresión (cómo los alumnos demuestran aprendizaje)
  * Implicación (cómo se motiva y compromete a los alumnos)
* Ofrece checklist de accesibilidad para cada actividad propuesta
* Sugiere adaptaciones específicas según tipos de necesidades:
  * Visuales
  * Auditivas
  * Motoras
  * Cognitivas
  * Atencionales
* Permite etiquetar actividades según principios DUA
* Incluye banco de estrategias inclusivas por tipo de contenido
* Genera alertas si la planificación carece de opciones diversificadas

---

## REQUISITOS NO FUNCIONALES

### RNF-001: Usabilidad

* Interfaz intuitiva que no requiera capacitación extensa
* Navegación clara entre espacios, unidades y contenidos
* Diseño responsive para uso en tablet, móvil y computadora
* Máximo 3 clics para acceder a cualquier funcionalidad principal
* Tutorial interactivo integrado para nuevos usuarios
* Ayuda contextual en cada sección
* Atajos de teclado para usuarios avanzados

### RNF-002: Performance

* Carga de planificaciones en menos de 3 segundos
* Guardado automático cada 30 segundos
* Procesamiento de PDFs de hasta 200 páginas en menos de 2 minutos
* Funcionamiento offline con sincronización posterior
* Caché inteligente de contenidos frecuentemente usados
* Optimización de imágenes y documentos adjuntos

### RNF-003: Seguridad

* Protección de datos personales de alumnos según normativa uruguaya (Ley 18.331)
* Acceso mediante autenticación segura (usuario/contraseña + 2FA opcional)
* Encriptación de información sensible (datos de alumnos)
* Copias de seguridad automáticas diarias
* Control de acceso basado en roles (administrador, docente, invitado)
* Auditoría de acceso a datos sensibles
* Cumplimiento con estándares de protección de datos educativos

### RNF-004: Accesibilidad

* Cumplimiento con estándares WCAG 2.1 nivel AA
* Tamaños de texto ajustables (100% a 200%)
* Contraste adecuado y navegación por teclado
* Compatibilidad con lectores de pantalla
* Textos alternativos en todas las imágenes
* Estructura semántica correcta (HTML5)
* Soporte para modo de alto contraste

### RNF-005: Compatibilidad

* Funciona en navegadores modernos (Chrome, Firefox, Safari, Edge)
* Compatible con sistemas operativos: Windows, macOS, Linux, iOS, Android
* Formato de datos exportables compatible con Office y Google Workspace
* API abierta para integración con otros sistemas educativos
* Estándares web abiertos (HTML5, CSS3, JavaScript ES6+)

### RNF-006: Escalabilidad

* Soporta hasta 10,000 usuarios concurrentes
* Capacidad de almacenar 100,000 planificaciones
* Base de datos escalable horizontalmente
* Arquitectura en la nube (AWS, Azure o similar)
* Sistema de caché distribuida

### RNF-007: Mantenibilidad

* Código documentado y modular
* Sistema de versionado de código (Git)
* Entorno de desarrollo, pruebas y producción separados
* Logs detallados para debugging
* Monitoreo de errores en tiempo real
* Actualización de contenidos sin downtime

### RNF-008: Disponibilidad

* Disponibilidad del sistema: 99.5% (menos de 4 horas de downtime al mes)
* Tiempo de recuperación ante fallos: menos de 30 minutos
* Backups incrementales cada 6 horas, completos semanalmente
* Plan de recuperación ante desastres documentado

---

## FLUJO PRINCIPAL DE USO

### Flujo 1: Creación de Planificación desde Cero

1. **Educadora ingresa al sistema**
   * Se autentica con sus credenciales
   * Accede al dashboard principal
2. **Crea nueva planificación**
   * Selecciona nivel educativo (ej: Tramo 2 - 1° grado)
   * Define período temporal (ej: Marzo-Junio 2024)
   * Asigna nombre y descripción
3. **Carga documentación oficial (primera vez)**
   * Sube PDFs del programa ANEP correspondiente al nivel
   * Sistema procesa y extrae estructura curricular
   * Revisa y valida la información extraída
4. **Selecciona espacios curriculares a trabajar**
   * Marca los espacios que abordará en este período
   * Sistema muestra unidades curriculares disponibles en cada espacio
5. **Dentro de cada espacio, selecciona unidades curriculares**
   * Elige una o más unidades por espacio
   * Visualiza descripción, competencias y contenidos oficiales
6. **Agrega contenidos específicos a cada unidad**
   * Selecciona de banco de contenidos estructurantes
   * Agrega contenidos específicos asociados
   * Establece secuencia didáctica
   * Puede personalizar o agregar contenidos propios
7. **Define criterios de logro para cada contenido**
   * Utiliza criterios sugeridos del programa oficial
   * Adapta redacción según necesidad
   * Especifica nivel de complejidad esperado
8. **Establece metas de aprendizaje**
   * Define metas generales de la planificación
   * Establece metas específicas por espacio/unidad
   * Vincula metas con criterios de logro
   * Establece tiempos estimados
9. **Vincula alumnos a la planificación**
   * Selecciona grupo/clase existente o crea uno nuevo
   * Revisa perfiles de alumnos vinculados
   * Identifica necesidades de personalización
10. **Personaliza para cada alumno según singularidades**
    * Revisa singularidades de cada alumno
    * Adapta contenidos, criterios o metas según necesidad
    * Agrega estrategias didácticas diferenciadas
    * Documenta adecuaciones realizadas
11. **Usa el asistente para pensar actividades de clase**
    * Solicita sugerencias de actividades por contenido
    * Revisa secuencias didácticas propuestas
    * Selecciona y adapta recursos sugeridos
    * Guarda actividades en biblioteca personal
12. **Organiza temporalmente la implementación**
    * Ubica contenidos y actividades en calendario
    * Distribuye carga por semanas/días
    * Ajusta según eventos especiales del centro
13. **Registra avances durante la implementación**
    * Marca progreso de cada alumno en criterios
    * Agrega observaciones y evidencias
    * Consulta alertas y sugerencias del sistema
14. **Ajusta la planificación según observaciones**
    * Modifica secuencia si es necesario
    * Agrega apoyos adicionales para alumnos específicos
    * Actualiza metas según avances reales

### Flujo 2: Uso del Asistente de Clase Diaria

1. **Educadora selecciona planificación activa**
2. **Elige fecha/clase a planificar**
3. **Sistema sugiere** :

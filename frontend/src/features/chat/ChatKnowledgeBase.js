// NexusForge AI — Exhaustive Knowledge Base (45 topics, 500+ lines)
// Each topic: category, question_patterns (5+), answer_en (detailed), answer_es (full translation)

export const NEXUSFORGE_KB = {

  // ═══════════════════════════════════════════
  // GETTING STARTED
  // ═══════════════════════════════════════════

  what_is_nexusforge: {
    category: 'getting_started',
    question_patterns: ['what is nexusforge', 'que es nexusforge', 'about', 'overview', 'what does this do', 'para que sirve', 'explain nexusforge', 'explicame nexusforge', 'introduce', 'descripcion', 'tell me about nexusforge', 'que hace esta plataforma'],
    answer_en: 'NexusForge AI is an enterprise-grade agent orchestration platform. It coordinates 22 specialized AI agents across 6 execution topologies (sequential, parallel, hierarchical, debate, consensus, adaptive). The platform includes a DAG execution engine using Kahn\'s algorithm for topological sorting, a 3-tier memory system (working, episodic, semantic), self-healing with 5 recovery strategies, a RAG pipeline with Voyage AI 512-dimensional embeddings stored in pgvector, multi-provider LLM routing from Groq to Claude with circuit breaker pattern, and real-time WebSocket monitoring. The backend is built with Python FastAPI and asyncio, the frontend with React 18 and Vite, backed by PostgreSQL and Redis. It is designed to let organizations build complex AI workflows that are observable, recoverable, and cost-efficient.',
    answer_es: 'NexusForge AI es una plataforma de orquestacion de agentes de grado empresarial. Coordina 22 agentes IA especializados a traves de 6 topologias de ejecucion (secuencial, paralelo, jerarquico, debate, consenso, adaptivo). La plataforma incluye un motor de ejecucion DAG usando el algoritmo de Kahn para ordenamiento topologico, un sistema de memoria de 3 niveles (trabajo, episodica, semantica), auto-reparacion con 5 estrategias de recuperacion, un pipeline RAG con embeddings Voyage AI de 512 dimensiones almacenados en pgvector, enrutamiento LLM multi-proveedor de Groq a Claude con patron circuit breaker, y monitoreo en tiempo real via WebSocket. El backend esta construido con Python FastAPI y asyncio, el frontend con React 18 y Vite, respaldado por PostgreSQL y Redis. Esta disenado para que las organizaciones construyan flujos de trabajo IA complejos que sean observables, recuperables y eficientes en costos.'
  },

  how_it_works: {
    category: 'getting_started',
    question_patterns: ['how it works', 'como funciona', 'data flow', 'flujo de datos', 'how does it work', 'explain the flow', 'explicar flujo', 'process', 'pipeline flow', 'step by step'],
    answer_en: 'Data enters NexusForge through document upload or API call. Documents get chunked into 500-character segments with 50-character overlap, then embedded with Voyage AI into 512-dimensional vectors stored in pgvector. Workflows define DAG pipelines of agent steps -- the executor uses topological sort (Kahn\'s algorithm) to determine execution order. Steps with no mutual dependencies run in parallel via asyncio.gather. Each step invokes an agent through the multi-provider LLM router, which tries Groq first (40x cheaper) and falls back to Claude if needed. Results are checkpointed to Redis after each step completes. Real-time events are broadcast via WebSocket so the UI updates live. If any step fails, the self-healing engine detects the error type, selects a recovery strategy (retry, skip, repair, escalate, or fallback), and attempts automatic recovery before moving to the dead letter queue.',
    answer_es: 'Los datos entran a NexusForge a traves de carga de documentos o llamada API. Los documentos se fragmentan en segmentos de 500 caracteres con 50 de solapamiento, luego se generan embeddings con Voyage AI en vectores de 512 dimensiones almacenados en pgvector. Los workflows definen pipelines DAG de pasos de agentes -- el ejecutor usa ordenamiento topologico (algoritmo de Kahn) para determinar el orden de ejecucion. Los pasos sin dependencias mutuas se ejecutan en paralelo via asyncio.gather. Cada paso invoca un agente a traves del router LLM multi-proveedor, que intenta Groq primero (40x mas barato) y recurre a Claude si es necesario. Los resultados se guardan en Redis despues de cada paso. Los eventos en tiempo real se transmiten via WebSocket. Si algun paso falla, el motor de auto-reparacion detecta el tipo de error, selecciona una estrategia de recuperacion y lo intenta automaticamente.'
  },

  use_cases: {
    category: 'getting_started',
    question_patterns: ['use cases', 'casos de uso', 'what can i do', 'que puedo hacer', 'examples', 'ejemplos', 'scenarios', 'escenarios', 'applications', 'aplicaciones'],
    answer_en: 'NexusForge supports a wide range of enterprise AI use cases. **Document processing pipelines** -- classify, extract entities, summarize, and validate documents in a single workflow. **Compliance checking** -- run documents through the compliance agent to flag regulatory issues. **Research automation** -- the researcher agent gathers information while the summarizer condenses findings. **Data classification** -- the classifier agent categorizes documents into legal, financial, technical, medical, or general. **Content generation** -- chain the planner, researcher, and reporter agents for structured content. **Multi-language translation** -- the translator agent handles content localization. **Quality assurance** -- the critic and validator agents score and gate output quality. You can combine any of the 22 agents into custom workflows using the DAG builder.',
    answer_es: 'NexusForge soporta una amplia gama de casos de uso empresariales. **Procesamiento de documentos** -- clasificar, extraer entidades, resumir y validar documentos en un solo workflow. **Verificacion de cumplimiento** -- ejecutar documentos a traves del agente de cumplimiento. **Automatizacion de investigacion** -- el agente investigador recopila informacion mientras el resumidor condensa hallazgos. **Clasificacion de datos** -- el agente clasificador categoriza documentos en legal, financiero, tecnico, medico o general. **Generacion de contenido** -- encadenar agentes planificador, investigador y reportero. **Traduccion multi-idioma** -- el agente traductor maneja localizacion. **Aseguramiento de calidad** -- los agentes critico y validador puntuan y filtran la calidad.'
  },

  getting_started: {
    category: 'getting_started',
    question_patterns: ['getting started', 'como empezar', 'start', 'comenzar', 'first steps', 'primeros pasos', 'tutorial', 'guide', 'guia', 'where do i start'],
    answer_en: 'Start by exploring the **Dashboard** to see platform stats like total agents, workflows, and executions. Then go to **Workflows** to see pre-built DAG pipelines -- try the "Analisis de Documentos" template which chains classifier, extractor, summarizer, and validator agents. Go to **Documents** to upload a file and watch the RAG pipeline chunk, embed, and index it in real-time. Use the **Agents** page to browse all 22 agents and see their configurations. Try **Swarms** to see how agents collaborate in different topologies like debate or consensus. Finally, check the **Analytics** page for execution metrics, cost tracking, and performance dashboards. Each section has interactive demos that work without API keys.',
    answer_es: 'Empieza explorando el **Dashboard** para ver estadisticas de la plataforma. Luego ve a **Workflows** para ver pipelines DAG pre-construidos -- prueba la plantilla "Analisis de Documentos" que encadena agentes clasificador, extractor, resumidor y validador. Ve a **Documentos** para subir un archivo y ver el pipeline RAG procesarlo en tiempo real. Usa la pagina de **Agentes** para explorar los 22 agentes. Prueba **Swarms** para ver como los agentes colaboran en topologias como debate o consenso. Finalmente, revisa **Analytics** para metricas de ejecucion, seguimiento de costos y dashboards de rendimiento.'
  },

  // ═══════════════════════════════════════════
  // AGENTS — OVERVIEW & INDIVIDUAL
  // ═══════════════════════════════════════════

  agents_overview: {
    category: 'agents',
    question_patterns: ['agents', 'agentes', 'how many agents', 'cuantos agentes', 'agent types', 'tipos de agentes', 'show agents', 'list agents', 'all agents', 'todos los agentes'],
    answer_en: 'NexusForge has **22 specialized agents**, each inheriting from BaseAgent. Every agent uses the multi-provider LLM router (Groq primary, Claude fallback) and has a demo fallback mode for offline operation.\n\n**Data Processing:** Classifier, Extractor, Normalizer, Validator\n**Analysis:** Analyzer, Summarizer, Sentiment, Researcher\n**Intelligence:** Planner, Router, Critic, Knowledge\n**Operations:** Monitor, Repair, Scheduler, Webhook\n**Content:** Reporter, Translator, OCR, Scraper\n**Quality:** Enricher, Compliance\n\nEach agent receives a structured input dict, processes it through its specialized prompt, and returns a standardized output with metadata including tokens used, latency, and cost.',
    answer_es: 'NexusForge tiene **22 agentes especializados**, cada uno heredando de BaseAgent. Cada agente usa el router LLM multi-proveedor (Groq primario, Claude respaldo) y tiene modo demo de respaldo.\n\n**Procesamiento de Datos:** Clasificador, Extractor, Normalizador, Validador\n**Analisis:** Analizador, Resumidor, Sentimiento, Investigador\n**Inteligencia:** Planificador, Router, Critico, Conocimiento\n**Operaciones:** Monitor, Reparacion, Programador, Webhook\n**Contenido:** Reportero, Traductor, OCR, Scraper\n**Calidad:** Enriquecedor, Cumplimiento\n\nCada agente recibe un dict de entrada estructurado, lo procesa a traves de su prompt especializado y retorna una salida estandarizada con metadatos.'
  },

  classifier_agent: {
    category: 'agents',
    question_patterns: ['classifier', 'clasificador', 'classify', 'clasificar', 'document classification', 'clasificacion de documentos', 'categorize', 'categorizar'],
    answer_en: 'The **Classifier Agent** categorizes documents into predefined types: legal, financial, technical, medical, and general. It analyzes the first 500 characters of a document using the LLM to determine the most likely category. The output includes the predicted category, a confidence score from 0 to 1, and detailed reasoning explaining why that category was chosen. It supports custom category lists via the `categories` config parameter. In demo mode, it uses keyword-based heuristics for fast classification without API calls. Typical latency is under 2 seconds with Groq. The classifier is often the first step in document processing workflows, routing documents to specialized downstream agents.',
    answer_es: 'El **Agente Clasificador** categoriza documentos en tipos predefinidos: legal, financiero, tecnico, medico y general. Analiza los primeros 500 caracteres usando el LLM para determinar la categoria mas probable. La salida incluye la categoria predicha, una puntuacion de confianza de 0 a 1, y razonamiento detallado. Soporta listas de categorias personalizadas via el parametro `categories`. En modo demo usa heuristicas basadas en palabras clave. La latencia tipica es menor a 2 segundos con Groq. El clasificador suele ser el primer paso en workflows de procesamiento de documentos.'
  },

  extractor_agent: {
    category: 'agents',
    question_patterns: ['extractor', 'extract', 'extraer', 'extraction', 'extraccion', 'named entities', 'entidades', 'entity extraction', 'ner'],
    answer_en: 'The **Extractor Agent** performs named entity recognition, pulling out people, organizations, dates, monetary amounts, and locations from text. It returns a structured list where each entity includes the type (PERSON, ORG, DATE, MONEY, LOCATION), the extracted value, and the surrounding context sentence. The agent can process documents up to 10,000 characters by splitting into overlapping windows. It deduplicates entities that appear in multiple windows. In demo mode, it uses regex patterns for common entity formats. The extractor is typically chained after the classifier to build structured metadata from unstructured documents.',
    answer_es: 'El **Agente Extractor** realiza reconocimiento de entidades nombradas, extrayendo personas, organizaciones, fechas, montos monetarios y ubicaciones del texto. Retorna una lista estructurada donde cada entidad incluye el tipo (PERSONA, ORG, FECHA, DINERO, UBICACION), el valor extraido y el contexto circundante. Puede procesar documentos de hasta 10,000 caracteres dividiendolos en ventanas con solapamiento. Deduplica entidades que aparecen en multiples ventanas. En modo demo usa patrones regex. El extractor tipicamente se encadena despues del clasificador.'
  },

  summarizer_agent: {
    category: 'agents',
    question_patterns: ['summarizer', 'resumidor', 'summarize', 'resumir', 'summary', 'resumen', 'condense', 'condensar', 'tldr'],
    answer_en: 'The **Summarizer Agent** generates configurable-length summaries with three modes: short (1-2 sentences), medium (1 paragraph), and long (multiple paragraphs with section headers). The output includes the summary text, an array of key points extracted from the document, and a word count. It handles documents up to 15,000 characters by first chunking, summarizing each chunk, then producing a final consolidated summary. The `style` config parameter allows formal, casual, or technical tone. In demo mode, it extracts the first and last sentences of each paragraph. The summarizer is one of the most frequently used agents in workflows.',
    answer_es: 'El **Agente Resumidor** genera resumenes de longitud configurable con tres modos: corto (1-2 oraciones), medio (1 parrafo) y largo (multiples parrafos con encabezados). La salida incluye el texto del resumen, un array de puntos clave y conteo de palabras. Maneja documentos de hasta 15,000 caracteres fragmentando, resumiendo cada fragmento y produciendo un resumen consolidado final. El parametro `style` permite tono formal, casual o tecnico. En modo demo extrae la primera y ultima oracion de cada parrafo.'
  },

  analyzer_agent: {
    category: 'agents',
    question_patterns: ['analyzer', 'analizador', 'analyze', 'analizar', 'analysis', 'analisis', 'sentiment analysis', 'topic detection', 'complexity'],
    answer_en: 'The **Analyzer Agent** performs multi-dimensional text analysis including sentiment detection (positive, negative, neutral with confidence), topic identification (returns top 5 topics with relevance scores), complexity assessment (Flesch-Kincaid grade level), and text statistics (word count, sentence count, average sentence length, vocabulary richness). It can also detect language and formality level. The agent is useful for content auditing, editorial workflows, and data quality assessment. In demo mode, it uses word-frequency heuristics and readability formulas. Typical output includes 6+ structured fields for comprehensive document understanding.',
    answer_es: 'El **Agente Analizador** realiza analisis de texto multidimensional incluyendo deteccion de sentimiento (positivo, negativo, neutro con confianza), identificacion de temas (top 5 temas con puntuaciones), evaluacion de complejidad (nivel Flesch-Kincaid) y estadisticas de texto (conteo de palabras, oraciones, longitud promedio, riqueza de vocabulario). Tambien puede detectar idioma y nivel de formalidad. En modo demo usa heuristicas de frecuencia de palabras.'
  },

  validator_agent: {
    category: 'agents',
    question_patterns: ['validator', 'validador', 'validate', 'validar', 'validation', 'validacion', 'quality gate', 'quality check', 'score output'],
    answer_en: 'The **Validator Agent** acts as a quality gate, scoring agent output from 0 to 100. It checks three dimensions: completeness (are all required fields present?), consistency (do the outputs agree with each other?), and accuracy (does the output match the input data?). It returns an `is_valid` boolean (true if score >= 70), the numeric score, an issues array listing specific problems found, and a recommendations array with improvement suggestions. The validation threshold is configurable. In workflows, the validator is typically the last step -- if it fails, the self-healing engine can trigger a repair cycle. This creates a built-in quality assurance loop.',
    answer_es: 'El **Agente Validador** actua como puerta de calidad, puntuando la salida de agentes de 0 a 100. Verifica tres dimensiones: completitud, consistencia y precision. Retorna un booleano `is_valid` (true si puntuacion >= 70), la puntuacion numerica, un array de problemas encontrados y un array de recomendaciones. El umbral es configurable. En workflows, el validador tipicamente es el ultimo paso -- si falla, el motor de auto-reparacion puede activar un ciclo de reparacion.'
  },

  repair_agent: {
    category: 'agents',
    question_patterns: ['repair agent', 'agente reparacion', 'reparar', 'fix agent', 'arreglar', 'diagnose', 'diagnosticar', 'self-repair'],
    answer_en: 'The **Repair Agent** is the core of the self-healing system. When a step fails, this agent receives the error message, the failed step\'s configuration, and the original input. It analyzes the failure and returns a structured diagnosis with: the root cause description, the fix_type (retry with different params, reconfigure the step, skip with default output, or escalate to human), suggested configuration changes as a dict, and a can_auto_fix boolean. If can_auto_fix is true, the executor automatically applies the suggested changes and re-runs the step. The repair agent has seen patterns from thousands of failure modes and can fix issues like timeout errors by reducing input size, or schema errors by reformatting the output.',
    answer_es: 'El **Agente de Reparacion** es el nucleo del sistema de auto-reparacion. Cuando un paso falla, recibe el mensaje de error, la configuracion del paso fallido y la entrada original. Analiza la falla y retorna un diagnostico estructurado con: descripcion de causa raiz, tipo de correccion (reintentar, reconfigurar, omitir o escalar), cambios de configuracion sugeridos, y un booleano can_auto_fix. Si can_auto_fix es true, el ejecutor aplica los cambios automaticamente y re-ejecuta el paso.'
  },

  planner_agent: {
    category: 'agents',
    question_patterns: ['planner', 'planificador', 'plan', 'planificar', 'decompose', 'descomponer', 'task planning', 'planificacion de tareas', 'break down'],
    answer_en: 'The **Planner Agent** decomposes complex tasks into an ordered list of subtasks with dependency relationships. Given a high-level objective, it returns an execution plan array where each entry has: step name, assigned agent (chosen from the 22 available), dependencies (list of step names that must complete first), priority (1-5), and estimated complexity. The planner understands agent capabilities and will never assign a task to an incompatible agent. It is the brain behind hierarchical swarm topology -- the planner creates the plan, workers execute subtasks in parallel where possible, and a synthesizer combines the results. Typical plans contain 3-8 steps.',
    answer_es: 'El **Agente Planificador** descompone tareas complejas en una lista ordenada de subtareas con relaciones de dependencia. Dado un objetivo de alto nivel, retorna un array de plan de ejecucion donde cada entrada tiene: nombre del paso, agente asignado (de los 22 disponibles), dependencias, prioridad (1-5) y complejidad estimada. El planificador entiende las capacidades de cada agente. Es el cerebro detras de la topologia jerarquica.'
  },

  critic_agent: {
    category: 'agents',
    question_patterns: ['critic', 'critico', 'critique', 'criticar', 'evaluate', 'evaluar', 'review', 'revisar', 'feedback'],
    answer_en: 'The **Critic Agent** evaluates output quality from other agents on a 0-100 scale. It provides a detailed critique with: overall score, strengths array (what was done well), improvements array (specific actionable suggestions), a pass/fail boolean (threshold at 75 by default), and a one-paragraph written review. The critic is central to the debate swarm topology -- an agent produces output, the critic evaluates it, and if the score is below threshold, the original agent tries again incorporating the critique. This loop continues until quality meets the standard or max iterations are reached.',
    answer_es: 'El **Agente Critico** evalua la calidad de salida de otros agentes en una escala de 0-100. Proporciona una critica detallada con: puntuacion general, array de fortalezas, array de mejoras (sugerencias especificas), booleano aprobado/reprobado (umbral en 75 por defecto), y una resena escrita. El critico es central en la topologia de debate -- un agente produce salida, el critico la evalua, y si la puntuacion es baja, el agente original intenta de nuevo incorporando la critica.'
  },

  normalizer_agent: {
    category: 'agents',
    question_patterns: ['normalizer', 'normalizador', 'normalize', 'normalizar', 'clean data', 'limpiar datos', 'standardize', 'estandarizar', 'data cleaning'],
    answer_en: 'The **Normalizer Agent** cleans and standardizes raw text data. It handles date format unification (converting varied formats to ISO 8601), currency normalization, name casing, whitespace cleanup, encoding fixes (UTF-8 normalization), and duplicate line removal. It returns the cleaned text plus a changelog of all transformations applied. The normalizer is essential in data pipelines where input comes from multiple sources with inconsistent formatting. It typically runs early in a workflow, right after extraction.',
    answer_es: 'El **Agente Normalizador** limpia y estandariza datos de texto. Maneja unificacion de formatos de fecha (convirtiendo a ISO 8601), normalizacion de monedas, capitalizacion de nombres, limpieza de espacios, correcciones de codificacion (normalizacion UTF-8) y eliminacion de lineas duplicadas. Retorna el texto limpio mas un registro de todas las transformaciones aplicadas. Es esencial en pipelines donde la entrada viene de multiples fuentes.'
  },

  enricher_agent: {
    category: 'agents',
    question_patterns: ['enricher', 'enriquecedor', 'enrich', 'enriquecer', 'augment', 'add context', 'agregar contexto'],
    answer_en: 'The **Enricher Agent** augments extracted data with additional context from the knowledge base and external lookups. Given a set of entities (people, companies, locations), it queries the semantic memory and RAG pipeline to find related information, then appends relevant context to each entity. For example, if "Anthropic" is extracted, the enricher might add "AI safety company, founded 2021, creator of Claude." It returns the original entities plus enrichment fields: description, related_entities, and confidence. This agent bridges the gap between raw extraction and actionable intelligence.',
    answer_es: 'El **Agente Enriquecedor** aumenta datos extraidos con contexto adicional de la base de conocimiento y busquedas externas. Dada una serie de entidades, consulta la memoria semantica y el pipeline RAG para encontrar informacion relacionada. Por ejemplo, si se extrae "Anthropic", podria agregar "Empresa de seguridad IA, fundada 2021, creadora de Claude." Retorna las entidades originales mas campos de enriquecimiento.'
  },

  researcher_agent: {
    category: 'agents',
    question_patterns: ['researcher', 'investigador', 'research', 'investigar', 'investigate', 'gather information', 'recopilar informacion'],
    answer_en: 'The **Researcher Agent** gathers and synthesizes information on a given topic. It queries the RAG pipeline for relevant document chunks, combines them with its LLM knowledge, and produces a structured research report with: executive summary, key findings (bulleted), supporting evidence with source references, knowledge gaps identified, and recommended next steps. The researcher can be configured with a `depth` parameter (shallow, medium, deep) that controls how many document chunks it retrieves and how detailed the analysis is. It is commonly paired with the summarizer in research automation workflows.',
    answer_es: 'El **Agente Investigador** recopila y sintetiza informacion sobre un tema dado. Consulta el pipeline RAG para fragmentos de documentos relevantes, los combina con su conocimiento LLM, y produce un informe de investigacion estructurado con: resumen ejecutivo, hallazgos clave, evidencia de soporte con referencias, brechas de conocimiento identificadas y proximos pasos recomendados. Se puede configurar con parametro `depth` (superficial, medio, profundo).'
  },

  translator_agent: {
    category: 'agents',
    question_patterns: ['translator', 'traductor', 'translate', 'traducir', 'translation', 'traduccion', 'language', 'idioma', 'multi-language'],
    answer_en: 'The **Translator Agent** handles content localization between languages. It supports translation between English, Spanish, French, German, Portuguese, and more. Beyond literal translation, it preserves formatting (markdown, bullet points, headers), adapts cultural references, and maintains technical terminology consistency. The output includes the translated text, source language detected, target language, and a confidence score. It can process documents up to 8,000 characters. The translator is commonly used in content generation workflows to produce multi-language output from a single source.',
    answer_es: 'El **Agente Traductor** maneja la localizacion de contenido entre idiomas. Soporta traduccion entre ingles, espanol, frances, aleman, portugues y mas. Mas alla de la traduccion literal, preserva formato (markdown, vinetas, encabezados), adapta referencias culturales y mantiene consistencia en terminologia tecnica. La salida incluye texto traducido, idioma fuente detectado, idioma destino y puntuacion de confianza.'
  },

  compliance_agent: {
    category: 'agents',
    question_patterns: ['compliance', 'cumplimiento', 'regulatory', 'regulatorio', 'legal check', 'verificacion legal', 'audit', 'auditoria'],
    answer_en: 'The **Compliance Agent** checks documents against regulatory and policy requirements. It scans for PII exposure (names, SSNs, emails, phone numbers), validates data handling practices against GDPR/CCPA guidelines, checks for required legal disclaimers, and flags potentially problematic language. The output includes a compliance_score (0-100), a list of violations with severity (critical, warning, info), specific text locations of issues, and remediation suggestions. The agent can be configured with custom rule sets for industry-specific compliance.',
    answer_es: 'El **Agente de Cumplimiento** verifica documentos contra requisitos regulatorios y de politicas. Escanea exposicion de PII (nombres, SSN, emails, telefonos), valida practicas de manejo de datos contra guias GDPR/CCPA, verifica disclaimers legales requeridos y senala lenguaje potencialmente problematico. La salida incluye compliance_score (0-100), lista de violaciones con severidad, ubicaciones en el texto y sugerencias de remediacion.'
  },

  monitor_agent: {
    category: 'agents',
    question_patterns: ['monitor', 'monitoring', 'monitoreo', 'observe', 'observar', 'health check', 'system health', 'salud del sistema'],
    answer_en: 'The **Monitor Agent** tracks system health and execution metrics in real-time. It collects agent latency, token usage, error rates, memory utilization, and queue depths. It can detect anomalies like sudden latency spikes or elevated error rates and trigger alerts. The monitor produces periodic health reports with: overall system status (healthy/degraded/critical), per-agent performance stats, resource utilization percentages, and trend indicators. It feeds data to the Prometheus metrics endpoint which powers the 5 Grafana dashboards.',
    answer_es: 'El **Agente Monitor** rastrea la salud del sistema y metricas de ejecucion en tiempo real. Recopila latencia de agentes, uso de tokens, tasas de error, utilizacion de memoria y profundidad de colas. Detecta anomalias como picos de latencia o tasas de error elevadas. Produce informes periodicos con: estado general del sistema, estadisticas por agente, porcentajes de utilizacion y indicadores de tendencia.'
  },

  router_agent: {
    category: 'agents',
    question_patterns: ['router agent', 'agente router', 'routing', 'enrutamiento', 'route tasks', 'enrutar tareas', 'task routing'],
    answer_en: 'The **Router Agent** intelligently dispatches tasks to the most suitable agent based on content analysis. Given an input document or task description, it evaluates the content type, complexity, and required capabilities, then selects the optimal agent or sequence of agents. It returns the recommended agent name, confidence in the routing decision, reasoning, and an alternative agent if the primary choice is unavailable. The router is the brain behind the adaptive swarm topology -- it dynamically selects which topology pattern to use based on the task characteristics.',
    answer_es: 'El **Agente Router** despacha inteligentemente tareas al agente mas adecuado basandose en analisis de contenido. Evalua tipo de contenido, complejidad y capacidades requeridas, luego selecciona el agente optimo. Retorna el nombre del agente recomendado, confianza en la decision, razonamiento y un agente alternativo. Es el cerebro detras de la topologia adaptiva.'
  },

  knowledge_agent: {
    category: 'agents',
    question_patterns: ['knowledge agent', 'agente conocimiento', 'knowledge base', 'base de conocimiento', 'knowledge management', 'gestion de conocimiento'],
    answer_en: 'The **Knowledge Agent** manages the semantic memory layer and serves as the interface to the organization\'s knowledge base. It can store new knowledge (embedding text into pgvector), retrieve relevant knowledge (semantic search), update existing entries, and identify knowledge gaps. When other agents need context, they query the knowledge agent which performs similarity search across all stored vectors. It returns relevant chunks with similarity scores, source document references, and freshness timestamps. The knowledge agent is what makes NexusForge\'s agents context-aware.',
    answer_es: 'El **Agente de Conocimiento** gestiona la capa de memoria semantica y sirve como interfaz a la base de conocimiento. Puede almacenar nuevo conocimiento (embeber texto en pgvector), recuperar conocimiento relevante (busqueda semantica), actualizar entradas y identificar brechas de conocimiento. Retorna fragmentos relevantes con puntuaciones de similitud, referencias a documentos fuente y timestamps.'
  },

  scraper_agent: {
    category: 'agents',
    question_patterns: ['scraper', 'web scraper', 'scraping', 'web scraping', 'crawl', 'rastrear', 'extract web', 'extraer web'],
    answer_en: 'The **Scraper Agent** extracts structured data from web pages and HTML content. It can parse HTML to extract text content, tables, links, metadata (title, description, OpenGraph tags), and specific CSS-selector-targeted elements. The output includes cleaned text, extracted tables as arrays, link inventory, and metadata dict. It handles common challenges like JavaScript-rendered content indicators, pagination hints, and encoding detection. The scraper feeds data into the RAG pipeline for indexing and is often the first step in research automation workflows.',
    answer_es: 'El **Agente Scraper** extrae datos estructurados de paginas web y contenido HTML. Puede parsear HTML para extraer texto, tablas, enlaces, metadatos (titulo, descripcion, OpenGraph) y elementos especificos por selector CSS. La salida incluye texto limpio, tablas como arrays, inventario de enlaces y dict de metadatos. Alimenta datos al pipeline RAG para indexacion.'
  },

  ocr_agent: {
    category: 'agents',
    question_patterns: ['ocr', 'optical character', 'reconocimiento optico', 'image to text', 'imagen a texto', 'scan document', 'escanear documento', 'pdf extract'],
    answer_en: 'The **OCR Agent** extracts text from images and scanned documents. It processes common image formats (PNG, JPG, TIFF) and scanned PDFs. The output includes the extracted text, confidence score per text block, detected language, and page layout information (text regions with bounding boxes). It handles multi-column layouts, tables in images, and rotated text. OCR output is typically fed into the normalizer agent for cleanup, then into the classifier and extractor for structured processing.',
    answer_es: 'El **Agente OCR** extrae texto de imagenes y documentos escaneados. Procesa formatos comunes (PNG, JPG, TIFF) y PDFs escaneados. La salida incluye texto extraido, puntuacion de confianza por bloque, idioma detectado e informacion de diseno de pagina. Maneja disenos multi-columna, tablas en imagenes y texto rotado.'
  },

  sentiment_agent: {
    category: 'agents',
    question_patterns: ['sentiment', 'sentimiento', 'opinion', 'mood', 'emotion', 'emocion', 'feeling', 'positive negative'],
    answer_en: 'The **Sentiment Agent** performs granular sentiment analysis beyond simple positive/negative classification. It detects: overall sentiment (positive, negative, neutral, mixed) with confidence score, emotional tone (joy, anger, sadness, surprise, fear, trust), aspect-based sentiment (different sentiments for different topics within the same text), intensity level (mild, moderate, strong), and sarcasm/irony detection. The output includes a sentiment_map that shows how sentiment changes throughout the document.',
    answer_es: 'El **Agente de Sentimiento** realiza analisis granular de sentimiento mas alla de la clasificacion simple positivo/negativo. Detecta: sentimiento general con confianza, tono emocional (alegria, enojo, tristeza, sorpresa, miedo, confianza), sentimiento por aspecto, nivel de intensidad (leve, moderado, fuerte) y deteccion de sarcasmo/ironia.'
  },

  scheduler_agent: {
    category: 'agents',
    question_patterns: ['scheduler', 'programador', 'schedule', 'programar', 'cron', 'recurring', 'recurrente', 'timed execution'],
    answer_en: 'The **Scheduler Agent** manages timed and recurring workflow executions. It supports cron-style scheduling (e.g., "every Monday at 9 AM"), interval-based triggers (e.g., "every 4 hours"), event-driven triggers (e.g., "when a new document is uploaded"), and one-time delayed execution. The scheduler maintains a priority queue of pending executions and handles timezone-aware scheduling. It returns execution receipts with: scheduled_time, workflow_id, trigger_type, and next_run.',
    answer_es: 'El **Agente Programador** gestiona ejecuciones programadas y recurrentes de workflows. Soporta programacion estilo cron, triggers por intervalo, triggers por evento y ejecucion diferida unica. Mantiene una cola de prioridad de ejecuciones pendientes y maneja zonas horarias. Retorna recibos de ejecucion con: hora_programada, workflow_id, tipo_trigger y proxima_ejecucion.'
  },

  webhook_agent: {
    category: 'agents',
    question_patterns: ['webhook', 'webhooks', 'external trigger', 'trigger externo', 'api trigger', 'integration', 'integracion'],
    answer_en: 'The **Webhook Agent** handles incoming and outgoing webhook integrations. For incoming webhooks, it validates payloads against configurable JSON schemas, extracts relevant data, and triggers appropriate workflows. For outgoing webhooks, it sends execution results to external systems with configurable retry policies. It supports HMAC signature verification for security, custom headers, and payload transformation templates. The webhook agent enables NexusForge to integrate with external tools like Slack, GitHub, Jira, and custom enterprise systems.',
    answer_es: 'El **Agente Webhook** maneja integraciones de webhooks entrantes y salientes. Para entrantes, valida payloads contra esquemas JSON configurables, extrae datos relevantes y activa workflows. Para salientes, envia resultados a sistemas externos con politicas de reintento. Soporta verificacion HMAC, headers personalizados y plantillas de transformacion. Permite integrar NexusForge con Slack, GitHub, Jira y sistemas empresariales.'
  },

  // ═══════════════════════════════════════════
  // WORKFLOWS
  // ═══════════════════════════════════════════

  workflows_intro: {
    category: 'workflows',
    question_patterns: ['workflow', 'workflows', 'flujo de trabajo', 'what are workflows', 'que son los workflows', 'pipeline', 'dag workflow', 'flujos'],
    answer_en: 'Workflows in NexusForge are **directed acyclic graphs (DAGs)** that chain multiple agents into processing pipelines. Each node in the graph is a "step" that invokes a specific agent with configured inputs. Edges represent dependencies -- step B depends on step A means B waits for A to complete and receives A\'s output. Because the graph is acyclic (no loops), the system can determine a valid execution order using topological sorting. Steps without mutual dependencies run in parallel automatically. Workflows support templates, versioning, and can be saved, shared, cloned, and scheduled. The UI provides both a visual DAG builder and a JSON editor for advanced users.',
    answer_es: 'Los Workflows en NexusForge son **grafos aciclicos dirigidos (DAGs)** que encadenan multiples agentes en pipelines de procesamiento. Cada nodo es un "paso" que invoca un agente especifico con entradas configuradas. Las aristas representan dependencias. Como el grafo es aciclico, el sistema determina un orden de ejecucion valido usando ordenamiento topologico. Los pasos sin dependencias mutuas se ejecutan en paralelo automaticamente. Los workflows soportan plantillas, versionado, y pueden guardarse, compartirse, clonarse y programarse.'
  },

  dag_engine: {
    category: 'workflows',
    question_patterns: ['dag engine', 'motor dag', 'kahn', 'topological sort', 'ordenamiento topologico', 'execution engine', 'motor de ejecucion', 'how does dag work', 'como funciona el dag'],
    answer_en: 'The DAG execution engine uses **Kahn\'s algorithm** for topological sorting to determine step execution order. The algorithm works by: (1) calculating the in-degree (number of dependencies) for each step, (2) adding all steps with in-degree 0 to a ready queue, (3) executing ready steps -- if multiple steps are ready simultaneously, they run in parallel via asyncio.gather, (4) when a step completes, decrementing the in-degree of its dependents and adding newly ready steps to the queue, (5) repeating until all steps complete. The engine includes **cycle detection** (rejects workflows with circular dependencies), **missing dependency validation**, and **duplicate step detection**. Each completed step\'s state is checkpointed to Redis for crash recovery.',
    answer_es: 'El motor de ejecucion DAG usa el **algoritmo de Kahn** para ordenamiento topologico. El algoritmo: (1) calcula el grado de entrada de cada paso, (2) agrega pasos con grado 0 a la cola de listos, (3) ejecuta pasos listos en paralelo via asyncio.gather, (4) al completar un paso, decrementa el grado de sus dependientes, (5) repite hasta completar todo. Incluye **deteccion de ciclos**, **validacion de dependencias faltantes** y **deteccion de pasos duplicados**. Cada paso completado se guarda en Redis.'
  },

  create_workflow: {
    category: 'workflows',
    question_patterns: ['create workflow', 'crear workflow', 'build workflow', 'construir workflow', 'new workflow', 'nuevo workflow', 'workflow template', 'plantilla workflow', 'how to create'],
    answer_en: 'To create a workflow, go to the **Workflows** page and click "New Workflow." You can start from scratch or use a template. Available templates include: **Analisis de Documentos** (classifier -> extractor -> summarizer -> validator), **Research Pipeline** (researcher -> analyzer -> summarizer -> critic), **Content Generation** (planner -> researcher -> reporter -> translator -> validator), and **Data Processing** (OCR -> normalizer -> classifier -> extractor -> enricher). Each step has configurable parameters: input source (previous step output, manual, or document), agent-specific settings, retry policy, and timeout. Use the visual editor to drag and connect steps, or switch to JSON mode for complex configurations.',
    answer_es: 'Para crear un workflow, ve a la pagina de **Workflows** y haz clic en "Nuevo Workflow." Puedes empezar desde cero o usar una plantilla. Plantillas disponibles: **Analisis de Documentos** (clasificador -> extractor -> resumidor -> validador), **Pipeline de Investigacion** (investigador -> analizador -> resumidor -> critico), **Generacion de Contenido** (planificador -> investigador -> reportero -> traductor -> validador) y **Procesamiento de Datos** (OCR -> normalizador -> clasificador -> extractor -> enriquecedor).'
  },

  workflow_execution: {
    category: 'workflows',
    question_patterns: ['run workflow', 'ejecutar workflow', 'workflow execution', 'ejecucion de workflow', 'what happens when run', 'que pasa al ejecutar', 'execute', 'ejecutar'],
    answer_en: 'When you click **Run** on a workflow: (1) The DAG is validated -- cycle detection, dependency check, agent availability. (2) An execution record is created with a unique run_id. (3) The topological sort identifies the first group of parallelizable steps. (4) Each step is dispatched to its assigned agent via the LLM router. (5) Real-time status updates broadcast via WebSocket -- you see each step transition through queued -> running -> completed/failed. (6) Completed step outputs are checkpointed to Redis and passed as inputs to dependent steps. (7) If a step fails, the self-healing engine evaluates and applies recovery. (8) When all steps finish, the final output is assembled with results, total duration, tokens used, and cost.',
    answer_es: 'Al hacer clic en **Ejecutar**: (1) Se valida el DAG. (2) Se crea un registro de ejecucion con run_id unico. (3) El ordenamiento topologico identifica el primer grupo de pasos paralelizables. (4) Cada paso se despacha a su agente via el router LLM. (5) Actualizaciones en tiempo real via WebSocket. (6) Las salidas se guardan en Redis y se pasan como entradas a pasos dependientes. (7) Si un paso falla, el motor de auto-reparacion evalua y aplica recuperacion. (8) Al finalizar, la salida final se ensambla con resultados, duracion, tokens y costo.'
  },

  checkpointing: {
    category: 'workflows',
    question_patterns: ['checkpoint', 'checkpointing', 'punto de control', 'crash recovery', 'recuperacion de fallos', 'resume', 'reanudar', 'dead letter', 'cola de muertos'],
    answer_en: 'NexusForge implements **step-level checkpointing** for workflow resilience. After each step completes successfully, its full state (output data, metadata, timing) is serialized and saved to Redis with a TTL of 24 hours. If the process crashes mid-workflow, the executor can resume from the last checkpoint instead of starting over. Steps that fail permanently after all recovery attempts are moved to the **dead letter queue** (DLQ), which is a Redis Stream that captures the step config, input, error details, and all recovery attempts. Operators can inspect the DLQ, fix the underlying issue, and manually replay failed steps.',
    answer_es: 'NexusForge implementa **checkpointing a nivel de paso** para resiliencia. Despues de que cada paso completa, su estado se serializa y guarda en Redis con TTL de 24 horas. Si el proceso falla, el ejecutor puede reanudar desde el ultimo checkpoint. Los pasos que fallan permanentemente van a la **cola de mensajes muertos** (DLQ) en Redis Stream, que captura configuracion, entrada, detalles del error y todos los intentos de recuperacion.'
  },

  // ═══════════════════════════════════════════
  // SWARMS & TOPOLOGIES
  // ═══════════════════════════════════════════

  swarms_intro: {
    category: 'swarms',
    question_patterns: ['swarm', 'swarms', 'enjambre', 'enjambres', 'topologies', 'topologias', 'explain swarms', 'explicar enjambres', 'explain topologies', 'explicar topologias', 'explica las topologias', 'what are swarms', 'que son los swarms', 'collaboration patterns', 'patrones de colaboracion'],
    answer_en: 'Swarms are **multi-agent collaboration patterns** that define how agents work together. While workflows define WHAT steps to run, swarm topologies define HOW agents collaborate. NexusForge supports **6 topologies**:\n\n1. **Sequential** -- A->B->C chain, output of one feeds the next\n2. **Parallel** -- Fan-out to N agents simultaneously, fan-in to merge results\n3. **Hierarchical** -- Planner decomposes task, workers execute in parallel, synthesizer combines\n4. **Debate** -- Agent produces output, Critic evaluates, loop until quality threshold met\n5. **Consensus** -- N agents solve independently, Judge evaluates all and picks best\n6. **Adaptive** -- Router analyzes task complexity and dynamically selects the best topology\n\nEach topology supports checkpointing, configurable retry policies, timeout limits, and real-time progress streaming via WebSocket.',
    answer_es: 'Los Swarms son **patrones de colaboracion multi-agente** que definen como los agentes trabajan juntos. NexusForge soporta **6 topologias**:\n\n1. **Secuencial** -- Cadena A->B->C, la salida de uno alimenta al siguiente\n2. **Paralelo** -- Fan-out a N agentes simultaneamente, fan-in para fusionar resultados\n3. **Jerarquico** -- Planificador descompone tarea, trabajadores ejecutan en paralelo, sintetizador combina\n4. **Debate** -- Agente produce salida, Critico evalua, ciclo hasta alcanzar umbral de calidad\n5. **Consenso** -- N agentes resuelven independientemente, Juez evalua y elige el mejor\n6. **Adaptivo** -- Router analiza complejidad y selecciona dinamicamente la mejor topologia\n\nCada topologia soporta checkpointing, politicas de reintento configurables, limites de timeout y streaming de progreso en tiempo real via WebSocket.'
  },

  topology_sequential: {
    category: 'swarms',
    question_patterns: ['sequential topology', 'topologia secuencial', 'chain', 'cadena', 'sequential swarm', 'enjambre secuencial', 'a then b then c'],
    answer_en: 'The **Sequential topology** is the simplest pattern: agents execute one after another in a defined order (A->B->C). The output of each agent becomes the input of the next. **When to use:** Straightforward processing pipelines where each step depends on the previous one, like document classification -> entity extraction -> summary generation. **How it works internally:** The executor creates a single-path DAG and processes steps one at a time. If any step fails, the self-healing engine activates. **Example:** A legal document goes through Classifier (identify as "legal") -> Extractor (pull out parties, dates, clauses) -> Summarizer (generate brief) -> Validator (quality check).',
    answer_es: 'La **topologia Secuencial** es el patron mas simple: los agentes ejecutan uno tras otro en orden definido (A->B->C). La salida de cada agente se convierte en la entrada del siguiente. **Cuando usar:** Pipelines de procesamiento directos donde cada paso depende del anterior. **Ejemplo:** Un documento legal pasa por Clasificador -> Extractor -> Resumidor -> Validador.'
  },

  topology_parallel: {
    category: 'swarms',
    question_patterns: ['parallel topology', 'topologia paralela', 'fan out', 'fan in', 'concurrent', 'concurrente', 'parallel swarm', 'enjambre paralelo', 'simultaneous'],
    answer_en: 'The **Parallel topology** uses a fan-out/fan-in pattern: a single input is sent to multiple agents simultaneously, then their results are merged. **When to use:** When you need multiple independent analyses of the same document, like running sentiment analysis, entity extraction, and summarization at the same time. **How it works internally:** The executor dispatches all parallel agents via asyncio.gather, which runs them concurrently. A configurable merge strategy combines results: "concat" appends all outputs, "merge_dict" deep-merges output dicts, or "custom" runs a merge function. **Example:** A research document is simultaneously analyzed by Analyzer, Extractor, Sentiment, and Summarizer. Speedup is near-linear with the number of parallel agents.',
    answer_es: 'La **topologia Paralela** usa un patron fan-out/fan-in: una entrada se envia a multiples agentes simultaneamente, luego los resultados se fusionan. **Cuando usar:** Cuando necesitas multiples analisis independientes del mismo documento. **Internamente:** asyncio.gather ejecuta todos los agentes concurrentemente. Estrategia de fusion configurable: "concat", "merge_dict" o "custom". **Ejemplo:** Un documento se analiza simultaneamente por Analizador, Extractor, Sentimiento y Resumidor.'
  },

  topology_hierarchical: {
    category: 'swarms',
    question_patterns: ['hierarchical topology', 'topologia jerarquica', 'hierarchical swarm', 'enjambre jerarquico', 'planner workers', 'planificador trabajadores', 'decompose task'],
    answer_en: 'The **Hierarchical topology** uses a three-phase approach: Plan -> Execute -> Synthesize. **Phase 1 (Plan):** The Planner agent receives the task and decomposes it into subtasks with dependencies and assigned agents. **Phase 2 (Execute):** Worker agents execute their assigned subtasks -- independent subtasks run in parallel, dependent ones wait. **Phase 3 (Synthesize):** A synthesizer agent combines all worker outputs into a coherent final result. **When to use:** Complex, multi-faceted tasks that benefit from divide-and-conquer. **Example:** "Analyze this 50-page contract" -> Planner creates 6 subtasks -> Workers execute -> Synthesizer produces a unified contract analysis report.',
    answer_es: 'La **topologia Jerarquica** usa un enfoque de tres fases: Planificar -> Ejecutar -> Sintetizar. **Fase 1:** El Planificador descompone la tarea en subtareas. **Fase 2:** Los trabajadores ejecutan subtareas, las independientes corren en paralelo. **Fase 3:** Un sintetizador combina todas las salidas en un resultado final coherente. **Cuando usar:** Tareas complejas que se benefician de dividir y conquistar.'
  },

  topology_debate: {
    category: 'swarms',
    question_patterns: ['debate topology', 'topologia debate', 'debate swarm', 'enjambre debate', 'iterative improvement', 'mejora iterativa', 'agent critic loop'],
    answer_en: 'The **Debate topology** creates an iterative improvement loop between a producer agent and the Critic agent. **How it works:** (1) The producer agent generates initial output. (2) The Critic agent evaluates it, scoring 0-100 with specific feedback. (3) If the score is below the quality threshold (default 75), the producer receives the critique and generates an improved version. (4) This loop repeats until the score passes the threshold or max iterations (default 3) are reached. **When to use:** Tasks where quality is critical and iterative refinement adds value, like content generation or complex analysis. **Example:** Summarizer produces a report -> Critic scores it 62 ("missing financial details") -> Summarizer revises -> Critic scores 81 ("comprehensive, clear") -> Output accepted. Typical improvement is 15-25 points between first and final iteration.',
    answer_es: 'La **topologia de Debate** crea un ciclo de mejora iterativa entre un agente productor y el agente Critico. **Como funciona:** (1) El productor genera salida inicial. (2) El Critico la evalua, puntuando 0-100. (3) Si la puntuacion esta bajo el umbral (default 75), el productor recibe la critica y genera una version mejorada. (4) El ciclo se repite hasta pasar el umbral o alcanzar maximo de iteraciones (default 3). **Ejemplo:** Resumidor produce informe -> Critico puntua 62 -> Resumidor revisa -> Critico puntua 81 -> Salida aceptada. Mejora tipica de 15-25 puntos entre primera y ultima iteracion.'
  },

  topology_consensus: {
    category: 'swarms',
    question_patterns: ['consensus topology', 'topologia consenso', 'consensus swarm', 'enjambre consenso', 'voting', 'votacion', 'judge', 'juez', 'multiple opinions'],
    answer_en: 'The **Consensus topology** gathers multiple independent opinions and selects the best. **How it works:** (1) N agents (typically 3-5) receive the same task independently -- they don\'t see each other\'s work. (2) Each agent produces its output. (3) A Judge agent (usually the Critic) evaluates all outputs, scoring each one. (4) The Judge selects the winner based on highest score and writes a justification. **When to use:** High-stakes decisions where you want to reduce bias and increase reliability. **Example:** 3 Analyzer agents independently assess a financial report -> Judge evaluates all three -> Selects the most thorough analysis -> Confidence increases from ~80% (single agent) to ~95% (consensus). The tradeoff is 3x the token cost for significantly higher reliability.',
    answer_es: 'La **topologia de Consenso** reune multiples opiniones independientes y selecciona la mejor. **Como funciona:** (1) N agentes reciben la misma tarea independientemente. (2) Cada agente produce su salida. (3) Un agente Juez evalua todas las salidas. (4) El Juez selecciona la ganadora con justificacion. **Cuando usar:** Decisiones de alto riesgo donde quieres reducir sesgo. **Ejemplo:** 3 Analizadores evaluan un informe -> Juez selecciona el mas completo -> Confianza aumenta de ~80% a ~95%. El tradeoff es 3x el costo de tokens.'
  },

  topology_adaptive: {
    category: 'swarms',
    question_patterns: ['adaptive topology', 'topologia adaptiva', 'adaptive swarm', 'enjambre adaptivo', 'dynamic topology', 'topologia dinamica', 'auto select', 'auto seleccionar'],
    answer_en: 'The **Adaptive topology** is the most intelligent pattern -- it dynamically selects the best topology based on task analysis. **How it works:** (1) The Router agent analyzes the incoming task for complexity, type, time constraints, and quality requirements. (2) Based on this analysis, it selects one of the other 5 topologies. (3) The selected topology executes normally. **Selection logic:** Simple tasks -> Sequential. Independent multi-analysis -> Parallel. Complex decomposable tasks -> Hierarchical. Quality-critical content -> Debate. High-stakes decisions -> Consensus. **When to use:** When you have diverse task types and don\'t want to manually select topologies. The adaptive topology adds ~500ms overhead for the routing decision but ensures optimal execution patterns. It learns from past executions via episodic memory to improve routing over time.',
    answer_es: 'La **topologia Adaptiva** es el patron mas inteligente -- selecciona dinamicamente la mejor topologia basandose en analisis de la tarea. **Como funciona:** (1) El agente Router analiza la tarea. (2) Selecciona una de las otras 5 topologias. (3) La topologia seleccionada ejecuta normalmente. **Logica de seleccion:** Tareas simples -> Secuencial. Multi-analisis independiente -> Paralelo. Tareas complejas -> Jerarquico. Calidad critica -> Debate. Decisiones de alto riesgo -> Consenso. **Cuando usar:** Cuando tienes diversos tipos de tareas. Agrega ~500ms de overhead pero asegura patrones optimos.'
  },

  // ═══════════════════════════════════════════
  // MEMORY SYSTEM
  // ═══════════════════════════════════════════

  memory_overview: {
    category: 'memory',
    question_patterns: ['memory', 'memoria', 'memory system', 'sistema de memoria', 'how memory works', 'como funciona la memoria', 'remember', 'recordar', 'context', 'contexto', '3 tier', '3 niveles'],
    answer_en: 'NexusForge uses a **3-tier memory system** designed to give agents both short-term context and long-term learning capabilities. **Working Memory** holds the current task context in-process. **Episodic Memory** stores task summaries and patterns in Redis with a 30-day TTL. **Semantic Memory** embeds knowledge as 512-dimensional vectors in pgvector for permanent cross-agent sharing. The three tiers work together: working memory provides immediate context, episodic memory lets agents learn from recent successes and failures, and semantic memory gives access to the organization\'s accumulated knowledge. This mirrors how human memory works -- short-term (working), medium-term (episodic), and long-term (semantic).',
    answer_es: 'NexusForge usa un **sistema de memoria de 3 niveles** disenado para dar a los agentes contexto a corto plazo y aprendizaje a largo plazo. **Memoria de Trabajo** mantiene el contexto actual en proceso. **Memoria Episodica** almacena resumenes de tareas en Redis con TTL de 30 dias. **Memoria Semantica** embebe conocimiento como vectores de 512 dimensiones en pgvector permanentemente. Los tres niveles trabajan juntos: la de trabajo provee contexto inmediato, la episodica permite aprender de exitos y fallos recientes, y la semantica da acceso al conocimiento acumulado.'
  },

  working_memory: {
    category: 'memory',
    question_patterns: ['working memory', 'memoria de trabajo', 'short term', 'corto plazo', 'current context', 'contexto actual', 'in process memory'],
    answer_en: '**Working Memory** is the fastest tier, stored entirely in-process (Python dict). It holds: the current task description, the last 20 messages in the conversation/execution chain, intermediate results from previous steps, and agent configuration for the current run. Working memory is scoped to a single execution -- when the workflow completes, it is discarded. Access latency is sub-millisecond since it is just a Python dictionary. Maximum capacity is approximately 50KB of context data per execution. Working memory allows agents within the same workflow to pass rich context to each other without database round-trips.',
    answer_es: '**Memoria de Trabajo** es el nivel mas rapido, almacenado en proceso (dict de Python). Mantiene: descripcion de tarea actual, ultimos 20 mensajes, resultados intermedios de pasos anteriores y configuracion del agente. Tiene alcance de una sola ejecucion -- al completar el workflow, se descarta. La latencia es sub-milisegundo. Capacidad maxima de aproximadamente 50KB por ejecucion.'
  },

  episodic_memory: {
    category: 'memory',
    question_patterns: ['episodic memory', 'memoria episodica', 'task history', 'historial de tareas', 'redis memory', 'learning from past', 'aprender del pasado'],
    answer_en: '**Episodic Memory** stores structured records of past executions in Redis with a 30-day TTL. Each episode contains: task type, agent used, input summary, output summary, success/failure status, error details if failed, execution duration, and token cost. Agents query episodic memory before execution to find similar past tasks. If a similar task succeeded before, the agent can reference that approach. If it failed, the agent avoids the same pitfalls. Episodic memory is stored as Redis Hashes with indexes on task_type and agent_name for fast lookups. Typical query latency is 2-5ms.',
    answer_es: '**Memoria Episodica** almacena registros estructurados de ejecuciones pasadas en Redis con TTL de 30 dias. Cada episodio contiene: tipo de tarea, agente usado, resumen de entrada/salida, estado exito/fallo, detalles de error, duracion y costo de tokens. Los agentes consultan la memoria episodica antes de ejecutar para encontrar tareas similares. Latencia tipica de 2-5ms.'
  },

  semantic_memory: {
    category: 'memory',
    question_patterns: ['semantic memory', 'memoria semantica', 'vector memory', 'memoria vectorial', 'pgvector memory', 'long term', 'largo plazo', 'permanent memory'],
    answer_en: '**Semantic Memory** is the permanent knowledge layer, using Voyage AI to embed text into 512-dimensional vectors stored in PostgreSQL\'s pgvector extension. It stores: document chunks from the RAG pipeline, agent-generated insights, cross-execution knowledge summaries, and organizational knowledge base entries. Queries use cosine similarity to find the most relevant vectors. Semantic memory has no TTL -- knowledge persists indefinitely. It enables cross-agent knowledge sharing: when one agent discovers something important, it can store it for all other agents to access. Typical query returns top-5 results in under 10ms. Vectors are indexed using IVFFlat for efficient approximate nearest neighbor search.',
    answer_es: '**Memoria Semantica** es la capa de conocimiento permanente, usando Voyage AI para embeber texto en vectores de 512 dimensiones almacenados en pgvector de PostgreSQL. Almacena: fragmentos de documentos del pipeline RAG, insights de agentes, resumenes de conocimiento y entradas de la base de conocimiento. Las consultas usan similitud coseno. No tiene TTL -- el conocimiento persiste indefinidamente. Permite compartir conocimiento entre agentes. Usa indices IVFFlat para busqueda eficiente.'
  },

  // ═══════════════════════════════════════════
  // SELF-HEALING
  // ═══════════════════════════════════════════

  healing_overview: {
    category: 'healing',
    question_patterns: ['self-healing', 'auto-reparacion', 'self healing', 'healing system', 'sistema de reparacion', 'error recovery', 'recuperacion de errores', 'automatic recovery', 'recuperacion automatica', 'heal'],
    answer_en: 'NexusForge\'s **self-healing engine** automatically detects, diagnoses, and recovers from failures without human intervention. In production AI systems, failures are inevitable -- LLM APIs go down, rate limits hit, data quality varies, and schemas change. The self-healing system addresses this with three components: (1) **FailureDetector** classifies errors into 6 types, (2) **StrategySelector** picks the optimal recovery approach from 5 strategies, (3) **RecoveryExecutor** applies the strategy and verifies success. The system reduces mean-time-to-recovery from hours (manual) to seconds (automatic). It maintains a healing log for post-mortem analysis and feeds recovery patterns back into episodic memory so the system improves over time.',
    answer_es: 'El **motor de auto-reparacion** de NexusForge detecta, diagnostica y recupera automaticamente de fallas sin intervencion humana. El sistema tiene tres componentes: (1) **FailureDetector** clasifica errores en 6 tipos, (2) **StrategySelector** elige la estrategia optima de 5 opciones, (3) **RecoveryExecutor** aplica la estrategia y verifica exito. Reduce el tiempo de recuperacion de horas a segundos y alimenta patrones a la memoria episodica.'
  },

  error_detection: {
    category: 'healing',
    question_patterns: ['error types', 'tipos de error', 'failure detection', 'deteccion de fallos', 'error classification', 'clasificacion de errores', 'what errors', 'que errores'],
    answer_en: 'The **FailureDetector** classifies errors into 6 categories:\n\n1. **Network errors** -- Connection timeouts, DNS failures, TLS handshake errors. Recovery: retry with exponential backoff.\n2. **Timeout errors** -- Agent took too long. Recovery: retry with reduced input or increased timeout.\n3. **Data quality errors** -- Invalid input format, missing fields, corrupt data. Recovery: repair agent normalizes input.\n4. **LLM errors** -- Rate limiting (429), context length exceeded, content filter triggered. Recovery: switch provider or reduce prompt.\n5. **Schema errors** -- Agent output doesn\'t match expected schema. Recovery: repair agent reformats output.\n6. **System errors** -- Out of memory, disk full, Redis connection lost. Recovery: escalate to human.\n\nEach error is logged with full context for debugging.',
    answer_es: 'El **FailureDetector** clasifica errores en 6 categorias:\n\n1. **Errores de red** -- Timeouts, fallos DNS, errores TLS. Recuperacion: reintento con backoff.\n2. **Errores de timeout** -- Agente tardo demasiado. Recuperacion: reintento con entrada reducida.\n3. **Errores de calidad de datos** -- Formato invalido, campos faltantes. Recuperacion: agente reparador normaliza.\n4. **Errores LLM** -- Rate limiting (429), contexto excedido, filtro de contenido. Recuperacion: cambiar proveedor.\n5. **Errores de esquema** -- Salida no coincide con esquema. Recuperacion: agente reparador reformatea.\n6. **Errores de sistema** -- Sin memoria, disco lleno, Redis caido. Recuperacion: escalar a humano.'
  },

  healing_strategies: {
    category: 'healing',
    question_patterns: ['healing strategies', 'estrategias de reparacion', 'recovery strategies', 'estrategias de recuperacion', '5 strategies', '5 estrategias', 'retry skip repair', 'how does healing work'],
    answer_en: 'The self-healing engine uses **5 recovery strategies**, selected based on error type and context:\n\n1. **Retry** -- Re-run the same step with modified parameters. Uses exponential backoff with jitter (base 2s, max 30s). For: network errors, timeouts, rate limits. Max 3 retries.\n2. **Skip** -- Generate a default/empty output and continue the pipeline. When: the step is optional or downstream steps can handle missing data. Marks output as "degraded."\n3. **Repair** -- The Repair Agent diagnoses the failure and suggests config changes. For: data quality errors, schema mismatches. May reduce input size, change output format, or adjust parameters.\n4. **Escalate** -- Route to human review queue when automatic recovery is impossible. For: system errors, repeated failures, security issues. Creates a detailed incident report.\n5. **Fallback** -- Use cached results from a previous successful execution of the same step with similar input. When: a recent cache exists and input similarity exceeds 0.85.',
    answer_es: 'El motor usa **5 estrategias de recuperacion**:\n\n1. **Reintento** -- Re-ejecutar con parametros modificados. Backoff exponencial (base 2s, max 30s). Para: errores de red, timeouts. Max 3 reintentos.\n2. **Omitir** -- Generar salida por defecto y continuar. Cuando: el paso es opcional.\n3. **Reparar** -- El Agente de Reparacion diagnostica y sugiere cambios. Para: errores de calidad de datos, esquemas incorrectos.\n4. **Escalar** -- Enviar a cola de revision humana. Para: errores de sistema, fallos repetidos.\n5. **Respaldo** -- Usar resultados en cache de una ejecucion exitosa previa (similitud > 0.85).'
  },

  healing_example: {
    category: 'healing',
    question_patterns: ['healing example', 'ejemplo de reparacion', 'healing walkthrough', 'show me healing', 'muestrame reparacion', 'healing in action', 'concrete example'],
    answer_en: 'Here is a concrete self-healing walkthrough:\n\n**Scenario:** A document processing workflow runs. Step 3 (Summarizer) fails.\n\n**1. Detection:** FailureDetector receives: "Context length exceeded: 128K tokens." Classified as **LLM error**.\n\n**2. Strategy Selection:** For LLM context errors, the selector picks **Repair** strategy.\n\n**3. Repair Agent runs:** Diagnosis: "Input document too large for single-pass summarization." Suggested fix: `{"max_input_chars": 5000, "strategy": "chunk_and_merge"}`. can_auto_fix: true.\n\n**4. Recovery:** Executor applies config changes and re-runs. This time it chunks the document into 5000-char segments, summarizes each, then merges.\n\n**5. Success:** Summarizer completes with score 78/100. The healing event is logged and stored in episodic memory. Next time a similar large document appears, the system proactively applies chunking.\n\n**Total recovery time:** 4.2 seconds (vs hours for manual debugging).',
    answer_es: 'Ejemplo concreto de auto-reparacion:\n\n**Escenario:** Un workflow falla en el Paso 3 (Resumidor).\n\n**1. Deteccion:** Error: "Longitud de contexto excedida: 128K tokens." Clasificado como **error LLM**.\n\n**2. Seleccion de estrategia:** Se selecciona **Reparar**.\n\n**3. Agente de Reparacion:** Diagnostico: "Documento demasiado grande." Correccion: `{"max_input_chars": 5000, "strategy": "chunk_and_merge"}`. can_auto_fix: true.\n\n**4. Recuperacion:** Se aplican cambios y se re-ejecuta. Fragmenta el documento y fusiona resumenes.\n\n**5. Exito:** Completado con puntuacion 78/100. El evento se registra en memoria episodica.\n\n**Tiempo total de recuperacion:** 4.2 segundos.'
  },

  // ═══════════════════════════════════════════
  // TECHNICAL DETAILS
  // ═══════════════════════════════════════════

  llm_router: {
    category: 'technical',
    question_patterns: ['llm router', 'router llm', 'multi provider', 'multi proveedor', 'groq claude', 'circuit breaker', 'llm routing', 'enrutamiento llm', 'which llm', 'que llm'],
    answer_en: 'The **LLM Router** manages multi-provider model access with intelligent failover. **Primary: Groq** running Llama 3.3 70B -- extremely fast (200+ tokens/sec) and 40x cheaper than Claude. **Fallback: Claude Sonnet** -- higher quality for complex reasoning. The router implements a **circuit breaker pattern**: when Groq errors exceed 50% in a 60-second window, the circuit "opens" and all requests route to Claude. After a 30-second cooldown, a probe request tests Groq -- if it succeeds, the circuit "closes" and Groq resumes. This prevents cascading failures. The router also tracks per-request cost (input/output tokens x price) and adds it to execution metadata.',
    answer_es: 'El **Router LLM** gestiona acceso multi-proveedor con failover inteligente. **Primario: Groq** con Llama 3.3 70B -- extremadamente rapido (200+ tokens/seg) y 40x mas barato que Claude. **Respaldo: Claude Sonnet** -- mayor calidad para razonamiento complejo. Implementa un **patron circuit breaker**: cuando los errores de Groq exceden 50% en 60 segundos, el circuito se "abre" y todo va a Claude. Despues de 30 segundos, una prueba verifica Groq. Tambien rastrea costo por solicitud.'
  },

  rag_pipeline: {
    category: 'technical',
    question_patterns: ['rag', 'rag pipeline', 'pipeline rag', 'retrieval augmented', 'generacion aumentada', 'vector search', 'busqueda vectorial', 'document search', 'busqueda documentos', 'embedding', 'embeddings'],
    answer_en: 'The **RAG pipeline** (Retrieval-Augmented Generation) gives agents access to your documents:\n\n**1. Upload:** Document received via API or UI upload.\n**2. Chunk:** Text split into 500-character segments with 50-character overlap.\n**3. Embed:** Each chunk embedded using Voyage AI voyage-3-lite (512-dimensional vectors).\n**4. Store:** Vectors stored in PostgreSQL using pgvector extension with IVFFlat indexing.\n**5. Search:** Query embedded -> cosine similarity finds top-K most relevant chunks.\n**6. Augment:** Retrieved chunks injected into the agent\'s prompt as context.\n\nSupports PDF, TXT, DOCX, and Markdown. Typical end-to-end latency from upload to searchable is under 5 seconds for a 10-page document.',
    answer_es: 'El **pipeline RAG** (Generacion Aumentada por Recuperacion):\n\n**1. Subir:** Documento recibido via API o UI.\n**2. Fragmentar:** Texto dividido en segmentos de 500 caracteres con 50 de solapamiento.\n**3. Embeber:** Cada fragmento embebido con Voyage AI voyage-3-lite (vectores 512d).\n**4. Almacenar:** Vectores en PostgreSQL con pgvector, indexados con IVFFlat.\n**5. Buscar:** Consulta embebida -> similitud coseno encuentra top-K fragmentos.\n**6. Aumentar:** Fragmentos inyectados en el prompt del agente como contexto.\n\nSoporta PDF, TXT, DOCX y Markdown. Latencia menor a 5 segundos para 10 paginas.'
  },

  cost_tracking: {
    category: 'technical',
    question_patterns: ['cost', 'costo', 'price', 'precio', 'token', 'tokens', 'how much', 'cuanto cuesta', 'pricing', 'precios', 'cost tracking', 'seguimiento de costos'],
    answer_en: '**Cost tracking** is built into every agent execution:\n\n**Groq (Llama 3.3 70B):** $0.59 per million input tokens, $0.79 per million output tokens. Average agent call: ~$0.0008.\n**Claude Sonnet:** $3.00 per million input tokens, $15.00 per million output tokens. Average agent call: ~$0.0084.\n\nThe router tries **Groq first** (40x cheaper), falling back to Claude only when needed. A typical 5-step workflow costs ~$0.004 on Groq vs ~$0.042 on Claude. The Analytics dashboard shows cost breakdown by agent, workflow, time period, and LLM provider. Monthly cost projections are calculated from trailing 7-day averages.',
    answer_es: '**Seguimiento de costos** integrado en cada ejecucion:\n\n**Groq (Llama 3.3 70B):** $0.59/M tokens entrada, $0.79/M salida. Llamada promedio: ~$0.0008.\n**Claude Sonnet:** $3.00/M entrada, $15.00/M salida. Llamada promedio: ~$0.0084.\n\nEl router intenta **Groq primero** (40x mas barato). Un workflow tipico de 5 pasos cuesta ~$0.004 en Groq vs ~$0.042 en Claude. El dashboard muestra desglose por agente, workflow, periodo y proveedor.'
  },

  infrastructure: {
    category: 'technical',
    question_patterns: ['infrastructure', 'infraestructura', 'docker', 'kubernetes', 'k8s', 'terraform', 'aws', 'grafana', 'prometheus', 'deploy', 'despliegue', 'deployment', 'monitoring', 'observability'],
    answer_en: '**Infrastructure stack:**\n\n**Containerization:** Docker Compose for local dev, multi-stage builds for production.\n**Orchestration:** Kubernetes with Helm charts. HPA auto-scales API pods. Separate worker pool for agent execution.\n**IaC:** Terraform modules for AWS -- EKS cluster, RDS (PostgreSQL), ElastiCache (Redis), ALB, Route53, ACM.\n**Observability:** Prometheus scrapes metrics from FastAPI `/metrics` endpoint. **5 Grafana dashboards:** System Overview, Agent Performance, Workflow Execution, Cost Analytics, Error Rates. **Loki** aggregates logs. **AlertManager** has **14 alert rules** covering: high error rates, latency spikes, memory pressure, queue depth, circuit breaker state, cost thresholds.\n**CI/CD:** GitHub Actions runs 231 tests, linting, type checking, and Docker build on every PR.',
    answer_es: '**Stack de infraestructura:**\n\n**Contenedores:** Docker Compose para dev, builds multi-etapa para produccion.\n**Orquestacion:** Kubernetes con Helm. HPA auto-escala pods. Pool de workers separado.\n**IaC:** Terraform para AWS -- EKS, RDS, ElastiCache, ALB, Route53, ACM.\n**Observabilidad:** Prometheus recopila metricas. **5 dashboards Grafana.** **Loki** agrega logs. **AlertManager** tiene **14 reglas de alerta**.\n**CI/CD:** GitHub Actions ejecuta 231 tests, linting, type checking y Docker build en cada PR.'
  },

  testing: {
    category: 'technical',
    question_patterns: ['test', 'testing', 'pytest', 'pruebas', 'tests', 'quality', 'coverage', 'test suite', 'suite de pruebas', '231 tests'],
    answer_en: '**Testing strategy** with **231 pytest tests** across all modules:\n\n**Unit tests (~140):** Agent logic, DAG engine topological sort, memory tier operations, LLM router with mock providers, circuit breaker state transitions, cost calculation.\n**Integration tests (~60):** API endpoints with FastAPI TestClient, WebSocket connection and events, Redis pub/sub flow, pgvector similarity search, checkpoint save/restore.\n**E2E tests (~31):** Complete workflow execution with all 6 topologies, self-healing recovery scenarios, document upload through RAG pipeline to search, multi-agent swarm collaboration.\n**Fixtures:** Mock LLM responses for deterministic testing without API calls. All 22 agent response formats covered.\n**CI/CD:** GitHub Actions runs `pytest --cov=nexusforge tests/` on every PR. Coverage target: 85%+.',
    answer_es: '**Estrategia de testing** con **231 tests pytest**:\n\n**Tests unitarios (~140):** Logica de agentes, motor DAG, operaciones de memoria, router LLM con mocks, circuit breaker.\n**Tests de integracion (~60):** Endpoints API, WebSocket, Redis pub/sub, busqueda pgvector.\n**Tests E2E (~31):** Ejecucion completa con 6 topologias, escenarios de auto-reparacion, pipeline RAG completo.\n**Fixtures:** Respuestas LLM simuladas para testing determinista.\n**CI/CD:** GitHub Actions ejecuta `pytest --cov=nexusforge tests/` en cada PR. Meta: 85%+.'
  },

  sdk: {
    category: 'technical',
    question_patterns: ['sdk', 'typescript sdk', 'javascript sdk', 'client library', 'libreria cliente', 'npm package', '@nexusforge/sdk'],
    answer_en: '**@nexusforge/sdk** -- Full-featured TypeScript SDK:\n\n**Type safety:** Complete TypeScript definitions for all API types.\n**Agent execution:** `client.agents.run("classifier", { text: "..." })` with streaming support.\n**Workflow builder:** Fluent API: `new WorkflowBuilder().addStep("classify", "classifier").addStep("extract", "extractor", { dependsOn: ["classify"] }).build()`.\n**WebSocket:** `client.executions.watch(runId)` returns real-time event stream.\n**Automatic retry:** Built-in retry with exponential backoff.\n**Both environments:** Works in Node.js (16+) and modern browsers.\n\nInstall: `npm install @nexusforge/sdk`',
    answer_es: '**@nexusforge/sdk** -- SDK TypeScript completo:\n\n**Type safety:** Definiciones TypeScript completas.\n**Ejecucion de agentes:** `client.agents.run("classifier", { text: "..." })` con streaming.\n**Constructor de workflows:** API fluida con WorkflowBuilder.\n**WebSocket:** `client.executions.watch(runId)` para eventos en tiempo real.\n**Reintento automatico:** Con backoff exponencial.\n\nInstalar: `npm install @nexusforge/sdk`'
  },

  cli: {
    category: 'technical',
    question_patterns: ['cli', 'command line', 'terminal', 'nxf', 'commands', 'comandos', 'nxf command', 'linea de comandos'],
    answer_en: '**NexusForge CLI** (`nxf`) -- 13 commands:\n\n`nxf init` -- Initialize project\n`nxf agent list` -- List all 22 agents\n`nxf agent run <name>` -- Run a specific agent\n`nxf workflow create` -- Create from template or JSON\n`nxf workflow run <id>` -- Execute and stream progress\n`nxf workflow status <id>` -- Check execution status\n`nxf swarm launch` -- Launch a swarm topology\n`nxf doc upload <file>` -- Upload to RAG pipeline\n`nxf doc search <query>` -- Semantic search\n`nxf plugin install <name>` -- Install plugin\n`nxf config set <key> <val>` -- Update config\n`nxf logs <run_id>` -- View execution logs\n`nxf health` -- System health check\n\nAll commands support `--json` for machine-readable output and `--verbose` for debug logging.',
    answer_es: '**CLI de NexusForge** (`nxf`) -- 13 comandos:\n\n`nxf init` -- Inicializar proyecto\n`nxf agent list` -- Listar los 22 agentes\n`nxf agent run <nombre>` -- Ejecutar un agente\n`nxf workflow create` -- Crear desde plantilla o JSON\n`nxf workflow run <id>` -- Ejecutar y transmitir progreso\n`nxf workflow status <id>` -- Ver estado de ejecucion\n`nxf swarm launch` -- Lanzar topologia de enjambre\n`nxf doc upload <archivo>` -- Subir al pipeline RAG\n`nxf doc search <consulta>` -- Busqueda semantica\n`nxf plugin install <nombre>` -- Instalar plugin\n`nxf config set <clave> <valor>` -- Actualizar configuracion\n`nxf logs <run_id>` -- Ver logs\n`nxf health` -- Verificar salud del sistema\n\nTodos soportan `--json` y `--verbose`.'
  },

  plugins: {
    category: 'technical',
    question_patterns: ['plugin', 'plugins', 'extension', 'extensiones', 'marketplace', 'custom agents', 'agentes personalizados', 'extend', 'extender'],
    answer_en: '**Plugin system** with the NexusPlugin interface:\n\n**Architecture:** Plugins are Python packages implementing `NexusPlugin`. Dynamically loaded via importlib. Each has a manifest (plugin.json) with name, version, description, author.\n\n**What plugins add:** Custom agents (extending BaseAgent), data connectors (new document sources), processing pipelines (pre/post hooks), and UI components.\n\n**Built-in plugins:** **gov-data-mx** -- connects to Mexico government open data APIs. **gov-data-us** -- connects to US government data portals (data.gov, Census, SEC).\n\n**Creating a plugin:** Implement `NexusPlugin`, define `register_agents()` and `register_connectors()`, add plugin.json, install via `nxf plugin install <path>`.',
    answer_es: '**Sistema de plugins** con interfaz NexusPlugin:\n\n**Arquitectura:** Plugins son paquetes Python que implementan `NexusPlugin`. Carga dinamica via importlib. Cada uno tiene manifiesto (plugin.json).\n\n**Que agregan:** Agentes personalizados, conectores de datos, pipelines de procesamiento y componentes UI.\n\n**Plugins incluidos:** **gov-data-mx** -- datos gobierno Mexico. **gov-data-us** -- datos gobierno EEUU.\n\n**Crear un plugin:** Implementar `NexusPlugin`, definir `register_agents()` y `register_connectors()`, agregar plugin.json, instalar via `nxf plugin install`.'
  },

  architecture_decisions: {
    category: 'technical',
    question_patterns: ['architecture decisions', 'decisiones de arquitectura', 'why pgvector', 'por que pgvector', 'why redis', 'por que redis', 'design choices', 'design decisions', 'trade-offs', 'tradeoffs', 'adr'],
    answer_en: '**Key architecture decisions:**\n\n**pgvector over Qdrant/Pinecone:** Lives inside PostgreSQL -- one less service, ACID transactions, existing team expertise. Tradeoff: slightly lower throughput at 10M+ vectors, but NexusForge targets under 1M where pgvector excels.\n\n**Redis over Kafka:** Redis Streams provide ordered, persistent queues with consumer groups -- sufficient for NexusForge\'s throughput. Also serves as cache and pub/sub, reducing infrastructure.\n\n**FastAPI over Django:** Async-first framework pairs naturally with asyncio.gather for parallel agent execution.\n\n**Groq primary over Claude primary:** 40x cost reduction with acceptable quality for most tasks. Claude reserved for complex reasoning.',
    answer_es: '**Decisiones de arquitectura clave:**\n\n**pgvector sobre Qdrant/Pinecone:** Vive dentro de PostgreSQL -- un servicio menos, transacciones ACID. Tradeoff: menor throughput a 10M+ vectores.\n\n**Redis sobre Kafka:** Redis Streams provee colas ordenadas y persistentes -- suficiente para NexusForge. Tambien sirve como cache y pub/sub.\n\n**FastAPI sobre Django:** Framework async-first, ideal con asyncio.gather.\n\n**Groq primario sobre Claude primario:** 40x reduccion de costos con calidad aceptable.'
  },

  security: {
    category: 'technical',
    question_patterns: ['security', 'seguridad', 'auth', 'authentication', 'autenticacion', 'authorization', 'autorizacion', 'jwt', 'rbac', 'permissions', 'permisos'],
    answer_en: '**Security features:**\n\n**Authentication:** JWT tokens with refresh rotation. Access tokens expire in 15 minutes, refresh in 7 days.\n**Authorization:** RBAC with three roles -- Admin (full access), Operator (run workflows, manage docs), Viewer (read-only). Per-workflow and per-agent permissions.\n**API Security:** Rate limiting (100 req/min), CORS whitelist, Pydantic validation, parameterized queries.\n**Data:** Encryption at rest (AES-256), in transit (TLS 1.3), API keys as bcrypt hashes.\n**Secrets:** Environment variables for dev, Kubernetes Secrets in production.\n**Audit:** Complete audit log of all executions, admin actions, document access. Immutable, 90-day retention.',
    answer_es: '**Caracteristicas de seguridad:**\n\n**Autenticacion:** JWT con rotacion de refresh tokens. Access tokens 15 min, refresh 7 dias.\n**Autorizacion:** RBAC con tres roles -- Admin, Operador, Visualizador. Permisos por workflow y por agente.\n**Seguridad API:** Rate limiting (100 req/min), CORS, validacion Pydantic.\n**Datos:** Cifrado en reposo (AES-256), en transito (TLS 1.3), claves API como hashes bcrypt.\n**Secretos:** Variables de entorno para dev, Kubernetes Secrets en produccion.\n**Auditoria:** Log completo de ejecuciones y acciones admin. Inmutable, 90 dias de retencion.'
  },

  comparison: {
    category: 'technical',
    question_patterns: ['compare', 'comparison', 'comparar', 'comparacion', 'vs', 'langchain', 'crewai', 'n8n', 'autogen', 'alternative', 'alternativa', 'diferencia'],
    answer_en: '**NexusForge vs alternatives:**\n\n**vs LangChain:** LangChain is a library; NexusForge is a complete platform with orchestration, 3-tier memory, self-healing, monitoring, and full UI.\n\n**vs CrewAI:** NexusForge offers 6 topologies (CrewAI has 2), 3-tier memory (vs single), self-healing with 5 strategies, and enterprise features like RBAC, audit logs, cost tracking.\n\n**vs n8n/Zapier:** NexusForge is AI-native -- agents reason, adapt, and learn. Supports multi-agent collaboration patterns beyond simple automation.\n\n**vs AutoGen:** NexusForge adds production infrastructure: DAG execution, checkpointing, monitoring, cost tracking, plugin system, and Kubernetes-ready deployment.\n\n**Key differentiators:** Self-healing, 22 specialized agents, adaptive topology, enterprise observability, multi-provider LLM routing with circuit breaker.',
    answer_es: '**NexusForge vs alternativas:**\n\n**vs LangChain:** LangChain es una libreria; NexusForge es una plataforma completa con orquestacion, memoria, auto-reparacion, monitoreo y UI.\n\n**vs CrewAI:** NexusForge ofrece 6 topologias (CrewAI tiene 2), memoria de 3 niveles, auto-reparacion con 5 estrategias y funciones enterprise.\n\n**vs n8n/Zapier:** NexusForge es AI-nativo -- los agentes razonan, se adaptan y aprenden.\n\n**vs AutoGen:** NexusForge agrega infraestructura de produccion: ejecucion DAG, checkpointing, monitoreo, costos, plugins y despliegue Kubernetes.'
  },

  // ═══════════════════════════════════════════
  // ABOUT
  // ═══════════════════════════════════════════

  about_creator: {
    category: 'about',
    question_patterns: ['who built', 'quien construyo', 'creator', 'creador', 'author', 'autor', 'who made', 'christian', 'developer', 'desarrollador', 'about creator'],
    answer_en: 'NexusForge AI was built by **Christian Hernandez Escamilla**, an AI Engineer with 3+ years of experience specializing in AI automation, agent orchestration, and full-stack development. Christian uses **Claude Code** as his primary development tool for rapid prototyping and production-quality code generation. The entire NexusForge platform -- backend, frontend, infrastructure, tests, and documentation -- was architected and built as a showcase of enterprise-grade AI engineering. Portfolio: **https://ch65-portfolio.vercel.app**. The project demonstrates expertise in Python (FastAPI, asyncio), React, PostgreSQL, Redis, Kubernetes, Terraform, and modern AI/ML tooling.',
    answer_es: 'NexusForge AI fue construido por **Christian Hernandez Escamilla**, un Ingeniero de IA con 3+ anos de experiencia en automatizacion IA, orquestacion de agentes y desarrollo full-stack. Christian usa **Claude Code** como su herramienta principal de desarrollo. Toda la plataforma fue disenada y construida como demostracion de ingenieria IA de grado empresarial. Portafolio: **https://ch65-portfolio.vercel.app**.'
  },

  tech_stack: {
    category: 'about',
    question_patterns: ['tech stack', 'stack tecnologico', 'technologies', 'tecnologias', 'what tech', 'que tecnologias', 'tools used', 'herramientas', 'versions', 'versiones'],
    answer_en: '**Complete tech stack:**\n\n**Backend:** Python 3.11 + FastAPI 0.104 + asyncio + Pydantic v2 + SQLAlchemy 2.0\n**Frontend:** React 18.2 + Vite 5.0 + React Router 6 + Recharts + Framer Motion\n**Database:** PostgreSQL 15 + pgvector 0.5\n**Cache/Queues:** Redis 7.2 (Streams, pub/sub, Hashes)\n**LLM Providers:** Groq (Llama 3.3 70B) + Anthropic Claude Sonnet\n**Embeddings:** Voyage AI voyage-3-lite (512 dimensions)\n**Infrastructure:** Docker 24 + Kubernetes 1.28 + Helm 3\n**IaC:** Terraform 1.6 (AWS: EKS, RDS, ElastiCache, ALB, Route53)\n**Observability:** Prometheus 2.48 + Grafana 10.2 + Loki 2.9 + AlertManager\n**Testing:** pytest 7.4 + pytest-asyncio + pytest-cov\n**CI/CD:** GitHub Actions\n**SDK:** TypeScript 5.3 + Node.js 18+\n**CLI:** Python Click 8.1',
    answer_es: '**Stack tecnologico completo:**\n\n**Backend:** Python 3.11 + FastAPI 0.104 + asyncio + Pydantic v2 + SQLAlchemy 2.0\n**Frontend:** React 18.2 + Vite 5.0 + React Router 6 + Recharts + Framer Motion\n**Base de datos:** PostgreSQL 15 + pgvector 0.5\n**Cache/Colas:** Redis 7.2\n**Proveedores LLM:** Groq (Llama 3.3 70B) + Anthropic Claude Sonnet\n**Embeddings:** Voyage AI voyage-3-lite (512 dimensiones)\n**Infraestructura:** Docker 24 + Kubernetes 1.28 + Helm 3\n**IaC:** Terraform 1.6 (AWS)\n**Observabilidad:** Prometheus 2.48 + Grafana 10.2 + Loki 2.9\n**Testing:** pytest 7.4\n**CI/CD:** GitHub Actions\n**SDK:** TypeScript 5.3\n**CLI:** Python Click 8.1'
  },

  project_stats: {
    category: 'about',
    question_patterns: ['stats', 'estadisticas', 'numbers', 'numeros', 'how big', 'que tan grande', 'project size', 'tamano del proyecto', 'metrics', 'metricas', 'scope'],
    answer_en: '**NexusForge by the numbers:**\n\n**243 files** across backend, frontend, infrastructure, and tests\n**231 pytest tests** (unit, integration, E2E)\n**22 specialized AI agents** across 6 functional groups\n**6 swarm topologies** (sequential, parallel, hierarchical, debate, consensus, adaptive)\n**3 memory tiers** (working, episodic, semantic)\n**5 self-healing strategies** (retry, skip, repair, escalate, fallback)\n**10 database migrations** (Alembic)\n**5 Grafana dashboards** (System, Agents, Workflows, Costs, Errors)\n**14 AlertManager rules** for proactive monitoring\n**13 CLI commands** via the `nxf` tool\n**2 LLM providers** with circuit breaker failover\n**2 plugins** (gov-data-mx, gov-data-us)\n**1 TypeScript SDK** with full type coverage',
    answer_es: '**NexusForge en numeros:**\n\n**243 archivos** entre backend, frontend, infraestructura y tests\n**231 tests pytest** (unitarios, integracion, E2E)\n**22 agentes IA especializados** en 6 grupos funcionales\n**6 topologias de enjambre**\n**3 niveles de memoria**\n**5 estrategias de auto-reparacion**\n**10 migraciones de BD** (Alembic)\n**5 dashboards Grafana**\n**14 reglas de AlertManager**\n**13 comandos CLI** via `nxf`\n**2 proveedores LLM** con circuit breaker\n**2 plugins** (gov-data-mx, gov-data-us)\n**1 SDK TypeScript**'
  },

  help: {
    category: 'help',
    question_patterns: ['help', 'ayuda', 'what can you do', 'que puedes hacer', 'commands', 'options', 'opciones', 'menu', 'topics', 'temas'],
    answer_en: 'I can help you with everything about **NexusForge AI**! Topics by category:\n\n**Getting Started:** What is NexusForge | How it works | Use cases | Getting started guide\n**Agents (22):** Overview | Classifier | Extractor | Summarizer | Analyzer | Validator | Repair | Planner | Critic | Normalizer | Enricher | Researcher | Translator | Compliance | Monitor | Router | Knowledge | Scraper | OCR | Sentiment | Scheduler | Webhook\n**Workflows:** Introduction | DAG engine | Creating workflows | Execution flow | Checkpointing\n**Swarms:** Overview | Sequential | Parallel | Hierarchical | Debate | Consensus | Adaptive\n**Memory:** Overview | Working | Episodic | Semantic\n**Self-Healing:** Overview | Error detection | Recovery strategies | Example walkthrough\n**Technical:** LLM Router | RAG pipeline | Cost tracking | Infrastructure | Testing | SDK | CLI | Plugins | Architecture decisions | Security | Comparisons\n**About:** Creator | Tech stack | Project stats\n\nJust ask about any topic!',
    answer_es: 'Puedo ayudarte con todo sobre **NexusForge AI**! Temas por categoria:\n\n**Inicio:** Que es NexusForge | Como funciona | Casos de uso | Guia de inicio\n**Agentes (22):** Resumen | Clasificador | Extractor | Resumidor | Analizador | Validador | Reparacion | Planificador | Critico | Normalizador | Enriquecedor | Investigador | Traductor | Cumplimiento | Monitor | Router | Conocimiento | Scraper | OCR | Sentimiento | Programador | Webhook\n**Workflows:** Introduccion | Motor DAG | Crear workflows | Ejecucion | Checkpointing\n**Enjambres:** Resumen | Secuencial | Paralelo | Jerarquico | Debate | Consenso | Adaptivo\n**Memoria:** Resumen | Trabajo | Episodica | Semantica\n**Auto-reparacion:** Resumen | Deteccion | Estrategias | Ejemplo\n**Tecnico:** Router LLM | Pipeline RAG | Costos | Infraestructura | Testing | SDK | CLI | Plugins | Arquitectura | Seguridad | Comparaciones\n**Acerca de:** Creador | Stack tecnologico | Estadisticas\n\nPregunta sobre cualquier tema!'
  },
}

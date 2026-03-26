export const NEXUSFORGE_KB = {
  // GETTING STARTED
  what_is_nexusforge: {
    question_patterns: ['what is nexusforge', 'que es nexusforge', 'about', 'overview', 'para que sirve', 'explain nexusforge'],
    answer_en: 'NexusForge AI is an enterprise agent orchestration platform with 22 specialized AI agents, 6 swarm topologies (sequential, parallel, hierarchical, debate, consensus, adaptive), 3-tier memory system, self-healing with 5 strategies, and RAG pipeline with pgvector. Built with FastAPI, React, PostgreSQL, and Redis.',
    answer_es: 'NexusForge AI es una plataforma de orquestación de agentes empresarial con 22 agentes IA, 6 topologías de enjambre, sistema de memoria de 3 niveles, auto-reparación con 5 estrategias, y pipeline RAG con pgvector. Construido con FastAPI, React, PostgreSQL y Redis.'
  },

  how_it_works: {
    question_patterns: ['how does it work', 'como funciona', 'data flow', 'flujo de datos', 'how data flows'],
    answer_en: 'Documents upload → chunk (500 chars, 50 overlap) → embed with Voyage AI (512d) → store in pgvector. Workflows define DAG pipelines → executor uses Kahn\'s algorithm for topological sort → steps run sequentially or in parallel via asyncio.gather → each step invokes an agent through the LLM router (Groq→Claude fallback) → results checkpointed to Redis → events broadcast via WebSocket.',
    answer_es: 'Documentos se suben → se dividen en chunks (500 chars, 50 solapamiento) → se embeben con Voyage AI (512d) → se almacenan en pgvector. Los workflows definen pipelines DAG → el executor usa el algoritmo de Kahn → los pasos se ejecutan secuencial o paralelamente con asyncio.gather → cada paso invoca un agente via el router LLM (Groq→Claude fallback) → resultados en Redis → eventos via WebSocket.'
  },

  use_cases: {
    question_patterns: ['use cases', 'casos de uso', 'what can it do', 'que puede hacer', 'examples', 'ejemplos'],
    answer_en: 'Document processing pipelines (classify→extract→summarize→validate), compliance checking for regulatory documents, multi-source research with citations, data classification and deduplication, content generation with quality gates, multi-language translation workflows, and automated report generation.',
    answer_es: 'Pipelines de procesamiento de documentos (clasificar→extraer→resumir→validar), verificación de cumplimiento regulatorio, investigación multi-fuente con citas, clasificación y deduplicación de datos, generación de contenido con gates de calidad, traducción multi-idioma, y generación automática de reportes.'
  },

  getting_started: {
    question_patterns: ['getting started', 'como empezar', 'first steps', 'primeros pasos', 'tutorial', 'where to start'],
    answer_en: 'Start with Dashboard to see platform stats. Go to Workflows to see DAG pipelines — try the "Analisis de Documentos" template. Visit Agents to browse all 22 agents. Try Swarms to see 6 topologies in action. Upload a document in Documents to test the RAG pipeline. Use Memory to see the 3-tier system live.',
    answer_es: 'Empieza en el Panel Principal para ver estadísticas. Ve a Flujos de Trabajo para ver pipelines DAG — prueba la plantilla "Análisis de Documentos". Visita Agentes para ver los 22 agentes. Prueba Enjambres para ver las 6 topologías. Sube un documento para probar el pipeline RAG. Usa Memoria para ver el sistema de 3 niveles en vivo.'
  },

  // AGENTS
  agents_overview: {
    question_patterns: ['agents', 'agentes', 'how many agents', 'cuantos agentes', 'agent types', 'tipos de agentes', 'list agents'],
    answer_en: '22 specialized agents organized in 6 groups:\n• Data Processing: Classifier, Extractor, Normalizer, Validator\n• Analysis: Analyzer, Summarizer, Sentiment, Researcher\n• Intelligence: Planner, Router, Critic, Knowledge\n• Operations: Monitor, Repair, Scheduler, Webhook\n• Content: Reporter, Translator, OCR, Scraper\n• Quality: Enricher, Compliance\n\nEach uses the LLM router (Groq→Claude) with demo fallback mode.',
    answer_es: '22 agentes especializados en 6 grupos:\n• Procesamiento: Classifier, Extractor, Normalizer, Validator\n• Análisis: Analyzer, Summarizer, Sentiment, Researcher\n• Inteligencia: Planner, Router, Critic, Knowledge\n• Operaciones: Monitor, Repair, Scheduler, Webhook\n• Contenido: Reporter, Translator, OCR, Scraper\n• Calidad: Enricher, Compliance\n\nCada uno usa el router LLM (Groq→Claude) con modo demo fallback.'
  },

  classifier: {
    question_patterns: ['classifier', 'clasificador', 'classify', 'clasificar', 'document type', 'tipo de documento'],
    answer_en: 'The Classifier agent categorizes documents into: legal, financial, technical, medical, or general. It analyzes the first 500 characters using the LLM and returns category, confidence score (0-1), and reasoning for the classification.',
    answer_es: 'El agente Clasificador categoriza documentos en: legal, financiero, técnico, médico o general. Analiza los primeros 500 caracteres usando el LLM y devuelve categoría, score de confianza (0-1) y razonamiento.'
  },

  extractor: {
    question_patterns: ['extractor', 'extract', 'entities', 'entidades', 'ner', 'named entity'],
    answer_en: 'The Extractor agent pulls named entities from text: people, organizations, dates, monetary amounts, and locations. Returns a structured list with entity type, value, and surrounding context for each match.',
    answer_es: 'El agente Extractor identifica entidades nombradas del texto: personas, organizaciones, fechas, montos monetarios y ubicaciones. Devuelve una lista estructurada con tipo, valor y contexto.'
  },

  summarizer: {
    question_patterns: ['summarizer', 'resumir', 'summary', 'resumen', 'summarize'],
    answer_en: 'Generates summaries in 3 lengths: short (~50 words), medium (~150 words), or long (~300 words). Returns the summary text, an array of key points, and total word count.',
    answer_es: 'Genera resúmenes en 3 longitudes: corto (~50 palabras), medio (~150), o largo (~300). Devuelve el texto, un array de puntos clave y conteo de palabras.'
  },

  validator: {
    question_patterns: ['validator', 'validar', 'quality gate', 'validate', 'quality check'],
    answer_en: 'Quality gate agent that scores output 0-100. Checks completeness, consistency, and accuracy. Returns is_valid boolean, numeric score, issues array, and recommendations for improvement.',
    answer_es: 'Agente de quality gate que puntúa output 0-100. Verifica completitud, consistencia y precisión. Devuelve is_valid, score numérico, array de issues y recomendaciones.'
  },

  repair: {
    question_patterns: ['repair', 'reparar', 'self-heal', 'fix', 'auto-fix', 'diagnostico'],
    answer_en: 'Self-healing agent that diagnoses failures. Analyzes error messages and step configs. Returns diagnosis, fix_type (retry/reconfigure/skip/escalate), suggested config changes, and can_auto_fix boolean.',
    answer_es: 'Agente de auto-reparación que diagnostica fallos. Analiza mensajes de error y configs. Devuelve diagnóstico, tipo de fix (retry/reconfigurar/skip/escalar), cambios sugeridos y si puede auto-reparar.'
  },

  planner: {
    question_patterns: ['planner', 'planificador', 'plan', 'decompose', 'descomponer', 'subtasks'],
    answer_en: 'Decomposes complex tasks into subtasks with dependencies. Returns an execution plan with step name, assigned agent type, dependencies array, and priority level for each subtask.',
    answer_es: 'Descompone tareas complejas en subtareas con dependencias. Devuelve un plan de ejecución con nombre, agente asignado, dependencias y prioridad por subtarea.'
  },

  critic: {
    question_patterns: ['critic', 'critico', 'evaluate', 'evaluar', 'score', 'quality score'],
    answer_en: 'Evaluates output quality from other agents. Provides score 0-100, detailed critique, strengths array, improvements array, and pass/fail boolean (pass threshold: 70).',
    answer_es: 'Evalúa la calidad del output de otros agentes. Provee score 0-100, crítica detallada, fortalezas, mejoras sugeridas y pass/fail (umbral: 70).'
  },

  // WORKFLOWS & DAG
  workflows: {
    question_patterns: ['workflow', 'flujo', 'dag', 'pipeline', 'how workflows work', 'como funcionan los flujos'],
    answer_en: 'Workflows are DAG (Directed Acyclic Graph) pipelines where each node is an agent step. The DAG engine uses Kahn\'s algorithm for topological sorting, identifies parallel groups for simultaneous execution, detects cycles, and validates dependencies. Steps run via asyncio.gather when independent.',
    answer_es: 'Los workflows son pipelines DAG (Grafo Acíclico Dirigido) donde cada nodo es un paso de agente. El motor DAG usa el algoritmo de Kahn para ordenamiento topológico, identifica grupos paralelos, detecta ciclos y valida dependencias.'
  },

  checkpointing: {
    question_patterns: ['checkpoint', 'resume', 'crash recovery', 'recuperacion', 'save progress'],
    answer_en: 'After each step completes, state is saved to Redis. If the process crashes, the executor resumes from the last checkpoint. Failed steps go to a dead letter queue for manual review or automatic retry.',
    answer_es: 'Después de cada paso, el estado se guarda en Redis. Si el proceso falla, el ejecutor resume desde el último checkpoint. Pasos fallidos van a dead letter queue para revisión o retry automático.'
  },

  // SWARMS
  swarms_overview: {
    question_patterns: ['swarm', 'swarms', 'topolog', 'enjambre', 'how agents collaborate', 'como colaboran'],
    answer_en: '6 swarm topologies define how agents collaborate:\n• Sequential: A→B→C chain\n• Parallel: all agents run simultaneously (fan-out/fan-in)\n• Hierarchical: Planner decomposes → workers execute → Planner synthesizes\n• Debate: Agent produces → Critic scores → iterate until quality threshold (70+)\n• Consensus: N agents vote independently → Judge picks best\n• Adaptive: Router selects optimal topology dynamically based on input',
    answer_es: '6 topologías definen cómo colaboran los agentes:\n• Secuencial: cadena A→B→C\n• Paralelo: todos ejecutan simultáneamente\n• Jerárquico: Planner descompone → workers ejecutan → Planner sintetiza\n• Debate: Agente produce → Critic evalúa → itera hasta calidad 70+\n• Consenso: N agentes votan → Judge elige el mejor\n• Adaptativo: Router selecciona topología óptima dinámicamente'
  },

  debate_topology: {
    question_patterns: ['debate', 'debate topology', 'topologia debate', 'critic loop', 'quality iteration'],
    answer_en: 'The Debate topology creates a quality improvement loop: Agent produces output → Critic scores it 0-100 → if score < 70, feedback goes back to the Agent → Agent improves → Critic re-scores. Max 3 rounds. Typically improves quality from ~45 to ~85+ in 2-3 iterations.',
    answer_es: 'La topología Debate crea un loop de mejora: Agente produce → Critic puntúa 0-100 → si score < 70, feedback regresa al Agente → Agente mejora → Critic re-evalúa. Máximo 3 rondas. Típicamente mejora de ~45 a ~85+ en 2-3 iteraciones.'
  },

  which_topology: {
    question_patterns: ['which topology', 'cual topologia', 'best topology', 'mejor topologia', 'when to use', 'cuando usar'],
    answer_en: 'Choose based on your task:\n• Simple pipeline → Sequential\n• Independent tasks → Parallel (fastest)\n• Complex task needing planning → Hierarchical\n• Quality-critical output → Debate (iterates until good)\n• Multiple perspectives needed → Consensus (voting)\n• Unsure → Adaptive (auto-selects the best)',
    answer_es: 'Elige según tu tarea:\n• Pipeline simple → Secuencial\n• Tareas independientes → Paralelo (más rápido)\n• Tarea compleja → Jerárquico (con planificación)\n• Output crítico en calidad → Debate (itera hasta calidad)\n• Múltiples perspectivas → Consenso (votación)\n• No estás seguro → Adaptativo (auto-selecciona)'
  },

  // MEMORY
  memory_system: {
    question_patterns: ['memory', 'memoria', 'remember', 'context', 'tier', 'how agents remember'],
    answer_en: '3-tier memory system:\n• Working Memory (in-process): current task context, last 20 messages. Resets per execution.\n• Episodic Memory (Redis, 30-day TTL): task summaries, success/failure patterns.\n• Semantic Memory (pgvector, permanent): embedded knowledge vectors, cross-agent sharing via similarity search.',
    answer_es: 'Sistema de memoria de 3 niveles:\n• Memoria de Trabajo (en proceso): contexto actual, últimos 20 mensajes. Se reinicia por ejecución.\n• Memoria Episódica (Redis, 30 días TTL): resúmenes de tareas, patrones de éxito/fallo.\n• Memoria Semántica (pgvector, permanente): vectores de conocimiento, compartidos entre agentes via búsqueda de similitud.'
  },

  // SELF-HEALING
  self_healing: {
    question_patterns: ['healing', 'self-healing', 'auto-reparacion', 'auto-reparación', 'reparacion', 'reparación', 'repair', 'recovery', 'error handling', 'manejo de errores', 'self heal', 'auto heal', 'estrategias de recuperacion', 'fallo', 'failure'],
    answer_en: 'Self-healing engine: FailureDetector classifies errors into 6 types (network, timeout, data_quality, schema_mismatch, llm_error, auth). Then selects from 5 strategies:\n• Retry: same step, different config/provider\n• Skip: default output, continue pipeline\n• Repair: RepairAgent diagnoses and fixes\n• Escalate: human review queue\n• Fallback: cached result from previous run',
    answer_es: 'Motor de auto-reparación: FailureDetector clasifica errores en 6 tipos (red, timeout, calidad_datos, schema, llm, auth). Selecciona de 5 estrategias:\n• Retry: mismo paso, diferente config/proveedor\n• Skip: output default, continuar pipeline\n• Repair: RepairAgent diagnostica y arregla\n• Escalate: cola de revisión humana\n• Fallback: resultado cacheado de ejecución anterior'
  },

  // RAG
  rag_pipeline: {
    question_patterns: ['rag', 'search', 'semantic search', 'busqueda', 'vector', 'embedding', 'document search'],
    answer_en: 'RAG pipeline: Upload document → chunk into 500-char segments (50-char overlap) → embed with Voyage AI voyage-3-lite (512 dimensions) → store in PostgreSQL with pgvector extension → search via cosine similarity using match_chunks RPC function → returns top-K results with similarity scores.',
    answer_es: 'Pipeline RAG: Subir documento → dividir en segmentos de 500 chars (50 solapamiento) → embeber con Voyage AI voyage-3-lite (512 dimensiones) → almacenar en PostgreSQL con pgvector → buscar por similitud coseno via match_chunks → devuelve top-K resultados con scores.'
  },

  // LLM ROUTER
  llm_router: {
    question_patterns: ['llm', 'router', 'groq', 'claude', 'provider', 'model', 'proveedor', 'circuit breaker'],
    answer_en: 'Multi-provider LLM router with circuit breaker. Tries Groq first (Llama 3.3 70B, $0.59/$0.79 per M tokens — 40x cheaper than Claude). If Groq fails, falls back to Claude Sonnet ($3/$15 per M tokens). Circuit breaker: 3 errors in 60 seconds → skip that provider for 30 seconds.',
    answer_es: 'Router LLM multi-proveedor con circuit breaker. Intenta Groq primero (Llama 3.3 70B, $0.59/$0.79 por M tokens — 40x más barato que Claude). Si Groq falla, usa Claude Sonnet ($3/$15 por M tokens). Circuit breaker: 3 errores en 60s → salta ese proveedor por 30s.'
  },

  // INFRASTRUCTURE
  infrastructure: {
    question_patterns: ['infrastructure', 'infraestructura', 'docker', 'kubernetes', 'k8s', 'terraform', 'deploy', 'desplegar'],
    answer_en: 'Docker Compose for local dev (FastAPI + PostgreSQL + Redis). Terraform with 5 AWS modules (VPC, EKS, RDS+pgvector, S3, ElastiCache). Kubernetes with 15 manifests, HPAs, and Kustomize overlays for staging/production. Observability: Prometheus (14 alerts) + 5 Grafana dashboards + Loki + AlertManager.',
    answer_es: 'Docker Compose para dev local (FastAPI + PostgreSQL + Redis). Terraform con 5 módulos AWS (VPC, EKS, RDS+pgvector, S3, ElastiCache). Kubernetes con 15 manifests, HPAs y Kustomize overlays staging/producción. Observabilidad: Prometheus (14 alertas) + 5 dashboards Grafana + Loki + AlertManager.'
  },

  // DEVELOPER TOOLS
  sdk_cli: {
    question_patterns: ['sdk', 'cli', 'nxf', 'command line', 'linea de comandos', 'developer tools', 'herramientas'],
    answer_en: 'TypeScript SDK (@nexusforge/sdk): NexusForgeClient with fluent WorkflowBuilder and AgentBuilder. CLI tool (nxf): 13 commands — health, agents list/info, workflows list/create/run, runs list/detail, swarms list/execute, docs upload/search, plugins list.',
    answer_es: 'SDK TypeScript (@nexusforge/sdk): NexusForgeClient con WorkflowBuilder y AgentBuilder fluent. CLI (nxf): 13 comandos — health, agents list/info, workflows list/create/run, runs list/detail, swarms list/execute, docs upload/search, plugins list.'
  },

  plugins: {
    question_patterns: ['plugin', 'extension', 'marketplace', 'custom agent', 'agente personalizado'],
    answer_en: 'Plugin system with NexusPlugin interface and dynamic loader. Plugins register custom agents and data connectors. 2 example plugins: gov-data-mx (Mexico government data: DatosAbierto + Compranet) and gov-data-us (US data: DataGov + SecEdgar).',
    answer_es: 'Sistema de plugins con interfaz NexusPlugin y cargador dinámico. Los plugins registran agentes y conectores personalizados. 2 plugins ejemplo: gov-data-mx (datos gobierno México) y gov-data-us (datos gobierno US).'
  },

  testing: {
    question_patterns: ['test', 'testing', 'pytest', 'tests', 'pruebas', 'how many tests', 'cuantos tests'],
    answer_en: '231 pytest tests covering: DAG validation (15), state machine (17), retry policies (9), all 22 agents (86), swarm topologies (19), memory system (17), self-healing (25), plugins (9), models (10), RAG chunking (5). All run without Docker or API keys.',
    answer_es: '231 tests pytest cubriendo: validación DAG (15), state machine (17), políticas retry (9), 22 agentes (86), topologías swarm (19), memoria (17), self-healing (25), plugins (9), modelos (10), chunking RAG (5). Todos corren sin Docker ni API keys.'
  },

  // ARCHITECTURE
  tech_stack: {
    question_patterns: ['tech stack', 'stack', 'technology', 'tecnologia', 'what is it built with', 'con que esta construido'],
    answer_en: 'Backend: Python 3.12 + FastAPI + asyncio. Frontend: React 18 + Vite 5. Database: PostgreSQL + pgvector. Cache/Queue: Redis (Streams + pub/sub). LLM: Groq + Claude (circuit breaker). Embeddings: Voyage AI (512d). Infra: Docker, Terraform (AWS), Kubernetes. Observability: Prometheus + Grafana + Loki. Tests: 231 pytest.',
    answer_es: 'Backend: Python 3.12 + FastAPI + asyncio. Frontend: React 18 + Vite 5. Base de datos: PostgreSQL + pgvector. Cache/Cola: Redis. LLM: Groq + Claude (circuit breaker). Embeddings: Voyage AI (512d). Infra: Docker, Terraform (AWS), Kubernetes. Observabilidad: Prometheus + Grafana + Loki. Tests: 231 pytest.'
  },

  project_stats: {
    question_patterns: ['stats', 'numbers', 'estadisticas', 'numeros', 'how big', 'project size'],
    answer_en: '243 files, 231 tests, 22 agents, 6 swarm topologies, 3-tier memory, 5 healing strategies, 10 DB migrations, 18 REST endpoints + WebSocket, 5 Grafana dashboards, 14 Prometheus alert rules, 5 ADRs, 2 plugins, 13 CLI commands, TypeScript SDK.',
    answer_es: '243 archivos, 231 tests, 22 agentes, 6 topologías, memoria 3 niveles, 5 estrategias healing, 10 migraciones DB, 18 endpoints REST + WebSocket, 5 dashboards Grafana, 14 alertas Prometheus, 5 ADRs, 2 plugins, 13 comandos CLI, SDK TypeScript.'
  },

  design_decisions: {
    question_patterns: ['why', 'design decision', 'adr', 'decision', 'por que', 'architecture decision'],
    answer_en: '5 Architecture Decision Records:\n• ADR-001: Modular monolith over microservices (simpler dev, extract later)\n• ADR-002: Redis pub/sub over Kafka (no new dependency)\n• ADR-003: pgvector over Qdrant (one fewer service, ACID)\n• ADR-004: Shared schema + tenant_id for multi-tenancy\n• ADR-005: 3-tier memory (working/episodic/semantic)',
    answer_es: '5 Architecture Decision Records:\n• ADR-001: Monolito modular sobre microservicios\n• ADR-002: Redis pub/sub sobre Kafka\n• ADR-003: pgvector sobre Qdrant (un servicio menos)\n• ADR-004: Schema compartido + tenant_id para multi-tenancy\n• ADR-005: Memoria 3 niveles'
  },

  about_creator: {
    question_patterns: ['who built', 'creator', 'author', 'quien creo', 'christian', 'developer'],
    answer_en: 'Built by Christian Hernandez Escamilla, AI Engineer with 3+ years experience training Claude and GPT-4o at Scale AI. Uses Claude Code as primary development tool. Portfolio: https://ch65-portfolio.vercel.app | GitHub: https://github.com/christianescamilla15-cell',
    answer_es: 'Creado por Christian Hernandez Escamilla, Ingeniero IA con 3+ años entrenando Claude y GPT-4o en Scale AI. Usa Claude Code como herramienta principal. Portfolio: https://ch65-portfolio.vercel.app | GitHub: https://github.com/christianescamilla15-cell'
  },

  // COMPARISONS
  vs_langchain: {
    question_patterns: ['langchain', 'vs langchain', 'compared to langchain', 'diferencia con langchain'],
    answer_en: 'LangChain is a developer framework (library). NexusForge is a complete platform with UI, monitoring, self-healing, and deployment infrastructure. NexusForge includes what LangChain does (agent chaining, RAG) PLUS visual workflow builder, real-time monitoring, 6 swarm topologies, and production infrastructure.',
    answer_es: 'LangChain es un framework (librería). NexusForge es una plataforma completa con UI, monitoreo, auto-reparación e infraestructura. NexusForge incluye lo que hace LangChain (encadenamiento, RAG) MÁS workflow visual, monitoreo en tiempo real, 6 topologías y infraestructura de producción.'
  },

  vs_crewai: {
    question_patterns: ['crewai', 'vs crewai', 'compared to crewai', 'diferencia con crewai'],
    answer_en: 'CrewAI focuses on multi-agent conversations. NexusForge goes further: 22 agents (vs CrewAI\'s custom agents), 6 formal topologies, 3-tier persistent memory, self-healing, DAG engine with checkpointing, visual builder, Terraform/K8s deployment, and observability stack.',
    answer_es: 'CrewAI se enfoca en conversaciones multi-agente. NexusForge va más allá: 22 agentes, 6 topologías formales, memoria persistente 3 niveles, auto-reparación, motor DAG con checkpointing, builder visual, Terraform/K8s y stack de observabilidad.'
  },

  vs_n8n: {
    question_patterns: ['n8n', 'make.com', 'zapier', 'automation', 'automatizacion', 'vs n8n'],
    answer_en: 'n8n/Zapier connect APIs with if-then logic. NexusForge orchestrates AI agents with reasoning capabilities — agents can plan, debate, critique, and self-heal. The swarm topologies (especially Debate and Adaptive) go far beyond simple automation.',
    answer_es: 'n8n/Zapier conectan APIs con lógica if-then. NexusForge orquesta agentes IA con capacidad de razonamiento — los agentes planifican, debaten, critican y se auto-reparan. Las topologías van mucho más allá de la automatización simple.'
  },
}

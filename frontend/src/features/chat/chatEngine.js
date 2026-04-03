import { NEXUSFORGE_KB } from './ChatKnowledgeBase'

function normalize(text) {
  return text.toLowerCase().trim()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove accents
    .replace(/[¿¡?!.,;:'"()]/g, '') // remove punctuation
}

export function generateResponse(message, lang = 'en') {
  const lower = normalize(message)

  // 1. Greetings
  if (/^(hola|hello|hi|hey|buenos|buenas|good morning|good afternoon|que tal|saludos|greetings)/.test(lower)) {
    const greeting = lang === 'es'
      ? '**¡Hola! Soy el asistente de NexusForge AI.** Puedo explicarte sobre:\n\n**Inicio:** Qué es NexusForge, cómo funciona, casos de uso\n**Agentes:** 24 agentes IA especializados\n**Topologías:** 6 patrones de colaboración multi-agente\n**Memoria:** Sistema de 3 niveles (trabajo, episódica, semántica)\n**Auto-Reparación:** 5 estrategias de recuperación automática\n**Casos Reales:** Operaciones Empresariales, Inteligencia Documental, Copiloto de Portafolio\n**Plataforma:** Playground, Timeline, Evaluación, Dashboard de Costos, Modo Demo/Real\n**Técnico:** RAG Pipeline, LLM Router, infraestructura, SDK, CLI\n\n¡Pregúntame lo que quieras!'
      : '**Hi! I\'m the NexusForge AI assistant.** I can explain:\n\n**Getting Started:** What is NexusForge, how it works, use cases\n**Agents:** 24 specialized AI agents\n**Topologies:** 6 multi-agent collaboration patterns\n**Memory:** 3-tier system (working, episodic, semantic)\n**Self-Healing:** 5 automatic recovery strategies\n**Real Use Cases:** Enterprise Operations, Document Intelligence, Portfolio Copilot\n**Platform:** Playground, Timeline, Evaluation, Cost Dashboard, Demo/Real Mode\n**Technical:** RAG Pipeline, LLM Router, infrastructure, SDK, CLI\n\nAsk me anything!'
    return {
      text: greeting,
      topic: 'greeting',
      confidence: 1,
      suggestedFollowups: lang === 'es'
        ? ['¿Qué es NexusForge?', '¿Cómo funciona?', 'Explica los agentes', 'Topologías']
        : ['What is NexusForge?', 'How does it work?', 'Explain the agents', 'Topologies']
    }
  }

  // 2. Help / menu command
  if (/^(help|ayuda|menu|commands|opciones|que puedo preguntar|todos los temas|all topics)/.test(lower)) {
    const topic = NEXUSFORGE_KB.help
    return {
      text: lang === 'es' ? topic.answer_es : topic.answer_en,
      topic: 'help',
      confidence: 1,
      suggestedFollowups: lang === 'es'
        ? ['¿Qué es NexusForge?', 'Agentes', 'Topologías', 'Arquitectura']
        : ['What is NexusForge?', 'Agents', 'Topologies', 'Architecture']
    }
  }

  // 3. Score all KB topics by pattern match quality
  const scores = Object.entries(NEXUSFORGE_KB).map(([key, topic]) => {
    let score = 0
    for (const pattern of topic.question_patterns) {
      const normalizedPattern = normalize(pattern)
      if (lower.includes(normalizedPattern)) {
        // Longer pattern matches get higher score (more specific = better)
        score += normalizedPattern.split(' ').length
      }
    }
    // Bonus: exact start match
    for (const pattern of topic.question_patterns) {
      if (lower.startsWith(normalize(pattern))) {
        score += 2
      }
    }
    return { key, topic, score }
  }).filter(s => s.score > 0).sort((a, b) => b.score - a.score)

  if (scores.length > 0) {
    const best = scores[0]
    return {
      text: lang === 'es' ? (best.topic.answer_es || best.topic.answer_en) : best.topic.answer_en,
      topic: best.key,
      confidence: Math.min(0.95, best.score * 0.2),
      suggestedFollowups: getContextualFollowups(best.key, lang)
    }
  }

  // 4. Intelligent fallback with categorized suggestions
  const fallback = lang === 'es'
    ? 'No encontre un tema exacto para esa pregunta. Prueba con alguno de estos:\n\n**Populares:** "Que es NexusForge?" | "Agentes" | "Topologias"\n**Tecnico:** "RAG Pipeline" | "LLM Router" | "Self-Healing"\n**Detalle:** "Classifier" | "Debate topology" | "Memoria semántica"\n**General:** "Ayuda" para ver todos los temas disponibles\n\nIntenta ser más específico o usa palabras clave!'
    : 'I couldn\'t find an exact topic for that question. Try one of these:\n\n**Popular:** "What is NexusForge?" | "Agents" | "Topologies"\n**Technical:** "RAG Pipeline" | "LLM Router" | "Self-Healing"\n**Detailed:** "Classifier" | "Debate topology" | "Semantic memory"\n**General:** "Help" to see all available topics\n\nTry being more specific or use keywords!'
  return {
    text: fallback,
    topic: 'fallback',
    confidence: 0.2,
    suggestedFollowups: lang === 'es'
      ? ['¿Qué es NexusForge?', 'Ayuda completa', 'Agentes', 'Topologías']
      : ['What is NexusForge?', 'Full help', 'Agents', 'Topologies']
  }
}

// Contextual follow-up suggestions based on current topic
function getContextualFollowups(topicKey, lang) {
  const followupMap = {
    // Getting started
    what_is_nexusforge: ['how_it_works', 'agents_overview', 'swarms_intro'],
    how_it_works: ['workflows_intro', 'rag_pipeline', 'llm_router'],
    use_cases: ['getting_started', 'agents_overview', 'workflows_intro'],
    getting_started: ['what_is_nexusforge', 'agents_overview', 'swarms_intro'],
    // Agents
    agents_overview: ['classifier_agent', 'planner_agent', 'swarms_intro'],
    classifier_agent: ['extractor_agent', 'summarizer_agent', 'workflows_intro'],
    extractor_agent: ['classifier_agent', 'normalizer_agent', 'summarizer_agent'],
    summarizer_agent: ['analyzer_agent', 'validator_agent', 'topology_debate'],
    analyzer_agent: ['sentiment_agent', 'summarizer_agent', 'agents_overview'],
    validator_agent: ['repair_agent', 'critic_agent', 'healing_overview'],
    repair_agent: ['healing_overview', 'healing_strategies', 'validator_agent'],
    planner_agent: ['topology_hierarchical', 'critic_agent', 'agents_overview'],
    critic_agent: ['topology_debate', 'validator_agent', 'planner_agent'],
    normalizer_agent: ['extractor_agent', 'enricher_agent', 'agents_overview'],
    enricher_agent: ['knowledge_agent', 'researcher_agent', 'agents_overview'],
    researcher_agent: ['summarizer_agent', 'knowledge_agent', 'rag_pipeline'],
    translator_agent: ['summarizer_agent', 'agents_overview', 'use_cases'],
    compliance_agent: ['validator_agent', 'security', 'agents_overview'],
    monitor_agent: ['infrastructure', 'healing_overview', 'agents_overview'],
    router_agent: ['topology_adaptive', 'llm_router', 'agents_overview'],
    knowledge_agent: ['semantic_memory', 'rag_pipeline', 'enricher_agent'],
    scraper_agent: ['ocr_agent', 'researcher_agent', 'rag_pipeline'],
    ocr_agent: ['normalizer_agent', 'extractor_agent', 'scraper_agent'],
    sentiment_agent: ['analyzer_agent', 'agents_overview', 'use_cases'],
    scheduler_agent: ['webhook_agent', 'workflows_intro', 'agents_overview'],
    webhook_agent: ['scheduler_agent', 'infrastructure', 'agents_overview'],
    // Workflows
    workflows_intro: ['dag_engine', 'create_workflow', 'swarms_intro'],
    dag_engine: ['checkpointing', 'workflow_execution', 'swarms_intro'],
    create_workflow: ['workflow_execution', 'agents_overview', 'swarms_intro'],
    workflow_execution: ['checkpointing', 'healing_overview', 'dag_engine'],
    checkpointing: ['healing_overview', 'workflow_execution', 'dag_engine'],
    // Swarms
    swarms_intro: ['topology_debate', 'topology_adaptive', 'topology_hierarchical'],
    topology_sequential: ['topology_parallel', 'swarms_intro', 'workflows_intro'],
    topology_parallel: ['topology_sequential', 'topology_hierarchical', 'swarms_intro'],
    topology_hierarchical: ['planner_agent', 'topology_debate', 'swarms_intro'],
    topology_debate: ['critic_agent', 'topology_consensus', 'swarms_intro'],
    topology_consensus: ['topology_debate', 'topology_adaptive', 'swarms_intro'],
    topology_adaptive: ['router_agent', 'swarms_intro', 'topology_debate'],
    // Memory
    memory_overview: ['working_memory', 'episodic_memory', 'semantic_memory'],
    working_memory: ['episodic_memory', 'semantic_memory', 'memory_overview'],
    episodic_memory: ['semantic_memory', 'working_memory', 'healing_overview'],
    semantic_memory: ['rag_pipeline', 'knowledge_agent', 'memory_overview'],
    // Healing
    healing_overview: ['error_detection', 'healing_strategies', 'healing_example'],
    error_detection: ['healing_strategies', 'repair_agent', 'healing_overview'],
    healing_strategies: ['healing_example', 'repair_agent', 'healing_overview'],
    healing_example: ['healing_strategies', 'repair_agent', 'healing_overview'],
    // Technical
    llm_router: ['cost_tracking', 'rag_pipeline', 'infrastructure'],
    rag_pipeline: ['semantic_memory', 'llm_router', 'knowledge_agent'],
    cost_tracking: ['llm_router', 'infrastructure', 'project_stats'],
    infrastructure: ['testing', 'security', 'tech_stack'],
    testing: ['project_stats', 'infrastructure', 'agents_overview'],
    sdk: ['cli', 'plugins', 'infrastructure'],
    cli: ['sdk', 'plugins', 'infrastructure'],
    plugins: ['sdk', 'cli', 'agents_overview'],
    architecture_decisions: ['tech_stack', 'infrastructure', 'comparison'],
    security: ['infrastructure', 'architecture_decisions', 'testing'],
    comparison: ['what_is_nexusforge', 'agents_overview', 'swarms_intro'],
    // About
    about_creator: ['tech_stack', 'project_stats', 'what_is_nexusforge'],
    tech_stack: ['infrastructure', 'project_stats', 'architecture_decisions'],
    project_stats: ['tech_stack', 'about_creator', 'testing'],
    help: ['what_is_nexusforge', 'agents_overview', 'swarms_intro'],
    // Real Use Cases
    enterprise_ops: ['document_intelligence', 'portfolio_copilot', 'execution_timeline'],
    document_intelligence: ['enterprise_ops', 'portfolio_copilot', 'workflow_playground'],
    portfolio_copilot: ['enterprise_ops', 'document_intelligence', 'evaluation_harness'],
    // Platform Features
    execution_timeline: ['workflow_playground', 'cost_dashboard', 'enterprise_ops'],
    workflow_playground: ['execution_timeline', 'evaluation_harness', 'demo_real_mode'],
    cost_dashboard: ['execution_timeline', 'evaluation_harness', 'llm_router'],
    evaluation_harness: ['workflow_playground', 'cost_dashboard', 'enterprise_ops'],
    demo_real_mode: ['workflow_playground', 'execution_timeline', 'getting_started'],
  }

  const topicLabels = {
    what_is_nexusforge: { en: 'What is NexusForge?', es: '¿Qué es NexusForge?' },
    how_it_works: { en: 'How does it work?', es: '¿Cómo funciona?' },
    use_cases: { en: 'Use cases', es: 'Casos de uso' },
    getting_started: { en: 'Getting started', es: 'Cómo empezar' },
    agents_overview: { en: 'All 24 agents', es: 'Los 24 agentes' },
    classifier_agent: { en: 'Classifier agent', es: 'Agente Clasificador' },
    extractor_agent: { en: 'Extractor agent', es: 'Agente Extractor' },
    summarizer_agent: { en: 'Summarizer agent', es: 'Agente Resumidor' },
    analyzer_agent: { en: 'Analyzer agent', es: 'Agente Analizador' },
    validator_agent: { en: 'Validator agent', es: 'Agente Validador' },
    repair_agent: { en: 'Repair agent', es: 'Agente Reparación' },
    planner_agent: { en: 'Planner agent', es: 'Agente Planificador' },
    critic_agent: { en: 'Critic agent', es: 'Agente Crítico' },
    normalizer_agent: { en: 'Normalizer agent', es: 'Agente Normalizador' },
    enricher_agent: { en: 'Enricher agent', es: 'Agente Enriquecedor' },
    researcher_agent: { en: 'Researcher agent', es: 'Agente Investigador' },
    translator_agent: { en: 'Translator agent', es: 'Agente Traductor' },
    compliance_agent: { en: 'Compliance agent', es: 'Agente Cumplimiento' },
    monitor_agent: { en: 'Monitor agent', es: 'Agente Monitor' },
    router_agent: { en: 'Router agent', es: 'Agente Router' },
    knowledge_agent: { en: 'Knowledge agent', es: 'Agente Conocimiento' },
    scraper_agent: { en: 'Scraper agent', es: 'Agente Scraper' },
    ocr_agent: { en: 'OCR agent', es: 'Agente OCR' },
    sentiment_agent: { en: 'Sentiment agent', es: 'Agente Sentimiento' },
    scheduler_agent: { en: 'Scheduler agent', es: 'Agente Programador' },
    webhook_agent: { en: 'Webhook agent', es: 'Agente Webhook' },
    workflows_intro: { en: 'Workflows', es: 'Flujos de trabajo' },
    dag_engine: { en: 'DAG engine', es: 'Motor DAG' },
    create_workflow: { en: 'Create workflow', es: 'Crear workflow' },
    workflow_execution: { en: 'Run workflow', es: 'Ejecutar workflow' },
    checkpointing: { en: 'Checkpointing', es: 'Checkpointing' },
    swarms_intro: { en: 'Swarm topologies', es: 'Topologías de enjambre' },
    topology_sequential: { en: 'Sequential topology', es: 'Topología Secuencial' },
    topology_parallel: { en: 'Parallel topology', es: 'Topología Paralela' },
    topology_hierarchical: { en: 'Hierarchical topology', es: 'Topología Jerárquica' },
    topology_debate: { en: 'Debate topology', es: 'Topología Debate' },
    topology_consensus: { en: 'Consensus topology', es: 'Topología Consenso' },
    topology_adaptive: { en: 'Adaptive topology', es: 'Topología Adaptiva' },
    memory_overview: { en: 'Memory system', es: 'Sistema de memoria' },
    working_memory: { en: 'Working memory', es: 'Memoria de trabajo' },
    episodic_memory: { en: 'Episodic memory', es: 'Memoria episódica' },
    semantic_memory: { en: 'Semantic memory', es: 'Memoria semántica' },
    healing_overview: { en: 'Self-healing', es: 'Auto-reparación' },
    error_detection: { en: 'Error types', es: 'Tipos de error' },
    healing_strategies: { en: '5 recovery strategies', es: '5 estrategias' },
    healing_example: { en: 'Healing example', es: 'Ejemplo de reparación' },
    llm_router: { en: 'LLM Router', es: 'Router LLM' },
    rag_pipeline: { en: 'RAG Pipeline', es: 'Pipeline RAG' },
    cost_tracking: { en: 'Cost tracking', es: 'Seguimiento de costos' },
    infrastructure: { en: 'Infrastructure', es: 'Infraestructura' },
    testing: { en: 'Testing (260 tests)', es: 'Testing (260 tests)' },
    sdk: { en: 'TypeScript SDK', es: 'SDK TypeScript' },
    cli: { en: 'CLI (13 commands)', es: 'CLI (13 comandos)' },
    plugins: { en: 'Plugin system', es: 'Sistema de plugins' },
    architecture_decisions: { en: 'Architecture decisions', es: 'Decisiones de arquitectura' },
    security: { en: 'Security', es: 'Seguridad' },
    comparison: { en: 'vs LangChain/CrewAI', es: 'vs LangChain/CrewAI' },
    about_creator: { en: 'About the creator', es: 'Sobre el creador' },
    tech_stack: { en: 'Tech stack', es: 'Stack tecnológico' },
    project_stats: { en: 'Project stats', es: 'Estadísticas del proyecto' },
    help: { en: 'Full help', es: 'Ayuda completa' },
    // Real Use Cases
    enterprise_ops: { en: 'Operations Assistant', es: 'Asistente de Operaciones' },
    document_intelligence: { en: 'Document Intelligence', es: 'Inteligencia Documental' },
    portfolio_copilot: { en: 'Portfolio Copilot', es: 'Copiloto de Portafolio' },
    // Platform Features
    execution_timeline: { en: 'Execution Timeline', es: 'Timeline de Ejecución' },
    workflow_playground: { en: 'Workflow Playground', es: 'Playground de Workflows' },
    cost_dashboard: { en: 'Cost Dashboard', es: 'Dashboard de Costos' },
    evaluation_harness: { en: 'Evaluation Harness', es: 'Harness de Evaluación' },
    demo_real_mode: { en: 'Demo/Real Mode', es: 'Modo Demo/Real' },
  }

  const keys = followupMap[topicKey] || ['what_is_nexusforge', 'agents_overview', 'swarms_intro']
  return keys.map(k => {
    const label = topicLabels[k]
    return label ? (lang === 'es' ? label.es : label.en) : k
  })
}

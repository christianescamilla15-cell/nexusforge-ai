import { NEXUSFORGE_KB } from './ChatKnowledgeBase'

function normalize(text) {
  return text.toLowerCase().trim()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove accents
    .replace(/[¿¡?!.,;:]/g, '') // remove punctuation
}

export function generateResponse(message, lang = 'en') {
  const lower = normalize(message)

  // Greetings
  if (/^(hola|hello|hi|hey|buenos|buenas|good morning|que tal)/.test(lower)) {
    const greeting = lang === 'es'
      ? '¡Hola! Soy el asistente de NexusForge. Puedo explicarte sobre:\n\n• **Agentes** (22 tipos especializados)\n• **Topologías** (6 patrones de colaboración)\n• **Memoria** (3 niveles)\n• **Auto-Reparación** (5 estrategias)\n• **RAG Pipeline** (búsqueda semántica)\n• **Arquitectura** (stack técnico)\n\n¿Qué te interesa saber?'
      : 'Hi! I\'m the NexusForge assistant. I can explain:\n\n• **Agents** (22 specialized types)\n• **Topologies** (6 collaboration patterns)\n• **Memory** (3 tiers)\n• **Self-Healing** (5 strategies)\n• **RAG Pipeline** (semantic search)\n• **Architecture** (tech stack)\n\nWhat would you like to know?'
    return { text: greeting, topic: 'greeting', confidence: 1, suggestedFollowups: lang === 'es' ? ['¿Qué es NexusForge?', '¿Cómo funciona?', 'Explica los agentes'] : ['What is NexusForge?', 'How does it work?', 'Explain the agents'] }
  }

  // Help command
  if (/^(help|ayuda|menu|commands|opciones|que puedo preguntar)/.test(lower)) {
    const help = lang === 'es'
      ? '**Temas disponibles:**\n\n🚀 **Inicio:** qué es, cómo funciona, casos de uso, cómo empezar\n🤖 **Agentes:** overview, classifier, extractor, summarizer, validator, repair, planner, critic\n🔄 **Flujos:** workflows, DAG engine, checkpointing\n🐝 **Enjambres:** 6 topologías, cuál usar\n🧠 **Memoria:** 3 niveles, cómo funciona\n🛡️ **Auto-Reparación:** detección, estrategias\n🔍 **RAG:** pipeline, búsqueda semántica\n⚡ **LLM Router:** Groq, Claude, circuit breaker\n🏗️ **Infraestructura:** Docker, Terraform, K8s\n🔧 **Herramientas:** SDK, CLI, plugins\n📊 **Stats:** números del proyecto\n🏆 **Comparaciones:** vs LangChain, CrewAI, n8n'
      : '**Available topics:**\n\n🚀 **Getting Started:** what is it, how it works, use cases\n🤖 **Agents:** overview, classifier, extractor, summarizer, validator, repair, planner, critic\n🔄 **Workflows:** DAG engine, checkpointing\n🐝 **Swarms:** 6 topologies, which to use\n🧠 **Memory:** 3 tiers\n🛡️ **Self-Healing:** detection, strategies\n🔍 **RAG:** pipeline, semantic search\n⚡ **LLM Router:** Groq, Claude, circuit breaker\n🏗️ **Infrastructure:** Docker, Terraform, K8s\n🔧 **Tools:** SDK, CLI, plugins\n📊 **Stats:** project numbers\n🏆 **Comparisons:** vs LangChain, CrewAI, n8n'
    return { text: help, topic: 'help', confidence: 1, suggestedFollowups: lang === 'es' ? ['¿Qué es NexusForge?', 'Agentes', 'Topologías', 'Arquitectura'] : ['What is NexusForge?', 'Agents', 'Topologies', 'Architecture'] }
  }

  // Score all topics by pattern match count (longer matches = higher score)
  const scores = Object.entries(NEXUSFORGE_KB).map(([key, topic]) => {
    let score = 0
    for (const pattern of topic.question_patterns) {
      if (lower.includes(normalize(pattern))) {
        score += pattern.split(' ').length
      }
    }
    return { key, topic, score }
  }).filter(s => s.score > 0).sort((a, b) => b.score - a.score)

  if (scores.length > 0) {
    const best = scores[0]
    const followups = getFollowups(best.key, lang)
    return {
      text: lang === 'es' ? (best.topic.answer_es || best.topic.answer_en) : best.topic.answer_en,
      topic: best.key,
      confidence: Math.min(0.95, best.score * 0.25),
      suggestedFollowups: followups
    }
  }

  // Intelligent fallback
  const fallback = lang === 'es'
    ? 'No encontré un tema exacto, pero puedo ayudarte con:\n\n• "¿Qué es NexusForge?" — visión general\n• "Agentes" — los 22 agentes\n• "Topologías" — 6 patrones de enjambre\n• "Memoria" — sistema de 3 niveles\n• "Auto-reparación" — 5 estrategias\n• "Ayuda" — ver todos los temas\n\n¡Intenta ser más específico!'
    : 'I couldn\'t find an exact match, but I can help with:\n\n• "What is NexusForge?" — overview\n• "Agents" — all 22 agents\n• "Topologies" — 6 swarm patterns\n• "Memory" — 3-tier system\n• "Self-healing" — 5 strategies\n• "Help" — see all topics\n\nTry being more specific!'
  return { text: fallback, topic: 'fallback', confidence: 0.3, suggestedFollowups: lang === 'es' ? ['¿Qué es NexusForge?', 'Ayuda', 'Agentes'] : ['What is NexusForge?', 'Help', 'Agents'] }
}

function getFollowups(topic, lang) {
  const map = {
    what_is_nexusforge: ['how_it_works', 'agents_overview', 'swarms_overview'],
    how_it_works: ['workflows', 'rag_pipeline', 'llm_router'],
    agents_overview: ['classifier', 'planner', 'repair'],
    classifier: ['extractor', 'summarizer', 'validator'],
    extractor: ['classifier', 'summarizer', 'agents_overview'],
    summarizer: ['extractor', 'validator', 'agents_overview'],
    validator: ['repair', 'critic', 'self_healing'],
    repair: ['self_healing', 'validator', 'planner'],
    planner: ['swarms_overview', 'critic', 'agents_overview'],
    critic: ['debate_topology', 'validator', 'planner'],
    workflows: ['checkpointing', 'swarms_overview', 'agents_overview'],
    swarms_overview: ['debate_topology', 'which_topology', 'workflows'],
    debate_topology: ['critic', 'which_topology', 'swarms_overview'],
    which_topology: ['swarms_overview', 'debate_topology', 'workflows'],
    memory_system: ['agents_overview', 'rag_pipeline', 'self_healing'],
    self_healing: ['repair', 'memory_system', 'infrastructure'],
    rag_pipeline: ['llm_router', 'memory_system', 'tech_stack'],
    llm_router: ['rag_pipeline', 'infrastructure', 'tech_stack'],
    infrastructure: ['tech_stack', 'project_stats', 'sdk_cli'],
    tech_stack: ['infrastructure', 'project_stats', 'design_decisions'],
    project_stats: ['tech_stack', 'about_creator', 'testing'],
    testing: ['project_stats', 'infrastructure', 'agents_overview'],
    sdk_cli: ['plugins', 'infrastructure', 'tech_stack'],
    plugins: ['sdk_cli', 'agents_overview', 'infrastructure'],
    design_decisions: ['tech_stack', 'infrastructure', 'about_creator'],
  }
  const keys = map[topic] || ['what_is_nexusforge', 'agents_overview', 'swarms_overview']

  const labels = {
    what_is_nexusforge: lang === 'es' ? '¿Qué es NexusForge?' : 'What is NexusForge?',
    how_it_works: lang === 'es' ? '¿Cómo funciona?' : 'How does it work?',
    agents_overview: lang === 'es' ? 'Ver agentes' : 'View agents',
    classifier: 'Classifier agent',
    extractor: 'Extractor agent',
    summarizer: 'Summarizer agent',
    validator: 'Validator agent',
    repair: 'Repair agent',
    planner: 'Planner agent',
    critic: 'Critic agent',
    workflows: lang === 'es' ? 'Flujos de trabajo' : 'Workflows',
    checkpointing: 'Checkpointing',
    swarms_overview: lang === 'es' ? 'Topologías' : 'Topologies',
    debate_topology: lang === 'es' ? 'Topología Debate' : 'Debate topology',
    which_topology: lang === 'es' ? '¿Cuál topología usar?' : 'Which topology?',
    memory_system: lang === 'es' ? 'Sistema de memoria' : 'Memory system',
    self_healing: 'Self-Healing',
    rag_pipeline: 'RAG Pipeline',
    llm_router: 'LLM Router',
    infrastructure: lang === 'es' ? 'Infraestructura' : 'Infrastructure',
    tech_stack: 'Tech Stack',
    project_stats: lang === 'es' ? 'Estadísticas' : 'Project stats',
    testing: 'Testing (231)',
    sdk_cli: 'SDK & CLI',
    plugins: 'Plugins',
    design_decisions: 'ADRs',
    about_creator: lang === 'es' ? 'Sobre el creador' : 'About creator',
  }

  return keys.map(k => labels[k] || k)
}

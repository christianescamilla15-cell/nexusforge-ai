import { NEXUSFORGE_KB } from './ChatKnowledgeBase'

export function generateResponse(message, lang = 'en') {
  const lower = message.toLowerCase().trim()

  // 1. Pattern matching against KB
  for (const [topic, data] of Object.entries(NEXUSFORGE_KB)) {
    for (const pattern of data.question_patterns) {
      if (lower.includes(pattern)) {
        return {
          text: lang === 'es' ? (data.answer_es || data.answer_en) : data.answer_en,
          topic,
          confidence: 0.9,
          sources: [`NexusForge ${topic} documentation`],
          suggestedFollowups: getFollowups(topic, lang)
        }
      }
    }
  }

  // 2. Greeting detection
  const greetings = ['hello', 'hi', 'hey', 'hola', 'buenos dias', 'buenas']
  if (greetings.some(g => lower.includes(g))) {
    return {
      text: lang === 'es'
        ? '¡Hola! Soy el asistente de NexusForge AI. ¿En qué puedo ayudarte hoy?\n\nPuedes preguntarme sobre agentes, swarms, memoria, arquitectura y más.'
        : 'Hello! I\'m the NexusForge AI assistant. How can I help you today?\n\nYou can ask me about agents, swarms, memory, architecture, and more.',
      topic: 'greeting',
      confidence: 0.85,
      sources: [],
      suggestedFollowups: lang === 'es'
        ? ['¿Qué es NexusForge?', 'Muéstrame los agentes', 'Explica los enjambres']
        : ['What is NexusForge?', 'Show me agents', 'Explain swarms']
    }
  }

  // 3. Intelligent fallback
  return {
    text: lang === 'en'
      ? 'I can help you with NexusForge! Try asking about:\n\n• **Agents** (22 types)\n• **Swarm topologies** (6 patterns)\n• **Memory system** (3 tiers)\n• **Self-healing** (5 strategies)\n• **Architecture** & tech stack\n• **RAG pipeline**\n• **Deployment** (Docker, K8s, AWS)\n• **CLI** & **SDK**\n• **Security** & **Testing**'
      : '¡Puedo ayudarte con NexusForge! Intenta preguntar sobre:\n\n• **Agentes** (22 tipos)\n• **Topologías de enjambre** (6 patrones)\n• **Sistema de memoria** (3 niveles)\n• **Auto-reparación** (5 estrategias)\n• **Arquitectura** y stack tecnológico\n• **Pipeline RAG**\n• **Despliegue** (Docker, K8s, AWS)\n• **CLI** y **SDK**\n• **Seguridad** y **Testing**',
    topic: 'general',
    confidence: 0.5,
    sources: [],
    suggestedFollowups: lang === 'es'
      ? ['¿Qué es NexusForge?', '¿Cuántos agentes hay?', 'Explica las topologías']
      : ['What is NexusForge?', 'How many agents?', 'Explain swarm topologies']
  }
}

function getFollowups(topic, lang) {
  const followupsEn = {
    overview: ['How many agents?', 'Explain swarm topologies', 'What is the tech stack?'],
    agents: ['Explain swarm topologies', 'How does memory work?', 'What is self-healing?'],
    swarms: ['Which topology is best?', 'How does debate work?', 'Show me agents'],
    memory: ['How do agents learn?', 'What is RAG?', 'Explain self-healing'],
    healing: ['How does the DAG engine work?', 'Explain memory system', 'Show deployment options'],
    architecture: ['How is it deployed?', 'What about security?', 'Tell me about testing'],
    dag: ['What are swarm topologies?', 'How does self-healing work?', 'Explain RAG pipeline'],
    rag: ['How does memory work?', 'Show me agents', 'What is the architecture?'],
    plugins: ['How do I deploy?', 'What is the SDK?', 'Show CLI commands'],
    cost: ['Compare with LangChain', 'What about security?', 'How is it deployed?'],
    cli: ['What about the SDK?', 'How do I deploy?', 'Show me agents'],
    sdk: ['What about the CLI?', 'Explain the architecture', 'How does RAG work?'],
    testing: ['How is it deployed?', 'What about security?', 'Explain the architecture'],
    deployment: ['What about security?', 'Show me the CLI', 'How does monitoring work?'],
    security: ['How is it deployed?', 'Tell me about testing', 'Explain the architecture'],
    comparison: ['What is NexusForge?', 'Show me agents', 'Explain swarm topologies'],
    help: ['What is NexusForge?', 'Show me agents', 'Explain the architecture'],
  }

  const followupsEs = {
    overview: ['¿Cuántos agentes hay?', 'Explica las topologías', '¿Cuál es el stack?'],
    agents: ['Explica los enjambres', '¿Cómo funciona la memoria?', '¿Qué es auto-reparación?'],
    swarms: ['¿Cuál topología es mejor?', '¿Cómo funciona debate?', 'Muéstrame los agentes'],
    memory: ['¿Cómo aprenden los agentes?', '¿Qué es RAG?', 'Explica auto-reparación'],
    healing: ['¿Cómo funciona el motor DAG?', 'Explica la memoria', 'Opciones de despliegue'],
    architecture: ['¿Cómo se despliega?', '¿Qué hay de seguridad?', 'Cuéntame del testing'],
    dag: ['¿Qué son las topologías?', '¿Cómo funciona auto-reparación?', 'Explica el RAG'],
    rag: ['¿Cómo funciona la memoria?', 'Muéstrame los agentes', '¿Cuál es la arquitectura?'],
    plugins: ['¿Cómo despliego?', '¿Qué es el SDK?', 'Muéstrame los comandos CLI'],
    cost: ['Compara con LangChain', '¿Qué hay de seguridad?', '¿Cómo se despliega?'],
    cli: ['¿Qué hay del SDK?', '¿Cómo despliego?', 'Muéstrame los agentes'],
    sdk: ['¿Qué hay del CLI?', 'Explica la arquitectura', '¿Cómo funciona el RAG?'],
    testing: ['¿Cómo se despliega?', '¿Qué hay de seguridad?', 'Explica la arquitectura'],
    deployment: ['¿Qué hay de seguridad?', 'Muéstrame el CLI', '¿Cómo funciona el monitoreo?'],
    security: ['¿Cómo se despliega?', 'Cuéntame del testing', 'Explica la arquitectura'],
    comparison: ['¿Qué es NexusForge?', 'Muéstrame los agentes', 'Explica las topologías'],
    help: ['¿Qué es NexusForge?', 'Muéstrame los agentes', 'Explica la arquitectura'],
  }

  const map = lang === 'es' ? followupsEs : followupsEn
  return map[topic] || (lang === 'es'
    ? ['¿Qué es NexusForge?', 'Explica la arquitectura', '¿Cómo funciona el RAG?']
    : ['Tell me about agents', 'Explain the architecture', 'How does RAG work?'])
}

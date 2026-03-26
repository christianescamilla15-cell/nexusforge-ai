export const translations = {
  en: {
    // Navigation
    dashboard: 'Dashboard',
    workflows: 'Workflows',
    executions: 'Executions',
    agents: 'Agents',
    swarms: 'Swarms',
    documents: 'Documents',
    settings: 'Settings',
    chat: 'AI Assistant',

    // Dashboard
    totalWorkflows: 'Total Workflows',
    activeRuns: 'Active Runs',
    agentsOnline: 'Agents Online',
    docsIndexed: 'Docs Indexed',
    recentExecutions: 'Recent Executions',
    agentActivity: 'Agent Activity',
    costOverview: 'Cost Overview',

    // Workflows
    newWorkflow: 'New Workflow',
    createWorkflow: 'Create Workflow',
    runWorkflow: 'Run Workflow',
    workflowName: 'Workflow Name',
    description: 'Description',
    dagDefinition: 'DAG Definition',
    status: 'Status',
    created: 'Created',
    version: 'Version',

    // Executions
    duration: 'Duration',
    cost: 'Cost',
    steps: 'Steps',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    pending: 'Pending',
    cancelled: 'Cancelled',

    // Agents
    agentType: 'Agent Type',
    agentDescription: 'Description',
    tools: 'Tools',
    memory: 'Memory',
    workingMemory: 'Working Memory',
    episodicMemory: 'Episodic Memory',
    semanticMemory: 'Semantic Memory',
    selfHealing: 'Self-Healing',

    // Swarms
    topology: 'Topology',
    sequential: 'Sequential',
    parallel: 'Parallel',
    hierarchical: 'Hierarchical',
    debate: 'Debate',
    consensus: 'Consensus',
    adaptive: 'Adaptive',
    executeSwarm: 'Execute Swarm',
    selectAgents: 'Select Agents',
    inputData: 'Input Data',

    // Documents
    uploadDocument: 'Upload Document',
    semanticSearch: 'Semantic Search',
    searchPlaceholder: 'Search documents...',
    title: 'Title',
    content: 'Content',
    similarity: 'Similarity',

    // Chat
    askAnything: 'Ask anything about NexusForge...',
    send: 'Send',
    thinking: 'Thinking...',
    chatWelcome: 'Hi! I\'m the NexusForge AI Assistant. Ask me anything about the platform — agents, workflows, swarms, or architecture.',

    // Onboarding
    welcome: 'Welcome to NexusForge AI',
    welcomeDesc: 'Enterprise Agent Orchestration Platform with 22 AI agents, 6 swarm topologies, and self-healing capabilities.',
    tourStep1: 'Dashboard — Monitor your platform health, costs, and recent activity',
    tourStep2: 'Workflows — Create and manage DAG-based execution pipelines',
    tourStep3: 'Executions — Watch workflows run in real-time with WebSocket monitoring',
    tourStep4: 'Agents — Browse 22 specialized AI agents with 3-tier memory',
    tourStep5: 'Swarms — Execute agent teams in 6 topologies (sequential, parallel, debate...)',
    tourStep6: 'Documents — Upload, index, and search with RAG + pgvector',
    tourStep7: 'AI Assistant — Ask questions about the entire system',
    next: 'Next',
    skip: 'Skip Tour',
    finish: 'Get Started',

    // Settings
    apiUrl: 'API URL',
    language: 'Language',
    theme: 'Theme',
    healthCheck: 'Health Check',
    resetTour: 'Reset Onboarding Tour',
    resetTourDesc: 'Show the onboarding tour again on next page load.',
    resetTourBtn: 'Reset Tour',
    tourReset: 'Tour will show on next reload.',

    // Common
    loading: 'Loading...',
    error: 'Error',
    retry: 'Retry',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    close: 'Close',
    back: 'Back',
    noData: 'No data available',
    search: 'Search',

    // Dashboard misc
    dashboardSubtitle: 'NexusForge AI system overview',
    demoMode: 'Demo mode — API unavailable',
    today: 'Today',
    thisWeek: 'This week',
    thisMonth: 'This month',

    // Workflows misc
    manageWorkflows: 'Manage your automated workflows',
    all: 'All',
    draft: 'Draft',
    active: 'Active',
    paused: 'Paused',
    archived: 'Archived',
    noWorkflows: 'No workflows',
    noWorkflowsDesc: 'Create your first workflow to start automating tasks with AI agents.',
    name: 'Name',

    // Executions misc
    monitorExecutions: 'Monitor all workflow executions in real-time.',
    total: 'total',
    noExecutionsFilter: 'No executions with this filter.',
    workflow: 'Workflow',
    start: 'Start',

    // Agents misc
    manageAgents: 'Manage and configure available AI agents.',
    registered: 'registered',
    loadingAgents: 'Loading agents...',

    // Swarms misc
    swarmSubtitle: 'Orchestrate multiple agents with different execution patterns.',
    topologies: 'topologies',

    // Documents misc
    manageDocuments: 'Manage the documents indexed in the system.',
    documentsCount: 'documents',
    upload: 'Upload',
    noDocuments: 'No documents. Upload one to get started.',
    type: 'Type',
    lang: 'Language',
    size: 'Size',

    // Settings misc
    settingsSubtitle: 'Configure NexusForge system preferences.',
    apiBaseUrl: 'API Base URL',
    apiBaseUrlDesc: 'NexusForge backend server URL.',
    themeDesc: 'Dark mode is enabled. Other themes coming soon.',
    languageDesc: 'Select the interface language.',
    apiStatus: 'API Status',
    apiStatusDesc: 'Verify the backend connection.',
    verifying: 'Verifying...',
    verifyConnection: 'Verify Connection',
    apiOperative: 'API operative',
    versionLabel: 'Version',
    versionDesc: 'NexusForge AI Platform',
    searchWorkflowsAgents: 'Search workflows, agents...',

    // Workflow detail
    edit: 'Edit',
    starting: 'Starting...',
    execute: 'Execute',
    updated: 'Updated',
    executionGraph: 'Execution Graph (DAG)',
    executionHistory: 'Execution History',
    errorExecuting: 'Error executing',

    // Execution detail
    backToExecutions: 'Back',
    loadingExecution: 'Loading execution...',
    progress: 'Progress',
    executionPipeline: 'Execution Pipeline',
    eventLog: 'Event Log',
    executionCompleted: 'Execution Completed',
    executionFailed: 'Execution Failed',
    totalTime: 'Total time',
    totalCost: 'Total cost',
    tokensUsed: 'Tokens used',
    tokens: 'Tokens',
  },
  es: {
    // Navigation
    dashboard: 'Panel Principal',
    workflows: 'Flujos de Trabajo',
    executions: 'Ejecuciones',
    agents: 'Agentes',
    swarms: 'Enjambres',
    documents: 'Documentos',
    settings: 'Configuracion',
    chat: 'Asistente IA',

    // Dashboard
    totalWorkflows: 'Total Flujos',
    activeRuns: 'Ejecuciones Activas',
    agentsOnline: 'Agentes Activos',
    docsIndexed: 'Docs Indexados',
    recentExecutions: 'Ejecuciones Recientes',
    agentActivity: 'Actividad de Agentes',
    costOverview: 'Resumen de Costos',

    // Workflows
    newWorkflow: 'Nuevo Flujo',
    createWorkflow: 'Crear Flujo',
    runWorkflow: 'Ejecutar Flujo',
    workflowName: 'Nombre del Flujo',
    description: 'Descripcion',
    dagDefinition: 'Definicion DAG',
    status: 'Estado',
    created: 'Creado',
    version: 'Version',

    // Executions
    duration: 'Duracion',
    cost: 'Costo',
    steps: 'Pasos',
    running: 'Ejecutando',
    completed: 'Completado',
    failed: 'Fallido',
    pending: 'Pendiente',
    cancelled: 'Cancelado',

    // Agents
    agentType: 'Tipo de Agente',
    agentDescription: 'Descripcion',
    tools: 'Herramientas',
    memory: 'Memoria',
    workingMemory: 'Memoria de Trabajo',
    episodicMemory: 'Memoria Episodica',
    semanticMemory: 'Memoria Semantica',
    selfHealing: 'Auto-Reparacion',

    // Swarms
    topology: 'Topologia',
    sequential: 'Secuencial',
    parallel: 'Paralelo',
    hierarchical: 'Jerarquico',
    debate: 'Debate',
    consensus: 'Consenso',
    adaptive: 'Adaptativo',
    executeSwarm: 'Ejecutar Enjambre',
    selectAgents: 'Seleccionar Agentes',
    inputData: 'Datos de Entrada',

    // Documents
    uploadDocument: 'Subir Documento',
    semanticSearch: 'Busqueda Semantica',
    searchPlaceholder: 'Buscar documentos...',
    title: 'Titulo',
    content: 'Contenido',
    similarity: 'Similitud',

    // Chat
    askAnything: 'Pregunta lo que sea sobre NexusForge...',
    send: 'Enviar',
    thinking: 'Pensando...',
    chatWelcome: 'Hola! Soy el Asistente IA de NexusForge. Preguntame sobre agentes, flujos, enjambres o arquitectura.',

    // Onboarding
    welcome: 'Bienvenido a NexusForge AI',
    welcomeDesc: 'Plataforma de Orquestacion de Agentes con 22 agentes IA, 6 topologias de enjambre y auto-reparacion.',
    tourStep1: 'Panel Principal — Monitorea la salud, costos y actividad reciente',
    tourStep2: 'Flujos de Trabajo — Crea y gestiona pipelines basados en DAG',
    tourStep3: 'Ejecuciones — Observa flujos en tiempo real con WebSocket',
    tourStep4: 'Agentes — Explora 22 agentes IA especializados con memoria de 3 niveles',
    tourStep5: 'Enjambres — Ejecuta equipos de agentes en 6 topologias (secuencial, paralelo, debate...)',
    tourStep6: 'Documentos — Sube, indexa y busca con RAG + pgvector',
    tourStep7: 'Asistente IA — Haz preguntas sobre todo el sistema',
    next: 'Siguiente',
    skip: 'Saltar Tour',
    finish: 'Comenzar',

    // Settings
    apiUrl: 'URL de API',
    language: 'Idioma',
    theme: 'Tema',
    healthCheck: 'Verificar Salud',
    resetTour: 'Reiniciar Tour de Bienvenida',
    resetTourDesc: 'Mostrar el tour de bienvenida de nuevo al recargar la pagina.',
    resetTourBtn: 'Reiniciar Tour',
    tourReset: 'El tour se mostrara al recargar.',

    // Common
    loading: 'Cargando...',
    error: 'Error',
    retry: 'Reintentar',
    cancel: 'Cancelar',
    save: 'Guardar',
    delete: 'Eliminar',
    close: 'Cerrar',
    back: 'Volver',
    noData: 'Sin datos disponibles',
    search: 'Buscar',

    // Dashboard misc
    dashboardSubtitle: 'Vista general del sistema NexusForge AI',
    demoMode: 'Modo demo — API no disponible',
    today: 'Hoy',
    thisWeek: 'Esta semana',
    thisMonth: 'Este mes',

    // Workflows misc
    manageWorkflows: 'Gestiona tus flujos de trabajo automatizados',
    all: 'Todos',
    draft: 'Borrador',
    active: 'Activo',
    paused: 'Pausado',
    archived: 'Archivado',
    noWorkflows: 'No hay workflows',
    noWorkflowsDesc: 'Crea tu primer workflow para comenzar a automatizar tareas con agentes IA.',
    name: 'Nombre',

    // Executions misc
    monitorExecutions: 'Monitorea todas las ejecuciones de workflows en tiempo real.',
    total: 'total',
    noExecutionsFilter: 'No hay ejecuciones con este filtro.',
    workflow: 'Workflow',
    start: 'Inicio',

    // Agents misc
    manageAgents: 'Gestiona y configura los agentes IA disponibles.',
    registered: 'registrados',
    loadingAgents: 'Cargando agentes...',

    // Swarms misc
    swarmSubtitle: 'Orquesta multiples agentes con diferentes patrones de ejecucion.',
    topologies: 'topologias',

    // Documents misc
    manageDocuments: 'Administra los documentos indexados en el sistema.',
    documentsCount: 'documentos',
    upload: 'Subir',
    noDocuments: 'No hay documentos. Sube uno para comenzar.',
    type: 'Tipo',
    lang: 'Idioma',
    size: 'Tamano',

    // Settings misc
    settingsSubtitle: 'Configura las preferencias del sistema NexusForge.',
    apiBaseUrl: 'API Base URL',
    apiBaseUrlDesc: 'URL del servidor backend de NexusForge.',
    themeDesc: 'Dark mode esta activado. Otros temas proximamente.',
    languageDesc: 'Selecciona el idioma de la interfaz.',
    apiStatus: 'Estado del API',
    apiStatusDesc: 'Verifica la conexion con el backend.',
    verifying: 'Verificando...',
    verifyConnection: 'Verificar Conexion',
    apiOperative: 'API operativo',
    versionLabel: 'Version',
    versionDesc: 'NexusForge AI Platform',
    searchWorkflowsAgents: 'Buscar workflows, agentes...',

    // Workflow detail
    edit: 'Editar',
    starting: 'Iniciando...',
    execute: 'Ejecutar',
    updated: 'Actualizado',
    executionGraph: 'Grafo de Ejecucion (DAG)',
    executionHistory: 'Historial de Ejecuciones',
    errorExecuting: 'Error al ejecutar',

    // Execution detail
    backToExecutions: 'Volver',
    loadingExecution: 'Cargando ejecucion...',
    progress: 'Progreso',
    executionPipeline: 'Pipeline de Ejecucion',
    eventLog: 'Log de Eventos',
    executionCompleted: 'Ejecucion Completada',
    executionFailed: 'Ejecucion Fallida',
    totalTime: 'Tiempo total',
    totalCost: 'Costo total',
    tokensUsed: 'Tokens usados',
    tokens: 'Tokens',
  }
}

export function t(key, lang = 'en') {
  return translations[lang]?.[key] || translations.en[key] || key
}

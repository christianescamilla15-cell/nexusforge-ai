import { Component } from 'react'

/**
 * Catches React render errors and shows a recovery UI instead of white screen.
 * Usage: <ErrorBoundary><App /></ErrorBoundary>
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      const lang = this.props.lang || 'en'
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#F9FAFB', padding: 24,
        }}>
          <div style={{
            background: '#fff', borderRadius: 16, padding: 32, maxWidth: 480,
            textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x26A0;&#xFE0F;</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
              {lang === 'es' ? 'Algo salio mal' : 'Something went wrong'}
            </h2>
            <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 20, lineHeight: 1.5 }}>
              {lang === 'es'
                ? 'La aplicacion encontro un error inesperado. Puedes intentar recargar la pagina.'
                : 'The application encountered an unexpected error. You can try reloading the page.'}
            </p>
            {this.state.error && (
              <pre style={{
                fontSize: 11, color: '#9CA3AF', background: '#F9FAFB', padding: 12,
                borderRadius: 8, marginBottom: 16, textAlign: 'left',
                overflow: 'auto', maxHeight: 100, border: '1px solid #E5E7EB',
              }}>
                {String(this.state.error)}
              </pre>
            )}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 24px', borderRadius: 8, border: 'none',
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {lang === 'es' ? 'Recargar pagina' : 'Reload page'}
              </button>
              <button
                onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/' }}
                style={{
                  padding: '10px 24px', borderRadius: 8, border: '1px solid #E5E7EB',
                  background: '#fff', color: '#374151', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {lang === 'es' ? 'Ir al inicio' : 'Go to Dashboard'}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

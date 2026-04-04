/**
 * Loading skeleton placeholders. Replaces spinners with content-shaped shimmers.
 * Usage: <Skeleton.Card />, <Skeleton.Line />, <Skeleton.Grid count={6} />
 */

const shimmer = `
@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
`

const base = {
  background: 'linear-gradient(90deg, #F3F4F6 25%, #E5E7EB 50%, #F3F4F6 75%)',
  backgroundSize: '800px 100%',
  animation: 'shimmer 1.5s infinite linear',
  borderRadius: 8,
}

function Line({ width = '100%', height = 14, style = {} }) {
  return <div style={{ ...base, width, height, marginBottom: 8, ...style }} />
}

function Card({ style = {} }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 16, border: '1px solid #F3F4F6',
      padding: 24, ...style,
    }}>
      <div style={{ display: 'flex', gap: 14, marginBottom: 16 }}>
        <div style={{ ...base, width: 52, height: 52, borderRadius: 14 }} />
        <div style={{ flex: 1 }}>
          <Line width="60%" height={16} />
          <Line width="80%" height={12} />
        </div>
      </div>
      <Line width="100%" height={12} />
      <Line width="70%" height={12} />
      <div style={{ borderTop: '1px solid #F3F4F6', marginTop: 16, paddingTop: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Line width="40%" height={12} />
        <div style={{ ...base, width: 80, height: 32, borderRadius: 8 }} />
      </div>
    </div>
  )
}

function Grid({ count = 6, style = {} }) {
  return (
    <>
      <style>{shimmer}</style>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 20,
        ...style,
      }}>
        {Array.from({ length: count }, (_, i) => <Card key={i} />)}
      </div>
    </>
  )
}

function Table({ rows = 5 }) {
  return (
    <>
      <style>{shimmer}</style>
      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} style={{
            padding: '14px 20px', borderBottom: i < rows - 1 ? '1px solid #F3F4F6' : 'none',
            display: 'flex', gap: 16, alignItems: 'center',
          }}>
            <div style={{ ...base, width: 24, height: 24, borderRadius: '50%' }} />
            <Line width="30%" height={14} style={{ marginBottom: 0, flex: 'none' }} />
            <Line width="20%" height={12} style={{ marginBottom: 0, flex: 'none' }} />
            <div style={{ flex: 1 }} />
            <Line width="60px" height={12} style={{ marginBottom: 0, flex: 'none' }} />
          </div>
        ))}
      </div>
    </>
  )
}

const Skeleton = { Line, Card, Grid, Table }
export default Skeleton

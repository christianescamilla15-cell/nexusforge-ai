import { useState } from 'react'

/**
 * Visual cron schedule picker. Returns a cron expression string.
 * Usage: <SchedulePicker value="0 9 * * 1" onChange={setCron} lang="en" />
 */

const PRESETS = [
  { cron: '*/5 * * * *', label: { en: 'Every 5 min', es: 'Cada 5 min' } },
  { cron: '*/15 * * * *', label: { en: 'Every 15 min', es: 'Cada 15 min' } },
  { cron: '0 * * * *', label: { en: 'Every hour', es: 'Cada hora' } },
  { cron: '0 8 * * *', label: { en: 'Daily at 8 AM', es: 'Diario a las 8 AM' } },
  { cron: '0 9 * * 1-5', label: { en: 'Weekdays at 9 AM', es: 'Lun-Vie a las 9 AM' } },
  { cron: '0 9 * * 1', label: { en: 'Every Monday 9 AM', es: 'Cada lunes 9 AM' } },
  { cron: '0 8 1 * *', label: { en: '1st of month 8 AM', es: '1ro de mes 8 AM' } },
]

const DAYS = [
  { value: '1', label: { en: 'Mon', es: 'Lun' } },
  { value: '2', label: { en: 'Tue', es: 'Mar' } },
  { value: '3', label: { en: 'Wed', es: 'Mie' } },
  { value: '4', label: { en: 'Thu', es: 'Jue' } },
  { value: '5', label: { en: 'Fri', es: 'Vie' } },
  { value: '6', label: { en: 'Sat', es: 'Sab' } },
  { value: '0', label: { en: 'Sun', es: 'Dom' } },
]

export default function SchedulePicker({ value = '', onChange, lang = 'en' }) {
  const [mode, setMode] = useState('preset') // preset | custom
  const [hour, setHour] = useState('9')
  const [minute, setMinute] = useState('0')
  const [selectedDays, setSelectedDays] = useState([])

  const selectStyle = {
    padding: '6px 10px', borderRadius: 6, border: '1px solid #E5E7EB',
    fontSize: 13, outline: 'none', background: '#fff',
  }

  const toggleDay = (d) => {
    setSelectedDays(prev => {
      const next = prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]
      const days = next.length > 0 ? next.sort().join(',') : '*'
      onChange?.(`${minute} ${hour} * * ${days}`)
      return next
    })
  }

  const handleCustomChange = (h, m) => {
    setHour(h); setMinute(m)
    const days = selectedDays.length > 0 ? [...selectedDays].sort().join(',') : '*'
    onChange?.(`${m} ${h} * * ${days}`)
  }

  return (
    <div style={{ fontSize: 13 }}>
      {/* Mode tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12, background: '#F3F4F6', borderRadius: 8, padding: 3 }}>
        <button onClick={() => setMode('preset')} style={{
          flex: 1, padding: '6px 12px', borderRadius: 6, border: 'none',
          background: mode === 'preset' ? '#fff' : 'transparent',
          fontSize: 12, fontWeight: 600, cursor: 'pointer',
          color: mode === 'preset' ? '#6366F1' : '#6B7280',
          boxShadow: mode === 'preset' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
        }}>{lang === 'es' ? 'Presets' : 'Presets'}</button>
        <button onClick={() => setMode('custom')} style={{
          flex: 1, padding: '6px 12px', borderRadius: 6, border: 'none',
          background: mode === 'custom' ? '#fff' : 'transparent',
          fontSize: 12, fontWeight: 600, cursor: 'pointer',
          color: mode === 'custom' ? '#6366F1' : '#6B7280',
          boxShadow: mode === 'custom' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
        }}>{lang === 'es' ? 'Personalizado' : 'Custom'}</button>
      </div>

      {mode === 'preset' && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {PRESETS.map(p => (
            <button key={p.cron} onClick={() => onChange?.(p.cron)} style={{
              padding: '6px 12px', borderRadius: 6, fontSize: 12,
              border: `1px solid ${value === p.cron ? '#6366F1' : '#E5E7EB'}`,
              background: value === p.cron ? 'rgba(99,102,241,0.08)' : '#fff',
              color: value === p.cron ? '#6366F1' : '#374151',
              cursor: 'pointer', fontWeight: value === p.cron ? 600 : 400,
            }}>
              {p.label[lang]}
            </button>
          ))}
        </div>
      )}

      {mode === 'custom' && (
        <div>
          {/* Time picker */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
            <span style={{ color: '#6B7280' }}>{lang === 'es' ? 'Hora:' : 'Time:'}</span>
            <select value={hour} onChange={e => handleCustomChange(e.target.value, minute)} style={selectStyle}>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={String(i)}>{String(i).padStart(2, '0')}:00</option>
              ))}
            </select>
            <span style={{ color: '#9CA3AF' }}>:</span>
            <select value={minute} onChange={e => handleCustomChange(hour, e.target.value)} style={selectStyle}>
              {['0', '15', '30', '45'].map(m => (
                <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
              ))}
            </select>
          </div>

          {/* Day picker */}
          <div style={{ display: 'flex', gap: 4 }}>
            {DAYS.map(d => (
              <button key={d.value} onClick={() => toggleDay(d.value)} style={{
                width: 36, height: 36, borderRadius: 8, border: 'none',
                background: selectedDays.includes(d.value) ? '#6366F1' : '#F3F4F6',
                color: selectedDays.includes(d.value) ? '#fff' : '#6B7280',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}>
                {d.label[lang]}
              </button>
            ))}
          </div>
          <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 6 }}>
            {selectedDays.length === 0
              ? (lang === 'es' ? 'Todos los dias' : 'Every day')
              : (lang === 'es' ? 'Dias seleccionados' : 'Selected days only')}
          </p>
        </div>
      )}

      {/* Current cron preview */}
      {value && (
        <div style={{
          marginTop: 10, padding: '6px 10px', borderRadius: 6,
          background: '#F9FAFB', border: '1px solid #E5E7EB',
          fontFamily: 'monospace', fontSize: 12, color: '#6B7280',
        }}>
          cron: {value}
        </div>
      )}
    </div>
  )
}

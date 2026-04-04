/**
 * Lightweight confetti animation. No dependencies.
 * Usage: fireConfetti()
 */
export function fireConfetti(duration = 2000) {
  const canvas = document.createElement('canvas')
  canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999'
  document.body.appendChild(canvas)
  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const colors = ['#6366F1', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444', '#3B82F6', '#EC4899']
  const particles = Array.from({ length: 80 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height * -0.5,
    vx: (Math.random() - 0.5) * 8,
    vy: Math.random() * 3 + 2,
    w: Math.random() * 8 + 4,
    h: Math.random() * 6 + 3,
    color: colors[Math.floor(Math.random() * colors.length)],
    rotation: Math.random() * 360,
    rotationSpeed: (Math.random() - 0.5) * 10,
    opacity: 1,
  }))

  const start = Date.now()

  function animate() {
    const elapsed = Date.now() - start
    if (elapsed > duration) {
      canvas.remove()
      return
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const fadeStart = duration * 0.7
    const globalAlpha = elapsed > fadeStart ? 1 - (elapsed - fadeStart) / (duration - fadeStart) : 1

    particles.forEach(p => {
      p.x += p.vx
      p.y += p.vy
      p.vy += 0.1 // gravity
      p.rotation += p.rotationSpeed

      ctx.save()
      ctx.translate(p.x, p.y)
      ctx.rotate((p.rotation * Math.PI) / 180)
      ctx.globalAlpha = globalAlpha
      ctx.fillStyle = p.color
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h)
      ctx.restore()
    })

    requestAnimationFrame(animate)
  }

  animate()
}

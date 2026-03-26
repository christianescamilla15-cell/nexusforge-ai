class LocalSearchEngine {
  constructor() {
    this.documents = [] // { id, title, chunks: [{ text, index, start, end }], fullText, fileType, sizeBytes }
  }

  addDocument(title, content, fileType = 'text', sizeBytes = 0) {
    const chunks = this.chunkText(content, 500, 50)
    const doc = {
      id: Date.now() + Math.random(),
      title,
      chunks,
      fullText: content,
      fileType,
      sizeBytes: sizeBytes || new Blob([content]).size,
      addedAt: new Date().toISOString(),
    }
    this.documents.push(doc)
    return doc
  }

  chunkText(text, size = 500, overlap = 50) {
    const chunks = []
    if (!text || text.length === 0) return chunks
    for (let i = 0; i < text.length; i += size - overlap) {
      chunks.push({
        text: text.slice(i, i + size),
        index: chunks.length,
        start: i,
        end: Math.min(i + size, text.length),
      })
      if (i + size >= text.length) break
    }
    return chunks
  }

  search(query, topK = 5) {
    const queryTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2)
    if (queryTerms.length === 0) return []
    const results = []

    for (const doc of this.documents) {
      for (const chunk of doc.chunks) {
        const chunkLower = chunk.text.toLowerCase()
        let score = 0
        const matchedTerms = []

        for (const term of queryTerms) {
          const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')
          const count = (chunkLower.match(regex) || []).length
          if (count > 0) {
            score += count * (1 / Math.log(chunk.text.length + 1))
            matchedTerms.push(term)
          }
        }

        if (score > 0) {
          const similarity = Math.min(95, Math.round(score * 100 / queryTerms.length * 3))
          results.push({
            docId: doc.id,
            docTitle: doc.title,
            chunkIndex: chunk.index,
            text: chunk.text,
            similarity,
            matchedTerms,
            highlight: this.highlightTerms(chunk.text, matchedTerms),
          })
        }
      }
    }

    return results.sort((a, b) => b.similarity - a.similarity).slice(0, topK)
  }

  highlightTerms(text, terms) {
    let result = text
    for (const term of terms) {
      const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      result = result.replace(new RegExp(`(${escaped})`, 'gi'), '**$1**')
    }
    return result
  }

  getStats() {
    return {
      totalDocs: this.documents.length,
      totalChunks: this.documents.reduce((sum, d) => sum + d.chunks.length, 0),
      totalChars: this.documents.reduce((sum, d) => sum + d.fullText.length, 0),
    }
  }

  getDocuments() {
    return this.documents.map(d => ({
      id: d.id,
      title: d.title,
      fileType: d.fileType,
      sizeBytes: d.sizeBytes,
      chunksCount: d.chunks.length,
      addedAt: d.addedAt,
    }))
  }
}

export const searchEngine = new LocalSearchEngine()

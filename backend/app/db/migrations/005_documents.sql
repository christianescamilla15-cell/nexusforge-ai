CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size_bytes INT,
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'uploaded' CHECK (status IN ('uploaded','processing','indexed','failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_docs_status ON documents(status);

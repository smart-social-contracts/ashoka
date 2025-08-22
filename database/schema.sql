CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_principal TEXT NOT NULL,
    realm_principal TEXT NOT NULL,
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    persona_name TEXT NOT NULL DEFAULT 'ashoka',
    prompt_context TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS realm_status (
    id SERIAL PRIMARY KEY,
    realm_principal TEXT NOT NULL,
    realm_url TEXT NOT NULL,
    status_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_conversations_persona_name ON conversations(persona_name);
CREATE INDEX IF NOT EXISTS idx_conversations_user_realm_persona ON conversations(user_principal, realm_principal, persona_name);

GRANT ALL PRIVILEGES ON TABLE conversations TO ashoka_user;
GRANT USAGE, SELECT ON SEQUENCE conversations_id_seq TO ashoka_user;
GRANT ALL PRIVILEGES ON TABLE realm_status TO ashoka_user;
GRANT USAGE, SELECT ON SEQUENCE realm_status_id_seq TO ashoka_user;

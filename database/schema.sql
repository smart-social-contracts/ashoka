CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_principal TEXT NOT NULL,
    realm_principal TEXT NOT NULL,
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    prompt_context TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT ALL PRIVILEGES ON TABLE conversations TO ashoka_user;
GRANT USAGE, SELECT ON SEQUENCE conversations_id_seq TO ashoka_user;

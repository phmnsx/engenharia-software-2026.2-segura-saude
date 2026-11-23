-- Tabelas de AuditLog e LogSistema
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb
);

-- Função de bloqueio WORM / Append-Only
CREATE OR REPLACE FUNCTION prevent_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Operação proibida (ASR01/RNF001): logs são imutáveis (append-only).';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_log_modification();

CREATE TRIGGER trg_audit_logs_no_truncate
    BEFORE TRUNCATE ON audit_logs
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_log_modification();

CREATE TRIGGER trg_system_logs_immutable
    BEFORE UPDATE OR DELETE ON system_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_log_modification();

CREATE TRIGGER trg_system_logs_no_truncate
    BEFORE TRUNCATE ON system_logs
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_log_modification();

-- Usuário com privilégio mínimo
CREATE ROLE log_writer LOGIN PASSWORD 'log_writer_dev_pass';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO log_writer;
GRANT SELECT, INSERT ON audit_logs, system_logs TO log_writer;
GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq, system_logs_id_seq TO log_writer;

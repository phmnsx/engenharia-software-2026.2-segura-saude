-- Banco principal de metadados (SeguraSaúde)
-- Tabelas: lotes_metadados, metadados e matrizes_risco

CREATE TABLE IF NOT EXISTS lotes_metadados (
    id UUID PRIMARY KEY,
    event_id VARCHAR UNIQUE,
    nome_lote VARCHAR(200) NOT NULL,
    base_legal VARCHAR(200) NOT NULL,
    analista_responsavel VARCHAR(100),
    data_criacao TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metadados (
    id UUID PRIMARY KEY,
    event_id VARCHAR UNIQUE,
    id_lote UUID NOT NULL REFERENCES lotes_metadados(id) ON DELETE CASCADE,
    origem VARCHAR(200) NOT NULL,
    temporalidade VARCHAR(100) NOT NULL,
    crm_responsavel VARCHAR(50) NOT NULL,
    tipo_dado VARCHAR(100),
    categoria VARCHAR(100),
    base_legal VARCHAR(200),
    criptografado BOOLEAN NOT NULL DEFAULT FALSE,
    atores_com_acesso JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS matrizes_risco (
    id UUID PRIMARY KEY,
    id_lote UUID NOT NULL REFERENCES lotes_metadados(id) ON DELETE CASCADE,
    nivel_risco INT NOT NULL,
    recomendacao_acao TEXT NOT NULL,
    detalhes JSONB DEFAULT '[]'::jsonb,
    data_hora TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_metadados_lote ON metadados(id_lote);
CREATE INDEX IF NOT EXISTS idx_lotes_data ON lotes_metadados(data_criacao DESC);
CREATE INDEX IF NOT EXISTS idx_matrizes_lote ON matrizes_risco(id_lote);
CREATE INDEX IF NOT EXISTS idx_matrizes_data ON matrizes_risco(data_hora DESC);

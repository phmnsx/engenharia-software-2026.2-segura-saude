from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID


class MetadadosIn(BaseModel):
    origem: str
    temporalidade: str
    crm_responsavel: str
    tipo_dado: Optional[str] = None
    categoria: Optional[str] = None
    base_legal: Optional[str] = None
    criptografado: bool = False
    atores_com_acesso: List[str] = Field(default_factory=list)


class LoteMetadadosIn(BaseModel):
    nome_lote: str
    base_legal: str = Field(
        ...,
        min_length=1,
        description="Base legal da LGPD (RN01). Campo obrigatório.",
    )
    analista_responsavel: Optional[str] = None
    metadados: List[MetadadosIn] = Field(default_factory=list)


class MetadadosOut(BaseModel):
    id: UUID
    id_lote: UUID
    origem: str
    temporalidade: str
    crm_responsavel: str
    tipo_dado: Optional[str] = None
    categoria: Optional[str] = None
    base_legal: Optional[str] = None
    criptografado: bool
    atores_com_acesso: List[str]


class LoteMetadadosOut(BaseModel):
    id: UUID
    nome_lote: str
    base_legal: str
    analista_responsavel: Optional[str] = None
    data_criacao: datetime
    metadados: List[MetadadosOut] = Field(default_factory=list)


class LoteMetadadosSummaryOut(BaseModel):
    id: UUID
    nome_lote: str
    base_legal: str
    analista_responsavel: Optional[str] = None
    data_criacao: datetime
    total_metadados: int


class DetalheItemRiscoOut(BaseModel):
    id_metadado: Optional[str] = None
    origem: str
    sensibilidade: str
    criptografado: bool
    atores_com_acesso: List[str] = Field(default_factory=list)
    nivel_risco: int
    fatores: List[str] = Field(default_factory=list)


class MatrizDeRiscoOut(BaseModel):
    id: UUID
    id_lote: UUID
    nivel_risco: int
    recomendacao_acao: str
    data_hora: datetime
    detalhes: List[DetalheItemRiscoOut] = Field(default_factory=list)


class AuditLogManualIn(BaseModel):
    """Registro manual de AuditLog pela tela de logs (RF005, RN06).

    O motivo é obrigatório. Espaços nas pontas são removidos antes da
    validação, então um motivo só com espaços é rejeitado (HTTP 422).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    actor_id: str = Field(..., min_length=1, max_length=100)
    actor_role: Literal["ANALISTA", "DESENVOLVEDOR"]
    action: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=150)
    motivo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Motivo da auditoria. Campo obrigatório (RF005).",
    )

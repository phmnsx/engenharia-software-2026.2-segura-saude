from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4


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

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid


class NivelRisco(int, Enum):
    BAIXO = 0
    MEDIO = 1
    ALTO = 2
    CRITICO = 3


class Metadados(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origem: str
    temporalidade: str
    crm_responsavel: str
    tipo_dado: Optional[str] = None
    categoria: Optional[str] = None
    base_legal: Optional[str] = None
    criptografado: bool = False
    atores_com_acesso: List[str] = Field(default_factory=list)


class LoteMetadados(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome_lote: str
    base_legal: str
    data_criacao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analista_responsavel: Optional[str] = None
    metadados: List[Metadados] = Field(default_factory=list)


class MatrizDeRisco(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    id_lote: str
    nivel_risco: NivelRisco
    data_hora: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recomendacao_acao: str
    detalhes: Optional[List[dict]] = None

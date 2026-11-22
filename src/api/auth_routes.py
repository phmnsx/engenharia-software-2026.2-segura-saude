from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel
from api.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])
auth_service = AuthService()
bearer_scheme = HTTPBearer()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        return auth_service.decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )


def require_role(allowed_role: str):
    """Helper já pronto para segregação RBAC (ASR04 / CQ05) nas próximas rotas."""
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != allowed_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: perfil {allowed_role} obrigatório.",
            )
        return user
    return _checker


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    result = auth_service.authenticate(payload.email, payload.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )
    return result


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["sub"],
        "email": current_user["email"],
        "role": current_user["role"],
    }

import os 
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.password_hasher import BcryptPasswordHasher
from app.token_service import JwtTokenService

DATA_SERVICE_URL = os.environ["DATA_SERVICE_URL"].rstrip("/")

app = FastAPI(title="add-ai-auth-service")
_hasher = BcryptPasswordHasher()
_tokens = JwtTokenService(
    secret_key=os.environ["JWT_SECRET_KEY"],
    algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "1440")),
)

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user_id: int
    name: str
    email: str

class VerifyRequest(BaseModel):
    token: str

class VerifyResponse(BaseModel):
    user_id: int
    name: str
    email: str

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    with httpx.Client(base_url=DATA_SERVICE_URL, timeout=10) as client:
        existing = client.get(f"/users/by-email/{req.email}").json()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = _hasher.hash(req.password)
        created = client.post("/users", json={
            "name": req.name, "email": req.email, "hashed_password": hashed,
        }).json()

    token = _tokens.issue_token(created["id"])
    return AuthResponse(token=token, user_id=created["id"], name=created["name"], email=created["email"])


@app.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    with httpx.Client(base_url=DATA_SERVICE_URL, timeout=10) as client:
        user = client.get(f"/users/by-email/{req.email}").json()

    if not user or not _hasher.verify(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _tokens.issue_token(user["id"])
    return AuthResponse(token=token, user_id=user["id"], name=user["name"], email=user["email"])


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    user_id = _tokens.verify_token(req.token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    with httpx.Client(base_url=DATA_SERVICE_URL, timeout=10) as client:
        user = client.get(f"/users/{user_id}").json()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return VerifyResponse(user_id=user["id"], name=user["name"], email=user["email"])

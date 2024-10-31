# Imports
import os
import datetime
from datetime import timedelta, timezone
import time
from typing import Annotated, Optional
from fastapi import Depends, FastAPI, HTTPException, Header, Request, status
import jwt
from pydantic import BaseModel
from sqlalchemy import Integer, String, create_engine, Column
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
import requests
from jwt.exceptions import InvalidTokenError

# Variaveis de ambiente
from dotenv import load_dotenv

load_dotenv()

DB_USERNAME = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SERVER = "db"
DB_PORT = 5432
DB_NAME = os.getenv("POSTGRES_DB")

SECRET_KEY = "13d9e823b00a02e37a52ed719c21ff31380bd402b8f8a13eae3f90bc0d692500"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = None
if DB_USERNAME and DB_PASSWORD and DB_SERVER and DB_PORT and DB_NAME:
    DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"

# Essenciais (setup)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos
class User(Base):
    __tablename__ = "usuarios"

    nome = Column(String(100))
    email = Column(String(100), primary_key=True)
    senha = Column(String(100))

    def __repr__(self):
        return f"<Usuario {self.email}>"

class Token(BaseModel):
    jwt: str

class TokenData(BaseModel):
    email: str

class Usuario(BaseModel):
    email: str
    nome: str

class UsuarioInDB(Usuario):
    hashed_password: str

class UsuarioCreate(Usuario):
    senha: str

class UsuarioLogin(BaseModel):
    email: str
    senha: str

class UsuarioPublic(BaseModel):
    email: str
    nome: str
    senha: str

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token if decoded_token["exp"] >= time.time() else None
    except:
        return {}

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Schema inválido de autenticação.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Token inválido ou expirado.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Código de autorização inválido.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = decodeJWT(jwtoken)
        except:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid

# Funcoes
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
    
def authenticate_user(password: str, user: User):
    return verify_password(password, user.senha)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(JWTBearer())], db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        token_data = TokenData(email=email)
    except InvalidTokenError:
        return None
    user = get_user(db, email=token_data.email)
    if user is None:
        return None
    return user

# APP START
Base.metadata.create_all(bind=engine)
app = FastAPI()

# Rotas
@app.post("/registrar")
async def register_new_user(usuario: UsuarioCreate, db: Session = Depends(get_db)) -> Token:
    user = get_user(db, usuario.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User já existe"
        )
    
    nova_senha = get_password_hash(usuario.senha)
    novo_user = User(email=usuario.email, nome=usuario.nome, senha=nova_senha)
    db.add(novo_user)
    db.flush()
    db.commit()
    db.refresh(novo_user)
    
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": novo_user.email}, expires_delta=access_token_expires
    )
    return Token(jwt=access_token)

@app.post("/login")
async def login_user(usuario: UsuarioLogin, db: Session = Depends(get_db)) -> Token:
    user = get_user(db, usuario.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User não existe")
    if not authenticate_user(usuario.senha, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")
    
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(jwt=access_token)

@app.get("/consulta")
def consultar_api(user: Annotated[UsuarioInDB, Depends(get_current_user)]):
    # return user
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não pode ser validado"
        )
    resposta = requests.get("https://api.jikan.moe/v4/random/anime")
    if resposta.status_code == 200:
        return resposta.json()
    else:
        return {"Reponse Code": resposta.status_code}

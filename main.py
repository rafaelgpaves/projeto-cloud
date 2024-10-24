# Imports
import os
import datetime
from datetime import timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
import jwt
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError

# Variaveis de ambiente
from dotenv import load_dotenv

load_dotenv()

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SERVER = os.getenv("DB_SERVER")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

DATABASE_URL = None
if DB_USERNAME and DB_PASSWORD and DB_SERVER and DB_PORT and DB_NAME:
    DATABASE_URL = f"postgres://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"

# Modelos
class Token(BaseModel):
    access_token: str

class TokenData(BaseModel):
    email: str

class Usuario(BaseModel):
    email: str
    nome: str

class UsuarioInDB(Usuario):
    hashed_password: str

# Essenciais (setup)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Funcoes
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db: Session, email: str):
    return db.query(UsuarioInDB).filter(Usuario.email == email).first()
    
def authenticate_user(password: str, user: UsuarioInDB):
    return verify_password(password, user.hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Rotas
@app.post("/registrar")
async def register_new_user(nome: str, email: str, senha: str, db: Session = Depends(get_db)) -> Token:
    user = get_user(db, email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User já existe"
        )
    
    senha = get_password_hash(senha)
    novo_user = UsuarioInDB(email=email, nome=nome, senha=senha)
    db.add(novo_user)
    db.flush(novo_user)
    db.commit()
    db.refresh(novo_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": novo_user.email}, expires_delta=access_token_expires
    )
    return {"jwt": access_token}

@app.post("/login")
async def login_user(email: str, senha: str, db: Session = Depends(get_db)) -> Token:
    user = get_user(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User não existe")
    if not authenticate_user(senha, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"jwt": access_token}

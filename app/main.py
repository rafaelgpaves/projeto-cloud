# Imports
import os
import datetime
from datetime import timedelta, timezone
from typing import Annotated, Optional
from fastapi import Depends, FastAPI, HTTPException, Header, status
import jwt
from pydantic import BaseModel
from sqlalchemy import Integer, String, create_engine, Column
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import requests
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
    DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"

# Essenciais (setup)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, username=token_data.email)
    if user is None:
        raise credentials_exception
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
    print("AAAAAAAAAAAAAAAAAAA", usuario.senha, nova_senha)
    novo_user = User(email=usuario.email, nome=usuario.nome, senha=nova_senha)
    print(novo_user.email)
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
async def consultar_api(user: Annotated[UsuarioInDB, Depends(get_current_user), Header()]):
    response = await requests.get("https://cat-fact.herokuapp.com/facts")
    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Error: {response.status_code}")

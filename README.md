# Projeto de Computação em Nuvem, 6° semestre de Engenharia da Computação do Insper

Desenvolvido por Rafael Gordon Paves.

## Sobre o projeto

Nesse projeto, foi feita uma API conectada a um banco de dados Postgres, em uma aplicação conteinerizada.

Um dos requisitos era fazer um web scraping ou usar uma api atualizada regularmente. Neste projeto, escolhi [Jikan](https://jikan.moe/), uma api com dados de animes, mangás, personagens, produtoras, usuários, entre outros que estão no site MyAnimeList.

## Executando a aplicação

1. Puxe a imagem:
```
docker pull rafaelgp3/
``` 

2. Rode o conteiner:
```
docker compose up
```

3. Para testar, pode entrar na documentação própria do FastAPI (Swagger) em http://localhost:8000/docs 

4. Quando quiser sair, pare o conteiner (rode esse comando em outro terminal):
```
docker compose down
```


## Rotas

POST /registrar
- Requer no corpo da requisição 3 chaves: "email", "nome" e "senha".
- Em sucesso, devolve um token jwt, com expiração de 30 minutos, no formato {"jwt": ${token}}
- Um exemplo usando curl:

```terminal
curl -X 'POST' \
  'http://127.0.0.1:8000/registrar' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "rafaelgpaves@gmail.com",
  "nome": "Rafael",
  "senha": "senhasupersecreta"
}'
```

POST /login
- Requer no corpo da requisição 2 chaves: "email" e "senha".
- Em sucesso, devolve um token jwt, com expiração de 30 minutos, no formato {"jwt": ${token}}
- Um exemplo usando curl:

```terminal
curl -X 'POST' \
  'http://127.0.0.1:8000/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "rafaelgpaves@gmail.com",
  "senha": "senhasupersecreta"
}'
```

GET /consulta
- Requer no cabeçalho um token jwt válido (obtido a partir das rotas registrar ou login)
- Em sucesso, devolve dados de um anime aleatório da API mencionada anteriormente pela rota https://api.jikan.moe/v4/random/anime. Alguns dados retornados incluem o nome do anime, data de lançamento, link para o trailer, sinopse, estúdio que produziu, entre outros.
- Um exemplo usando curl (não coloque '$', '{', '}', apenas o token):

```
curl -X 'GET' \
  'http://127.0.0.1:8000/consulta' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer ${token}'
}'
```

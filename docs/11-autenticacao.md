# 11 — Autenticacao e Autorizacao

## Tipo de Auth

- **JWT (JSON Web Tokens)**, algoritmo **HS256**
- **Access token** expira em 24 horas (`ACCESS_TOKEN_EXPIRE_MINUTES`, default `1440`)
- **Refresh token** expira em 7 dias (`REFRESH_TOKEN_EXPIRE_MINUTES`, default `10080`)

## Fluxo

1. Usuario faz login: `POST /auth/login` com email + senha
2. Sistema verifica credenciais (bcrypt)
3. Sistema retorna **access token** + **refresh token**
4. Cliente envia o access token em todas as requisicoes: `Authorization: Bearer <token>`
5. Backend valida o token em cada request
6. Quando o access expira, `POST /auth/refresh` com o refresh token devolve um **novo par** (refresh token e rotacionado)

## Cadastro

`POST /auth/register`:
```json
{
  "company_name": "Minha Empresa",
  "name": "Joao",
  "email": "joao@empresa.com",
  "password": "senha123"
}
```

Cria automaticamente:
- 1 empresa
- 1 usuario (role: **owner**)
- Config padrao para a empresa

## Login

`POST /auth/login` (corpo: `{"username": <email>, "password": <senha>}` — exige `Content-Type: application/x-www-form-urlencoded`):

Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {}
}
```

## Gerenciamento de Sessao / Senha

- `POST /auth/refresh` — corpo `{"refresh_token": "..."}`; renova o par; refresh possui `type=refresh` e **nao** e aceito como access (401).
- `POST /auth/change-password` — corpo `{"current_password", "new_password"}` (autenticado; nova senha minima 6 caracteres).
- `POST /auth/forgot-password` — corpo `{"email"}`; envia email com link; resposta generica (anti-enumercao). Requer SMTP configurado, senao retorna **503**. Taxa limitada (10/min).
- `POST /auth/reset-password` — corpo `{"token", "new_password"}`; token gravado apenas como hash SHA-256, de **uso unico** (usado/validade respondem 400).

## Token

```json
{
  "sub": "1",           // user_id
  "company_id": "1",
  "role": "owner",
  "type": "access"      // ou "refresh"
}
```

## Roles

| Role | Descricao |
|------|-----------|
| `owner` | Acesso total a empresa (criado no cadastro) |
| `admin` | Gerenciamento (criado via `/users/`) |
| `agent` | Acesso basico |

## Protecao dos Endpoints

```python
# No router:
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    return decode_access_token(token, db)

# Usando:
@router.get("/items/")
def list_items(current_user: User = Depends(get_current_user)):
    # current_user.user e o usuario autenticado
    pass
```

## Senhas

- Hasheadas com **bcrypt**
- Nao armazenadas em texto puro
- Verificadas com `verify_password(plain, hashed)`
- Geracao de senha nova nao impoe complexidade (somente minimo de 6 caracteres nos fluxos de troca/reset)

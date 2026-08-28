# 11 — Autenticacao e Autorizacao

## Tipo de Auth

- **JWT (JSON Web Tokens)**
- **Algoritmo:** HS256
- **Expiracao:** 24 horas (1440 minutos)

## Fluxo

1. Usuario faz login: `POST /auth/login` com email + senha
2. Sistema verifica credenciais (bcrypt)
3. Sistema retorna token JWT
4. Cliente envia token em todas as requisicoes: `Authorization: Bearer <token>`
5. Backend valida o token em cada request

## Cadastro

`POST /auth/register`:
```json
{
  "company_name": "Minha Empresa",
  "user_name": "Joao",
  "email": "joao@empresa.com",
  "password": "senha123"
}
```

Cria automaticamente:
- 1 empresa
- 1 usuario (role: "admin")
- Config padrao para a empresa

## Login

`POST /auth/login`:
```json
{
  "email": "joao@empresa.com",
  "password": "senha123"
}
```

Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Token

```json
{
  "sub": "1",           // user_id
  "company_id": "1",
  "role": "admin"
}
```

## Roles

| Role | Descricao |
|------|-----------|
| `admin` | Acesso total a empresa |
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

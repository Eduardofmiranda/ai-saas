# 18 — Troubleshooting

## Problemas Comuns

### Backend nao inicia

**Erro:** `ModuleNotFoundError: No module named 'X'`

**Solucao:**
```bash
pip install -r requirements.txt
```

### Erro de conexao com banco

**Erro:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Verificar:**
1. `DATABASE_URL` esta correto?
2. PostgreSQL esta rodando?
3. Firewall nao bloqueia porta 5432?

### Erro de JWT

**Erro:** `jwt.exceptions.DecodeError`

**Verificar:**
1. `SECRET_KEY` e a mesma usada para criar o token?
2. Token nao expirou (24h)?

### Erro de IA

**Erro:** `httpx.HTTPStatusError: 401 Unauthorized`

**Verificar:**
1. `ai_api_key` esta configurada?
2. Chave e valida no provedor?
3. Chave esta criptografada corretamente?

### Erro de WhatsApp

**Erro:** `Evolution API error: instance not found`

**Verificar:**
1. `EVOLUTION_BASE_URL` esta correto?
2. `EVOLUTION_API_KEY` e valido?
3. `EVOLUTION_INSTANCE` existe na Evolution?
4. Webhook esta configurado na Evolution?

### Frontend nao conecta ao backend

**Erro:** `Failed to fetch`

**Verificar:**
1. Backend esta rodando na porta 8000?
2. `VITE_API_BASE` esta correto?
3. CORS esta configurado?

### Docker compose nao sobe

**Erro:** `port is already allocated`

**Solucao:**
```bash
# Verificar o que esta usando a porta
netstat -ano | findstr :8000

# Matar o processo ou mudar a porta no docker-compose.yml
```

### Erro de criptografia

**Erro:** `cryptography.fernet.InvalidToken`

**Verificar:**
1. `SECRET_ENCRYPTION_KEY` e a mesma usada para criptografar?
2. Chave foi alterada depois de salvar dados criptografados? (NAO ALTERAR)

### Testes falham

**Erro:** `sqlite3.OperationalError: no such table`

**Solucao:**
```bash
pytest tests/ -xvs
# Os testes usam SQLite em memoria e criam tabelas automaticamente
```

## Logs

### Ver logs do backend (Docker)
```bash
docker compose logs -f backend
```

### Ver logs do Celery
```bash
docker compose logs -f celery-worker
```

### Ver logs do nginx (frontend)
```bash
docker compose logs -f frontend
```

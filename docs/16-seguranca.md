# 16 — Seguranca

## Medidas Implementadas

### Senhas
- Hasheadas com **bcrypt**
- Nunca armazenadas em texto puro
- Verificadas com `verify_password()`

### JWT
- Tokens assinados com HS256
- Expiracao: 24 horas
- Payload: user_id, company_id, role

### Credenciais Criptografadas
- `ai_api_key` e `evolution_api_key` criptografadas com **Fernet** (AES-128-CBC + HMAC-SHA256)
- Chave derivada via PBKDF2 de `SECRET_ENCRYPTION_KEY` ou `SECRET_KEY`
- Prefijo `enc:` para identificar valores criptografados
- Retrocompatibilidade com texto puro legado

```python
# app/services/field_crypto.py
encrypted = encrypt_field("minha-chave")  # → "enc:gAAAAABh..."
decrypted = decrypt_field("enc:gAAAAABh...")  # → "minha-chave"
decrypted = decrypt_field("chave-legada")  # → "chave-legada" (sem alteracao)
```

### Isolamento Multi-tenant
- Todas as queries filtram por `company_id`
- Usuario so ve dados da propria empresa
- `company_id` extraido do token JWT

### Validacao de Entrada
- Pydantic valida todos os inputs
- Required fields obrigatorios
- Tipos validados automaticamente

### Tratamento de Erros
- Erros retornam `{detail: "mensagem"}`
- SQL errors tratados (duplicate key)
- 401 para nao autenticado
- 403 para nao autorizado

## Riscos Conhecidos

1. **Credenciais VAZADAS em logs de conversa (03/09/2026)** — Ainda em uso,
   exigem rotacao imediata:
   - Chave da Groq (`DEFAULT_AI_API_KEY`) — rotacionar em console.groq.com.
   - Senha do Postgres local (`POSTGRES_PASSWORD` / `DATABASE_URL`) — `yangeme`.
   - Chave da Evolution (`EVOLUTION_AUTH_KEY` / `EVOLUTION_API_KEY`).
   - `SECRET_KEY` e `SECRET_ENCRYPTION_KEY` estavam **iguais** — usar valores
     distintos e rotacionar (cuidado: rotacionar quebra a descriptografia das
     chaves criptografadas ja salvas; planejar migracao).
   - `REDIS_URL` ja apontou para um Redis externo (Redis Cloud) com senha exposta
     — corrigido para o Redis interno no `.env` atual.
2. **Rate limiting** — Nao implementado. Vulneravel a brute force.
3. **HTTPS** — Nao configurado. Necessario para producao.
4. **CORS** — Configurado apenas para localhost:5173 em dev. Ajustar para producao.
5. **Injection** — SQLAlchemy usa queries parametrizadas (protegido contra SQL injection).
6. **XSS** — React escapa por padrao. Nao usa dangerouslySetInnerHTML.

## Checklist Antes de Producao

- [ ] Rotacionar **todas** as credenciais vazadas (Groq, postgres, Evolution, SECRET_*)
- [ ] Garantir `SECRET_KEY` != `SECRET_ENCRYPTION_KEY`
- [ ] Configurar HTTPS
- [ ] Configurar CORS para dominio real
- [ ] Configurar rate limiting
- [ ] Remover dados sensiveis dos logs
- [ ] Revisar permissoes de acesso

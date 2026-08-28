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

1. **Credenciais vazadas** — Senha Supabase, chave Groq expostas no historico. **URGENTE: rotacionar antes de producao.**
2. **Rate limiting** — Nao implementado. Vulneravel a brute force.
3. **HTTPS** — Nao configurado. Necessario para producao.
4. **CORS** — Configurado apenas para localhost:5173 em dev. Ajustar para producao.
5. **Injection** — SQLAlchemy usa queries parametrizadas (protegido contra SQL injection).
6. **XSS** — React escapa por padrao. Nao usa dangerouslySetInnerHTML.

## Checklist Antes de Producao

- [ ] Rotacionar credenciais vazadas
- [ ] Configurar HTTPS
- [ ] Configurar CORS para dominio real
- [ ] Configurar rate limiting
- [ ] Remover dados sensiveis dos logs
- [ ] Revisar permissoes de acesso

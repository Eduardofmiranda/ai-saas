# 16 — Seguranca

## Medidas Implementadas

### Senhas
- Hasheadas com **bcrypt**
- Nunca armazenadas em texto puro
- Verificadas com `verify_password()`

### JWT
- Tokens assinados com HS256 (via **PyJWT** 2.13.0; `python-jose` removido em 08/09/2026)
- **Access token** expira em 24 horas (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh token** expira em 7 dias (`REFRESH_TOKEN_EXPIRE_MINUTES`) com claim `type=refresh`;
  usado apenas em `POST /auth/refresh` (rotacionado); access token nao e aceito como refresh (401)
- Payload: user_id, company_id, role, type
- **`SECRET_KEY` obrigatoria no startup** — se nao estiver definida no
  ambiente, o aplicativo **nao inicia** (exibe erro e sai com `sys.exit(1)`).
  Nao existe mais valor fallback `"dev-secret"`.

### Recuperacao de Senha
- `POST /auth/forgot-password` gera token aleatorio; apenas o **hash SHA-256** e persistido
- Token de reset e de **uso unico** (`used_at`) e expira em `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` (default 60)
- Resposta generica para email conhecido/desconhecido (anti-enumeracao)
- Sem SMTP configurado, `forgot-password` retorna **503** (nao simula envio)
- `POST /auth/forgot-password` com rate limit de **10/min**

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

### Autenticacao Obrigatoria em Todos os Routers de Dados
Todos os routers que manipulam dados sao protegidos por `Depends(get_current_user)`:

- `conversation_router.py` — todos os endpoints
- `message_router.py` — todos os endpoints
- `company_router.py` — todos os endpoints
- `customer_router.py` — todos os endpoints
- `workflow_router.py` — ja protegido
- `knowledge_router.py` — ja protegido
- `config_router.py` — ja protegido
- `dashboard_router.py` — ja protegido
- `users_router.py` — ja protegido

### Isolamento Multi-tenant
- Todas as queries filtram por `company_id` do usuario logado
- Usuario so ve dados da propria empresa
- `company_id` extraido do token JWT
- Acesso cross-tenant retorna **403** (ex.: acessar `/{company_id}` de outra empresa)

### Webhook com Autenticacao
- O webhook `POST /webhook/whatsapp/{company_id}` valida o header
  **`evolution-auth`** contra `EVOLUTION_AUTH_KEY` (comparacao via
  `hmac.compare_digest` para evitar timing attacks).
- Requisicao sem header valido retorna **401**.
- Isso impede injecao de mensagens falsas por terceiros.

### Rate Limiting
- Implementado via **slowapi** (adicionado ao `requirements.txt`).
- Login: **5 tentativas/minuto** por IP.
- Registro: **5 tentativas/minuto** por IP.
- Recuperacao de senha (`forgot-password`): **10 tentativas/minuto** por IP.
- Resposta padrao de excesso: HTTP **429** com mensagem em portugues.
- O import e condicional (via `try/except ImportError`), entao o app funciona
  mesmo se slowapi nao estiver instalado (apenas sem rate limiting).

### Garantia Transacional contra Dupla Reserva (Agenda)
- **Implementado:** `_serialize_booking` em `app/services/agenda.py` usa
  `pg_advisory_xact_lock` transacional chaveado por `(company_id, date)` antes
  da leitura de conflito em `add_appointment`/`update_appointment`.
- Em READ COMMITTED (Supabase), a segunda transacao bloqueada so executa o
  `has_conflict` apos o commit da primeira, enxergando a linha recem-gravada.
- Em SQLite (dev/testes): no-op (lock global de escrita do banco ja serializa).
- Migration `0015`: indice composto `(company_id, date)` para performance.
- Teste concorrente em `tests/test_agenda_concurrency.py` (Postgres descartavel
  via `TEST_POSTGRES_URL`, CI-only).
- Veja `docs/SEGURANCA-2026-09-08-AGENDA.md` (item #2 concluido).

### Confirmacao Server-side (Agenda)
- **Implementado (criacao, 8.6b):** criacao provisoria (`awaiting_confirmation`)
  + resposta `CONFIRMAR`/`CANCELAR` processada de forma deterministica no webhook
  (sem LLM).
- **Implementado (remarcar/cancelar):** com `confirmation_required` ativo,
  `alterar_agendamento` (data/horario) e `cancelar_agendamento` via tools da IA
  criam registro em `pending_appointment_actions` e enviam pedido de confirmacao;
  a acao so e efetivada apos o cliente responder CONFIRMAR. CANCELAR mantem o
  compromisso original. Pendencia e escopada ao telefone do dono e expira em
  `confirmation_expiry_hours` (o compromisso original permanece inalterado).

### CORS via Ambiente
- Origens permitidas configuradas pela env var `ALLOWED_ORIGINS`
  (lista separada por virgula).
- Default seguro: `http://localhost:5173,http://127.0.0.1:5173`.
- Permite configurar o dominio real de producao sem alterar codigo.

### Healthcheck
- Endpoint `GET /health` retorna `{"status": "healthy"}`.
- Util para monitoramento / healthcheck no Docker.

### Validacao de Entrada
- Pydantic valida todos os inputs
- Required fields obrigatorios
- Tipos validados automaticamente

### Tratamento de Erros
- Erros retornam `{detail: "mensagem"}`
- SQL errors tratados (duplicate key)
- 401 para nao autenticado
- 403 para nao autorizado (cross-tenant)
- 429 para rate limit

## Riscos Conhecidos / Pendentes

1. **HTTPS** — **Nao configurado** (IP sem dominio). Necessario para producao.
   Considerar Caddy, nginx + Let's Encrypt, ou Cloudflare Tunnel.
2. **Confirmacao de rotacao na VPS** — As credenciais foram rotacionadas no
   `.env` local, mas a **rotacao real nos servicos (Groq, Postgres da VPS,
   Evolution) e confirmacao de que o WhatsApp continua conectado** devem ser
   feitas manualmente na VPS.
3. **Injection** — SQLAlchemy usa queries parametrizadas (protegido contra SQL injection).
4. **XSS** — React escapa por padrao. Nao usa dangerouslySetInnerHTML.

> Confirmacao server-side da agenda (criar/remarcar/cancelar com consentimento
> real do cliente) e garantia transacional contra dupla reserva estao
> **implementadas** — veja as secoes acima e `docs/SEGURANCA-2026-09-08-AGENDA.md`.
> Pendentes na agenda: limites de abuso por empresa/cliente e permissoes
> granulares dos operadores.

## Checklist Antes de Producao

- [x] Rotacionar credenciais vazadas **no `.env` local** (Groq marcada para troca manual)
- [ ] Confirmar rotacao na VPS (Groq console, Postgres da VPS, Evolution) e WhatsApp conectado
- [x] Garantir `SECRET_KEY` != `SECRET_ENCRYPTION_KEY` (valores distintos)
- [ ] Configurar HTTPS
- [x] Proteger todos os routers com autenticacao (multi-tenant)
- [x] Validar autenticacao do webhook Evolution
- [x] Configurar rate limiting (login/registro)
- [x] Configurar CORS via `ALLOWED_ORIGINS`
- [ ] Remover dados sensiveis dos logs
- [ ] Revisar permissoes de acesso

# Setup VPS Completo - E2E

## Configuracao Recomendada

| Recurso | Minimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disco | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Preco | $4-6/mes | $6-12/mes |

**Provedores sugeridos:**
- DigitalOcean ($6/mes - 1GB RAM, 25GB SSD)
- Vultr ($6/mes - 1GB RAM, 25GB SSD)
- Hetzner ($4.50/mes - 2 vCPU, 4GB RAM)

---

## Passo 1: Acessar a VPS

```bash
# Apos comprar a VPS, voce recebera um IP e senha
ssh root@SEU_IP
```

## Passo 2: Atualizar o Sistema

```bash
apt update && apt upgrade -y
```

## Passo 3: Instalar Docker

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Habilitar Docker
systemctl enable --now docker

# Verificar
docker --version
```

## Passo 4: Instalar Docker Compose

```bash
# Docker Compose ja vem junto com Docker
docker compose version
```

## Passo 5: Instalar Git

```bash
apt install git -y
```

## Passo 6: Criar Usuario Non-Root (Opcional)

```bash
# Criar usuario deploy
adduser deploy
usermod -aG docker deploy

# Trocar para usuario deploy
su - deploy
```

## Passo 7: Clonar o Repositorio

```bash
cd /opt
git clone https://github.com/Eduardofmiranda/ai-saas.git
cd ai-saas
```

## Passo 8: Criar Arquivo .env

O repositorio ja vem com um exemplo pronto para producao. Use-o:

```bash
cp .env.production.example .env

# Editar com suas configuracoes
nano .env
```

> **Nota:** nao use o `.env.example` para a VPS. Use o `.env.production.example`, que ja foi feito para producao com Supabase.

### Explicacao das variaveis mais confusas:

| Variavel | O que faz | De onde vem |
|----------|-----------|-------------|
| `DATABASE_URL` | Connection string do banco PostgreSQL | **Supabase** (seguindo seu projeto). Cole a string do painel do Supabase |
| `SECRET_KEY` | Assina os tokens JWT de login | Gere na VPS com `openssl rand -hex 32`. Nao e um valor real fixo |
| `SECRET_ENCRYPTION_KEY` | Criptografa chaves IA/Evolution de cada empresa | Gere na VPS com `openssl rand -hex 32` |
| `DEFAULT_AI_*` | Chave/modelo de IA padrao (Groq) | Sua chave no painel da Groq |
| `EVOLUTION_*` | Conexao com a Evolution API (WhatsApp) | Voce define (criar instancia) |
| `REDIS_URL` | Fila do Celery | Mantenha `redis://redis:6379/0` (servico interno do docker) |

### Gerar Chaves Secretas (na VPS):

```bash
# Gerar SECRET_KEY
openssl rand -hex 32

# Gerar SECRET_ENCRYPTION_KEY
openssl rand -hex 32
```

Cole os dois resultados no `.env` (nos campos `SECRET_KEY` e `SECRET_ENCRYPTION_KEY`).

## Passo 9: Subir Database com Supabase

O banco usado e o **Supabase** (nao roda Postgres local). Confirme no `.env`:

```env
DATABASE_URL=postgresql://postgres:SUA_SENHA_SUPABASE@db.SEU_PROJETO.supabase.co:5432/postgres
```

O `docker-compose.yml` do repositorio ja usa essa variavel. Nada mais a fazer aqui.

## Passo 10: Subir os Servicos (RAILWAY/BACKEND/FRONTEND)

O repositorio ja tem todo o `docker-compose.yml`. Basta subir:

```bash
# Build e subir (backend, celery, frontend, redis)
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f backend
```

## Passo 11: Subir a Evolution API (WhatsApp) separadamente

A Evolution API usa um compose proprio (nao interfere no principal):

```bash
# Usa o docker-compose.evolution.yml que ja esta no repositorio
docker compose -f docker-compose.evolution.yml up -d

# Verificar status
docker compose -f docker-compose.evolution.yml ps
```

## Passo 12: Rodar Migracoes

```bash
# Criar tabelas no banco (Supabase)
docker compose exec backend python -c "from app.create_tables import *"
```

## Passo 13: Configurar Evolution API

> **Antes de comecar:** a Evolution API e **open-source e self-hosted**. Nao ha inscricao/cadastro em site deles. Voce mesmo instala a imagem Docker na sua VPS e conecta no seu proprio numero de WhatsApp. O unico passo manual e escanear o QR Code uma vez. A `EVOLUTION_API_KEY` e uma senha que VOCE cria ao instalar.

### Subir a Evolution (se ainda nao subiu no Passo 11):

```bash
docker compose -f docker-compose.evolution.yml up -d
```

### Criar Instancia:

```bash
# Criar instancia "flowai"
curl -X POST http://localhost:8080/instance/createFlowAi \
  -H "Content-Type: application/json" \
  -H "apikey: meu-secret-key-evolution-123" \
  -d '{
    "instanceName": "flowai",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

### Conectar WhatsApp:

1. Apos criar a instancia, voce recebera um QR Code
2. Abra o WhatsApp no celular
3. Va em **Aparelhos conectados** > **Conectar aparelho**
4. Escaneie o QR Code

### Configurar Webhook:

```bash
# Configurar webhook para receber mensagens
curl -X POST http://localhost:8080/webhook/setFlowai \
  -H "Content-Type: application/json" \
  -H "apikey: meu-secret-key-evolution-123" \
  -d '{
    "enabled": true,
    "url": "http://backend:8000/webhook/whatsapp/1",
    "events": ["messages.upsert"]
  }'
```

## Passo 14: Acessar o Sistema

1. Acesse `http://SEU_IP`
2. Faca cadastro (criara uma empresa automaticamente)
3. Va em **Configuracoes** e configure:
   - Chave IA (ja vem configurada com Groq)
   - Evolution API (ja vem configurada)
4. Crie um workflow ou use um template
5. Ative o workflow
6. Envie uma mensagem no WhatsApp conectado

## Passo 15: Configurar SSL (Recomendado)

### Opcao 1: Cloudflare (Mais Facil)

1. Crie uma conta no Cloudflare (gratis)
2. Adicione seu dominio
3. Ative o proxy (nuvem laranja)
4. O HTTPS ja funciona automaticamente

### Opcao 2: Certbot (Mais Avancado)

```bash
# Instalar Nginx
apt install nginx -y

# Configurar Nginx
cat > /etc/nginx/sites-available/flowai << 'EOF'
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /webhook/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Ativar site
ln -s /etc/nginx/sites-available/flowai /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Instalar Certbot
apt install certbot python3-certbot-nginx -y
certbot --nginx -d seu-dominio.com
```

## Troubleshooting

### Ver logs de todos os servicos:

```bash
docker compose logs -f
```

### Reiniciar um servico especifico:

```bash
docker compose restart backend
```

### Parar tudo:

```bash
docker compose down
```

### Limpar tudo (cuidado!):

```bash
docker compose down -v
```

### Verificar se os servicos estao rodando:

```bash
docker compose ps
```

### Testar conexao com banco:

Como o banco e o Supabase (externo), teste direto:

```bash
# De dentro do container do backend
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(engine.connect().execute(text('SELECT 1')).scalar())"
```

### Testar conexao com Redis:

```bash
docker compose exec redis redis-cli ping
```

### Verificar webhook:

```bash
# Testar se o backend esta respondendo
curl http://localhost:8000/

# Verificar se a Evolution API esta rodando
curl http://localhost:8080/
```

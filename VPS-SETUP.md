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

```bash
# Copiar exemplo
cp .env.example .env

# Editar com suas configuracoes
nano .env
```

### Conteudo do .env para Producao:

```env
# Database (Supabase)
DATABASE_URL=postgresql://postgres:Du297845%40%40%40@db.iedkugumqyweawhcepgt.supabase.co:5432/postgres

# Redis (local)
REDIS_URL=redis://localhost:6379/0

# Security (Gere uma chave nova!)
SECRET_KEY=cole-uma-chave-secreta-aqui-openssl-rand-hex-32
SECRET_ENCRYPTION_KEY=cole-outra-chave-secreta-aqui-openssl-rand-hex-32

# AI Defaults (Groq)
DEFAULT_AI_PROVIDER=groq
DEFAULT_AI_MODEL=qwen/qwen3.8-27b
DEFAULT_AI_API_KEY=sua-chave-groq-aqui

# Evolution API
EVOLUTION_BASE_URL=http://evolution:8080
EVOLUTION_API_KEY=meu-secret-key-evolution-123
EVOLUTION_INSTANCE=flowai
```

### Gerar Chaves Secretas:

```bash
# Gerar SECRET_KEY
openssl rand -hex 32

# Gerar SECRET_ENCRYPTION_KEY
openssl rand -hex 32
```

## Passo 9: Criar docker-compose.yml Completo

```bash
# Criar docker-compose.yml com todos os servicos
cat > docker-compose.yml << 'EOF'
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: ai_saas
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  evolution:
    image: atendai/evolution-api:v2.2.3
    container_name: evolution
    environment:
      - SERVER_URL=http://localhost:8080
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY:-meu-secret-key-123}
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/ai_saas
      - CACHE_REDIS_ENABLED=false
      - WEBHOOK_GLOBAL_ENABLED=false
      - LOG_LEVEL=WARN
    volumes:
      - evolution_instances:/evolution/instances
      - evolution_store:/evolution/store
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: backend
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/ai_saas
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: celery-worker
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/ai_saas
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: celery-beat
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/ai_saas
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: ../Dockerfile.frontend
    container_name: frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  evolution_instances:
  evolution_store:
EOF
```

## Passo 10: Subir os Servicos

```bash
# Build e subir
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f backend
```

## Passo 11: Rodar Migracoes

```bash
# Criar tabelas
docker compose exec backend python -c "from app.create_tables import *"
```

## Passo 12: Configurar Evolution API

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

## Passo 13: Acessar o Sistema

1. Acesse `http://SEU_IP`
2. Faca cadastro (criara uma empresa automaticamente)
3. Va em **Configuracoes** e configure:
   - Chave IA (ja vem configurada com Groq)
   - Evolution API (ja vem configurada)
4. Crie um workflow ou use um template
5. Ative o workflow
6. Envie uma mensagem no WhatsApp conectado

## Passo 14: Configurar SSL (Recomendado)

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

```bash
docker compose exec postgres psql -U postgres -d ai_saas
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

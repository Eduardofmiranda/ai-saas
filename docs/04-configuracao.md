# 04 — Configuracao

> Atualização de segurança (07/09/2026): consulte
> [a primeira etapa de proteção](SEGURANCA-2026-09-07.md) para as restrições
> atuais da API. Os campos de infraestrutura dos exemplos abaixo exigem
> superadmin; as rotas WhatsApp usam URL/chave do ambiente. A política de IA
> por usuário está parcialmente implementada, com pendências registradas ali.

## Arquivos de Configuracao

| Arquivo | Finalidade |
|---------|-----------|
| `.env` | Variaveis de ambiente (nao versionado) |
| `.env.example` | Template de variaveis de ambiente |
| `alembic.ini` | Configuracao do Alembic (migrations) |
| `docker-compose.yml` | Orquestracao dos containers |
| `docker-compose.dev.yml` | Overrides para desenvolvimento (usar `-f` explicitamente) |
| `frontend/vite.config.js` | Configuracao do Vite (build) |
| `frontend/nginx.conf` | Configuracao do nginx (producao) |

## Configuracao por Empresa

A configuracao de IA e WhatsApp e feita por empresa via API `PATCH /config/`:

```json
{
  "ai_provider": "groq",
  "ai_model": "qwen/qwen3.8-27b",
  "ai_api_key": "sua-chave-aqui",
  "system_prompt": "Voce e um assistente de atendimento.",
  "evolution_base_url": "http://evolution:8080",
  "evolution_api_key": "sua-chave-evolution",
  "evolution_instance": "minha-instancia",
  "ai_on": true
}
```

## Configuracao da IA

O sistema suporta multiplos provedores. A resolucao de **chat** e unica para
conversa, workflows/nodes, RAG (resposta final) e o teste de conectividade:

1. Override nao vazio da empresa em `company_configs`
2. Variaveis globais `DEFAULT_AI_*` do `.env` realmente carregado pelo backend
3. Defaults seguros do adapter (provider, modelo e base URL quando nao houver env)

Uma configuracao nova e criada com `ai_provider`, `ai_model`, `ai_api_key` e
`ai_base_url` vazios. Isso e intencional: campos vazios usam o `.env` e nao
criam um valor aleatorio no banco. A resposta de `GET /config/` conserva esses
campos brutos e inclui `resolved_ai_provider`/`resolved_ai_model` apenas para a
interface mostrar o valor efetivo, sem expor a chave.

Na tela `/ai`, salvar prompt ou status nao persiste provider/modelo. Provider e
modelo so viram override quando o operador os altera; **Usar padroes do .env**
limpa os dois overrides ao salvar.

## Configuracao de Embeddings

Knowledge e a busca semantica do RAG nao usam `DEFAULT_AI_*`: usam
`DEFAULT_EMBEDDING_*`, pois o endpoint e `/embeddings` e pode requerer outro
provedor, modelo e chave. Essa configuracao e global por ambiente nesta versao;
nao existe override de embeddings por empresa. Em producao Supabase,
`ENABLE_PGVECTOR=true` habilita a busca vetorial no banco. Trocar modelo ou
dimensao requer reindexar os documentos existentes.
## Configuracao do WhatsApp

A integracao com WhatsApp e feita via **Evolution API**. Configuracao:

1. `EVOLUTION_BASE_URL`: URL da instancia da Evolution
2. `EVOLUTION_API_KEY`: Chave de API da Evolution (em v2.2.x e a senha definida no instal; em 2.4.0+ e o `api_key` da ativacao de licenca)
3. `EVOLUTION_INSTANCE`: Nome da instancia

O webhook deve apontar para: `POST /webhook/whatsapp/{company_id}`

## Credenciais por provedor e administração da plataforma

**Implementado:** a resolução do chat não usa mais a chave do `.env` de um
provedor para autenticar outro. A ordem é: chave própria legada da empresa,
credencial global ativa do **mesmo** provedor, e `DEFAULT_AI_*` somente quando
o provedor selecionado é o provedor padrão do ambiente. Sem chave compatível, o
teste e o workflow retornam uma orientação explícita em vez de uma chamada
ambígua.

O botão **Testar resposta da IA** testa o provedor/modelo atualmente escolhido
na tela, ainda que o usuário não tenha salvo a alteração. O teste não persiste
o override.

**Implementado:** `/plataforma` é uma área separada de `/admin`. Apenas um
operador da plataforma pode cadastrar credenciais globais por provedor. Elas
são criptografadas em repouso e nunca retornam pela API ou pelo frontend.
Papéis `owner`, `admin` e `agent` continuam restritos à sua própria empresa.

**Parcial:** o painel consulta o saldo monetário oficial do DeepSeek quando há
credencial cadastrada. Não existe uma equivalência confiável de saldo para
"tokens restantes"; o rastreamento de tokens efetivamente usados pelo sistema
ainda é planejado.

## Politica de IA por usuario (Planejado)

Apenas o superadmin cadastra chaves, provedores e modelos disponíveis. O
superadmin define quais IAs cada usuario pode utilizar e qual será a IA/modelo
padrao dele. O usuario comum NÃO visualiza nem altera chaves, provedor ou
modelo livremente. O painel do usuario exibe apenas a configuração efetiva
definida pelo administrador e, quando permitido, opções previamente autorizadas.

Regra de prioridade (backend): **politica especifica do usuario** → **politica
da empresa** → **padrao global da plataforma**. Workflows e nodes usam a
politica efetiva do usuario no backend; não confiam em valores enviados pelo
frontend. Todas as chaves permanecem centralizadas e criptografadas no painel
superadmin.
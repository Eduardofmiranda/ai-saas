# 01 — Visao Geral

## O que e o FlowAI

FlowAI e uma plataforma de automacao de atendimento ao cliente via WhatsApp, inspirada no n8n. O usuario cria **workflows** (fluxos de automacao) compostos por **nodes** conectados visualmente, que processam mensagens do WhatsApp usando IA.

## Caso de Uso Principal

1. Empresa cria uma conta no sistema
2. Empresa configura sua chave de IA (Groq, OpenAI, etc.) e conexao com WhatsApp (Evolution API)
3. Empresa cria um workflow de atendimento no editor visual
4. Cliente envia mensagem no WhatsApp
5. Sistema recebe a mensagem via webhook
6. Workflow e executado: IA processa e responde o cliente
7. Fluxo pode pausar aguardando proxima mensagem e retomar automaticamente

## Multi-tenant

Cada empresa tem:
- Sua propria configuracao de IA (provedor, modelo, chave)
- Sua propria configuracao de WhatsApp (Evolution API)
- Seus proprios workflows
- Seus proprios clientes e conversas
- Suas proprias execucoes

## Capacidades Atuais

- Autenticacao JWT (login/cadastro)
- Editor visual de workflows (drag & drop)
- 11 tipos de nodes implementados
- Motor de execucao de workflows
- IA multi-provedor (Groq, OpenAI, DeepSeek, Mistral, Ollama, mock)
- Memoria de conversa (historico do banco)
- Aguardar proxima mensagem (wait_until_message)
- Webhook WhatsApp (Evolution API v2)
- Credenciais criptografadas em repouso
- Deploy via Docker Compose
- Testes automatizados (25 testes)

# 17 — Monitoramento

## Status Atual

**NAO IMPLEMENTADO** — Apenas placeholders no dashboard.

## Dashboard (`GET /dashboard/stats`)

Resposta atual:
```json
{
  "totalConversations": 0,
  "activeConversations": 0,
  "waitingConversations": 0,
  "totalCustomers": 0
}
```

## O que falta implementar

### Metricas
- Total de conversas ativas
- Total de workflows ativos
- Total de execucoes (sucesso/erro)
- Tempo medio de resposta da IA
- Total de clientes atendidos
- Mensagens por hora/dia

### Logs
- Logs de execucao de workflows (implementado em `context["logs"]`)
- Logs estruturados (nao implementado)
- Centralizacao de logs (nao implementado)

### Alertas
- Notificacao de erro em workflow
- Alerta de API key invalida
- Alerta de Evolution API offline
- Alerta de banco de dados indisponivel

### Observabilidade
- Métricas Prometheus (nao implementado)
- Tracing (nao implementado)
- Health checks (nao implementado)

### Health Checks

Nao implementados. Sugestao:
```
GET /health
GET /health/db
GET /health/redis
GET /health/evolution
GET /health/llm
```

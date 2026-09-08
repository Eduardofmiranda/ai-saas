# 17 — Monitoramento

## Estado atual

### Implementado

- `GET /health`: liveness do processo HTTP.
- `GET /health/db`: consulta `SELECT 1` no banco configurado.
- `GET /health/redis`: executa `PING` no Redis configurado.
- `GET /health/evolution`: valida alcance/autenticacao na Evolution, sem
  expor chave ou resposta do servico.
- `GET /health/llm`: valida se provider, modelo, URL e chave globais estao
  coerentemente configurados; nao chama o modelo nem gera custo.
- Falhas de resposta da IA registram provider/modelo/company_id, sem prompt,
  resposta do usuario ou chave de API.
- O dashboard (`GET /dashboard/`) agrega contagens por empresa: clientes,
  conversas (abertas/pendentes/fechadas), mensagens, workflows, execucoes
  (total/sucesso/erro).
- Health checks de dependencias (`/health/*`) respondem `503` com
  `status: unhealthy` quando a dependencia falha. Nao expõem URL, tokens,
  nem a resposta do provedor.

### Parcial

- Logs seguem a saida dos containers (`docker compose logs`); nao ha
  agregador central, alertas ou formato JSON padronizado para todos os eventos.
- O dashboard nao tem serie temporal, tendencia, latencia de IA ou metricas de
  fila Celery.
- Nao ha correlacao de requisicoes entre webhook, execucao, LLM e envio
  WhatsApp (sem correlation ID).

### Planejado

- Metricas Prometheus/OpenTelemetry (latencia de requisicoes, uso de conexao,
  tamanho de filas).
- Alertas para erro recorrente de workflow, Evolution offline e fila parada.
- Correlation ID entre webhook, execucao, LLM e envio WhatsApp.
- Logs estruturados JSON para todos os eventos (necessario para agregacao e
  busca em ferramentas como ELK/Datadog).
- Dashboard com serie temporal de atendimentos, tempo medio de resposta e
  taxa de resolucao.

## Operacao

Na VPS, monitore `docker compose ps`, os cinco endpoints `/health*` e os logs
estruturados do backend/worker. Um `200` em `/health` nao prova que Supabase,
Redis, Evolution ou LLM estejam utilizaveis; use o endpoint especifico.

```bash
# Checar saude completa
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/health/db
curl -fsS http://127.0.0.1:8000/health/redis
curl -fsS http://127.0.0.1:8000/health/evolution
curl -fsS http://127.0.0.1:8000/health/llm

# Ver logs em tempo real
docker compose logs -f backend
docker compose logs -f celery-worker
```

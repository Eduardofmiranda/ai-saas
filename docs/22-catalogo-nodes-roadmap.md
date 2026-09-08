# 22 — Catálogo de Nodes e Roadmap de Integrações

## Status deste documento

**PARCIAL.** O catálogo e as prioridades estão planejados. No P0, a orientação de entrega, o checklist com verificações explícitas de IA/WhatsApp e o modo de teste seguro estão implementados; os demais itens seguem planejados.

O código é a fonte de verdade para o estado de cada node.

## Decisão de produto

Não vamos copiar literalmente todos os conectores de plataformas de automação. Os
catálogos são dinâmicos e extensos: o diretório do n8n lista milhares de
integrações e o Activepieces também opera um catálogo que cresce continuamente.
O produto será melhor se tiver um núcleo seguro, conectores consistentes e uma
lista priorizada por uso real de clientes de WhatsApp, atendimento e vendas.

Referências estudadas:

- [n8n — biblioteca de integrações](https://n8n.io/integrations)
- [n8n — core nodes](https://docs.n8n.io/integrations/builtin/core-nodes/)
- [n8n — nodes de IA](https://docs.n8n.io/integrations/builtin/cluster-nodes/)
- [Zapier — apps e ferramentas](https://help.zapier.com/hc/en-us/categories/8495901804429)
- [Make — controle de fluxo](https://help.make.com/flow-control)
- [Activepieces — catálogo de pieces](https://www.activepieces.com/pieces)

## Estado real atual

### Implementado

- Registro estático de nodes e metadados do editor em
  `app/services/nodes/registry.py`.
- Execução de grafo, erros, pausa/retomada e sub-workflow em
  `app/services/workflow_engine.py`.
- Trigger de mensagem WhatsApp, IA, RAG, definir variável, condição, atraso,
  log, envio por WhatsApp, handoff humano, espera por nova mensagem,
  transferência para setor (`transfer_to_department`), captura de lead
  (`capture_lead`), horário comercial (`check_business_hours`) e
  sub-workflow (`execute_workflow`).
- Configuração criptografada por empresa para IA e Evolution em
  `app/models/company_config.py` e `app/services/field_crypto.py`.
- Validação do grafo antes de ativar ou executar workflows.

### Parcial ou indisponível

- Webhook externo, agendamento (`schedule`), loop, agregação e filtro estão
  registrados, mas não devem ser liberados para novos fluxos enquanto não
  tiverem contrato e segurança completos.
- **Bloqueado por segurança:** `code` (exec em Python sem sandbox) e `http`
  (requisicoes a URLs arbitrarias sem anti-SSRF). O registro e mantido para
  que workflows legados possam ser visualizados; execucao esta desabilitada.
- Não existe ainda um modelo de credenciais genéricas por empresa para OAuth,
  API key, token renovável ou conexão de conectores.
- Não existe SDK/manifesto versionado de conectores, marketplace ou permissões
  específicas por integração.

## Taxonomia alvo

| Grupo | Nodes alvo | Prioridade |
|---|---|---|
| Gatilhos | mensagem, manual, webhook autenticado, agenda, eventos de conectores | P0/P1 |
| Fluxo | condição, switch, filtro, merge, iterator, agregador, espera, retry, erro, sub-workflow | P0/P1 |
| Dados | definir campos, template, JSON, texto, data/hora, validação, deduplicação, storage | P1 |
| Atendimento | enviar WhatsApp, tags, atualizar contato, transferir humano, aprovação, follow-up | P0/P1 |
| IA | resposta, RAG, extrair lead, classificar intenção, resumo, memória, áudio, guardrails | P0/P2 |
| CRM e vendas | Sheets, Calendar/Calendly, HubSpot, Pipedrive, RD Station, Kommo, Zoho | P2 |
| Comunicação | e-mail, Telegram, Slack, Teams, SMS, notificações internas | P2 |
| Conhecimento | Google Drive, Notion, OneDrive, Dropbox, ingestão de arquivos | P2 |
| Marketing e pagamentos | Meta Lead Ads, Brevo, Mailchimp, Stripe, Mercado Pago, Asaas | P3 |
| Operações | Airtable, Notion, Trello, ClickUp, Jira, Monday, PostgreSQL/Supabase | P3 |
| Desenvolvedor | HTTP restrito, GraphQL, webhook de resposta, filas, observabilidade | P2/P3 |

## Requisitos obrigatórios para cada node

Todo node novo precisa ter:

1. schema de configuração validado antes de ativar;
2. inputs, outputs e handles declarados;
3. isolamento por `company_id`;
4. timeout, comportamento de erro e política de retry explícitos;
5. secrets fora do JSON do workflow;
6. logs sem tokens, chaves ou conteúdo sensível desnecessário;
7. status visível: implementado, beta, parcial ou indisponível;
8. testes unitários e de integração; e
9. documentação e template de exemplo quando aplicável.

Nodes de HTTP arbitrário, código, banco de dados ou ferramentas de IA só serão
liberados com política anti-SSRF, permissões, limites e auditoria. Não serão
reativados apenas para igualar o catálogo de outra plataforma.

## Fases de implementação

### P0 — Atendimento confiável e guiado

1. **Implementado:** assistente no editor para completar `Mensagem → IA/RAG → Enviar WhatsApp`.
2. **Implementado:** checklist de estrutura no editor (trigger, prompt, caminho
   de sucesso e campos de envio) e verificacao autenticada e explicita de IA e
   WhatsApp. O teste de IA chama o provedor; a consulta do WhatsApp nao envia
   mensagem.
3. **Implementado:** modo de teste seguro por padrao; simula envio de WhatsApp, espera e handoff.
4. Erros compreensíveis de cota, configuração, envio e webhook.
5. Execução auditável: resposta gerada, destinatário e resultado do envio.

### P1 — Núcleo de automação

1. Switch e filtro completos.
2. Transformação de texto, JSON, data/hora e campos.
3. Storage por empresa, idempotência e deduplicação.
4. Retry com backoff, caminho de erro e interrupção controlada.
5. Espera persistente por tempo/callback e agendamento.
6. Iterator, agregador, merge e sub-workflows com limites.
7. Captura estruturada de lead, tags e atualização de contato.

### P2 — Plataforma de conectores

1. Modelo de `Credential` criptografado, isolado por empresa e nunca retornado
   em texto puro.
2. Conectores com manifesto versionado, actions, triggers, schemas e escopos.
3. OAuth2 com refresh token, API keys e conexão testável.
4. Primeiro lote: Google Sheets, Google Calendar/Calendly, um CRM escolhido por
   demanda, Google Drive/Notion e e-mail/Slack.
5. HTTP Request somente com proteção SSRF, allowlist e permissões de admin.

### P3 — IA e integrações de escala

1. Classificação, extração de lead, resumo, memória e avaliação de qualidade.
2. Transcrição de áudio e ingestão controlada de documentos. **Nota (07/09/2026):**
   mídia WhatsApp NÃO será processada (webhook responde automaticamente, Fase 8.1);
   áudio/documentos só entram aqui se surgir demanda real de outro canal.
3. Integrações de marketing, pagamentos, suporte e operações conforme uso real.
4. Catálogo administrável por empresa, permissões por papel, auditoria e
   marketplace/SDK somente após a plataforma de credenciais estar madura.

## Ordem do próximo lote

As tres primeiras entregas de P0 estao implementadas. **Captura estruturada de
lead (P1) esta implementada**: o node `capture_lead` extrai nome, email,
telefone, empresa, cidade e notas com IA e atualiza o contato automaticamente
(com toggle de sobrescrita). O proximo codigo deve evoluir a auditoria da
execucao (resposta gerada, destinatario e resultado do envio) e o apoio de tags
e atualizacao de contato, antes das credenciais genericas para conectores.

## Critério de aceite por lote

Um lote só passa para produção quando tiver testes automatizados, build do
frontend, validação de isolamento por empresa, execução na VPS e documentação
atualizada com os itens implementados e planejados claramente separados.

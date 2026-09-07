# Segurança — primeira etapa local (07/09/2026)

Este registro descreve o escopo desta etapa. Não equivale a uma certificação
de segurança, nem indica que as alterações foram aplicadas na VPS.

## Implementado

- PATCH /config/ exige privilégio de superadmin quando o corpo inclui
  ai_provider, ai_model, ai_api_key, ai_base_url, evolution_base_url,
  evolution_api_key ou evolution_instance. Owner/admin/agent recebem 403;
  nenhuma alteração solicitada é persistida. JWT de acesso continua obrigatório.
- Campos de personalidade e ativação (system_prompt e ai_on) mantêm o contrato
  anterior. A interface comum já envia apenas esses campos ao salvar.
- Nas rotas de configuração WhatsApp, URL e chave vêm de EVOLUTION_BASE_URL
  e EVOLUTION_API_KEY do ambiente em execução. O teste ignora os overrides
  URL/chave/instância do corpo; a instância vem da empresa ou inst-<company_id>.
- O resolver de IA não combina chave global com URL legada da empresa.
  Credenciais legadas só são elegíveis quando o provedor da empresa coincide
  com o provedor efetivo. A URL acompanha a origem da chave.
- RAG passa user_id do contexto ao resolver, como o node de IA.
- Sem EVOLUTION_AUTH_KEY, o webhook retorna 503 antes de agendar o processamento.
  Cabeçalho incorreto ou ausente com chave configurada retorna 401.
- O Compose exige SECRET_KEY não vazia; o fallback conhecido foi removido.
  Nenhuma chave existente foi rotacionada.

## Parcial e planejado

- A política por usuário ainda exige validação completa, tratamento explícito
  de política vazia/inválida e definição de identidade para workflows legados.
  O teste /config/ai/test ainda aceita overrides de provider/modelo.
- A dependência require_company_manager está disponível, mas a aplicação
  abrangente de papéis a workflows, setores e demais rotas continua pendente.
- O envio por nodes e o pipeline legado ainda precisam ser unificados com a
  configuração segura de Evolution das rotas. Não considerar SSRF totalmente
  resolvido nem remover a revisão de URLs legadas antes de um deploy.
- Revogação de sessões, auditoria, proteção adicional de uploads, limites de
  paginação e validação de segredos fracos continuam pendentes.
- Reset administrativo de senha e bloqueio de contas não estão incluídos.

## Validação e implantação

Os testes desta etapa usam SQLite temporário e serviços simulados: verificam
negação dos campos protegidos para os três papéis de empresa, acesso do
superadmin, separação entre chave global e URL de empresa, configuração
Evolution nas rotas e rejeição do webhook sem autenticação.

Não há migration nova. Produção continua no Supabase. Antes de um futuro
deploy, conferir a configuração efetiva dos containers e compatibilidade dos
endpoints legados, sem imprimir credenciais. Nenhum comando foi executado na VPS.

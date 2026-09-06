/** Regras puras do canvas; o backend continua sendo a autoridade final. */
const PROMPT_SUGGESTIONS = Object.freeze({
  ai: "Responda de forma clara e cordial: {{ data.message.text }}",
  ai_rag: "{{ data.message.text }}",
});

export function suggestedPrompt(nodeType) {
  return PROMPT_SUGGESTIONS[nodeType] || "";
}
/** Reune as saidas por node para verificar caminhos do canvas sem alterar o grafo. */
function outgoingEdges(edges) {
  const outgoing = new Map();
  for (const edge of edges) {
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
    outgoing.get(edge.source).push(edge);
  }
  return outgoing;
}

function reachesNodeType(sourceNode, expectedType, nodes, outgoing, successPathOnly = false) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const firstEdges = outgoing.get(sourceNode.id) || [];
  const allowedFirstEdges = successPathOnly
    ? firstEdges.filter((edge) => !edge.sourceHandle || ["out", "success"].includes(edge.sourceHandle))
    : firstEdges;
  const pending = allowedFirstEdges.map((edge) => edge.target);
  const visited = new Set();

  while (pending.length) {
    const currentId = pending.pop();
    if (visited.has(currentId)) continue;
    visited.add(currentId);
    const current = byId.get(currentId);
    if (current?.type === expectedType) return true;
    pending.push(...(outgoing.get(currentId) || []).map((edge) => edge.target));
  }
  return false;
}

/**
 * Retorna uma orientacao quando a resposta de IA nao tem um node de entrega
 * alcancavel pelo caminho de sucesso. A decisao de salvar ou ativar continua
 * sendo do usuario e do backend; esta funcao apenas evita o erro comum de
 * gerar uma resposta sem envia-la ao WhatsApp.
 */
export function workflowGuidance(nodes, edges) {
  const outgoing = outgoingEdges(edges);
  const responseNode = nodes.find(
    (node) => ["ai", "ai_rag"].includes(node.type)
      && !reachesNodeType(node, "whatsapp_send", nodes, outgoing, true),
  );
  if (!responseNode) return null;

  return {
    sourceNodeId: responseNode.id,
    message: "A resposta da IA ainda nao esta ligada a Enviar WhatsApp. Sem esse node, ela aparece apenas no resultado da execucao.",
  };
}

/**
 * Checklist local do editor. Ele confirma a estrutura do grafo. A conectividade
 * externa e exibida separadamente apos uma acao explicita no editor, usando os
 * endpoints autenticados do backend.
 */
export function activationChecklist(nodes, edges) {
  const outgoing = outgoingEdges(edges);
  const responseNodes = nodes.filter((node) => ["ai", "ai_rag"].includes(node.type));
  const sendNodes = nodes.filter((node) => node.type === "whatsapp_send");
  const messageTriggers = nodes.filter((node) => node.type === "trigger_message");
  const missingPrompts = responseNodes.filter((node) => !String(node.data?.prompt || "").trim());
  const missingDelivery = responseNodes.filter(
    (node) => !reachesNodeType(node, "whatsapp_send", nodes, outgoing, true),
  );
  const incompleteSends = sendNodes.filter(
    (node) => !String(node.data?.phone || "").trim() || !String(node.data?.text || "").trim(),
  );

  return [
    {
      id: "message-trigger",
      label: "Gatilho de mensagem",
      detail: messageTriggers.length === 1
        ? "Um gatilho de mensagem foi encontrado."
        : "Este fluxo precisa de exatamente um gatilho de mensagem.",
      state: messageTriggers.length === 1 ? "ready" : "warning",
    },
    {
      id: "ai-prompt",
      label: "Prompt de IA/RAG",
      detail: responseNodes.length === 0
        ? "Nao se aplica: este fluxo nao usa IA/RAG."
        : missingPrompts.length === 0
          ? "Todos os nodes de IA/RAG possuem prompt."
          : `${missingPrompts.length} node(s) de IA/RAG precisam de prompt.`,
      state: responseNodes.length === 0 ? "not_applicable" : missingPrompts.length === 0 ? "ready" : "warning",
    },
    {
      id: "response-delivery",
      label: "Entrega da resposta",
      detail: responseNodes.length === 0
        ? "Nao se aplica: este fluxo nao gera resposta com IA/RAG."
        : missingDelivery.length === 0
          ? "Toda resposta de IA/RAG alcanca Enviar WhatsApp pelo caminho de sucesso."
          : `${missingDelivery.length} resposta(s) de IA/RAG ainda nao chegam ao WhatsApp.`,
      state: responseNodes.length === 0 ? "not_applicable" : missingDelivery.length === 0 ? "ready" : "warning",
    },
    {
      id: "whatsapp-fields",
      label: "Dados de envio",
      detail: sendNodes.length === 0
        ? "Nao se aplica: nao ha envio de WhatsApp neste fluxo."
        : incompleteSends.length === 0
          ? "Todos os envios possuem telefone e texto."
          : `${incompleteSends.length} envio(s) precisam de telefone e texto.`,
      state: sendNodes.length === 0 ? "not_applicable" : incompleteSends.length === 0 ? "ready" : "warning",
    },
  ];
}

/**
 * Converte as respostas dos endpoints autenticados em itens simples para o
 * editor. A chamada dos endpoints e feita apenas por uma acao explicita do
 * usuario; esta funcao nao inicia requisicoes nem envia mensagens.
 */
export function integrationChecklist(aiResult, whatsappResult) {
  const aiReady = aiResult?.ok === true;
  const whatsappReady = whatsappResult?.state === "open";
  const instance = whatsappResult?.instance ? ` (${whatsappResult.instance})` : "";

  return [
    {
      id: "ai-connection",
      label: "Conexao da IA",
      detail: aiReady
        ? aiResult.detail || "A IA respondeu ao teste de conectividade."
        : aiResult?.detail || "Nao foi possivel testar a configuracao da IA.",
      state: aiReady ? "ready" : "warning",
    },
    {
      id: "whatsapp-connection",
      label: "Conexao do WhatsApp",
      detail: whatsappReady
        ? `WhatsApp conectado${instance}.`
        : whatsappResult?.detail || `WhatsApp esta ${whatsappResult?.state || "indisponivel"}${instance}.`,
      state: whatsappReady ? "ready" : "warning",
    },
  ];
}

export function nodeData(spec, data = {}) {
  return {
    ...data,
    label: spec?.label || data.label || "Node",
    category: spec?.category || data.category || "data",
    description: spec?.description || data.description || "",
    status: spec?.status || data.status || "implemented",
    input_handles: spec?.input_handles || data.input_handles || ["in"],
    output_handles: spec?.output_handles || data.output_handles || ["out", "error"],
  };
}

function makesCycle(source, target, edges) {
  const outgoing = new Map();
  for (const edge of edges) {
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
    outgoing.get(edge.source).push(edge.target);
  }
  const pending = [target];
  const visited = new Set();
  while (pending.length) {
    const current = pending.pop();
    if (current === source) return true;
    if (visited.has(current)) continue;
    visited.add(current);
    pending.push(...(outgoing.get(current) || []));
  }
  return false;
}

export function connectionIssue(params, nodes, edges) {
  const source = nodes.find((node) => node.id === params.source);
  const target = nodes.find((node) => node.id === params.target);
  if (!source || !target) return "Conexao referencia um node inexistente.";
  if (source.id === target.id) return "Um node nao pode se conectar a ele mesmo.";
  if ((target.data?.input_handles || []).length === 0) return "Nodes de trigger nao recebem conexoes.";
  if (!params.sourceHandle || !(source.data?.output_handles || []).includes(params.sourceHandle)) {
    return "Escolha uma saida valida do node de origem.";
  }
  if (edges.some((edge) => edge.source === params.source && edge.target === params.target && edge.sourceHandle === params.sourceHandle)) {
    return "Esta conexao ja existe.";
  }
  if (makesCycle(params.source, params.target, edges)) {
    return "Esta conexao criaria um ciclo. Remova o retorno para um node anterior.";
  }
  return "";
}
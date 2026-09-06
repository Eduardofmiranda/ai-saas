/** Regras puras do canvas; o backend continua sendo a autoridade final. */
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
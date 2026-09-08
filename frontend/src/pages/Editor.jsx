import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "../api";
import Header from "../components/Header";
import { activationChecklist, connectionIssue, integrationChecklist, nodeData, suggestedPrompt, workflowGuidance } from "../workflowGraph";

const ICONS = {
  trigger: "▶",
  ai: "✦",
  logic: "➜",
  data: "=",
  integration: "⇄",
  whatsapp: "✆",
  core: "◆",
  atendimento: "★",
};

const NODE_COLORS = {
  trigger: "#22c55e",
  ai: "#a78bfa",
  logic: "#f59e0b",
  data: "#94a3b8",
  integration: "#22d3ee",
  whatsapp: "#22c55e",
  core: "#6ea8ff",
  atendimento: "#f472b6",
};

const NODE_GUIDANCE = {
  trigger_message: "Use como primeiro node do fluxo. A mensagem e o telefone do cliente ficam disponiveis no contexto, por exemplo em {{ data.message.text }} e {{ data.customer }}.",
  trigger_webhook: "Use apenas em fluxos disparados por webhook configurado. Ele inicia o processamento com os dados recebidos na requisicao.",
  schedule: "Defina a expressao Cron que representa o horario desejado. Confirme que o disparador de agendamento esteja configurado antes de ativar o fluxo.",
  ai: "A resposta gerada fica em {{ data.ai_reply }}. Conecte este node a Enviar WhatsApp e use essa variavel no campo Texto para responder ao cliente.",
  ai_rag: "Busca conteudo na Base de Conhecimento antes de gerar a resposta. A resposta fica em {{ data.ai_reply }} e as fontes usadas ficam no contexto da execucao.",
  whatsapp_send: "Em fluxos de mensagem, mantenha {{ data.phone }} para responder automaticamente a qualquer remetente. Use um numero fixo somente em envio proativo; para a resposta da IA use {{ data.ai_reply }} no campo Texto.",
  condition: "Conecte a saida Sim ao caminho que deve rodar quando a regra for verdadeira e a saida Nao ao caminho alternativo.",
  wait_until_message: "Pausa o fluxo e o retoma na proxima mensagem do mesmo cliente. Conecte-o ao node que deve processar essa nova mensagem.",
  transfer_to_agent: "Entrega a conversa para atendimento humano. A conversa passa para o estado aguardando agente quando houver uma conversa valida no contexto.",
  http: "Este node esta em revisao e nao pode ser adicionado ou executado em novos fluxos por enquanto.",
  set: "Cria ou atualiza um valor no contexto do fluxo. Depois use {{ data.nome_da_variavel }} nos proximos nodes.",
  code: "Este node esta em revisao e nao pode ser adicionado ou executado em novos fluxos por enquanto.",
  delay: "Aguarda pelo numero de segundos informado antes de continuar. Evite tempos longos em fluxos que precisam responder rapidamente.",
  log: "Registra uma mensagem no log da execucao para facilitar diagnosticos. Nao inclua senhas, tokens ou dados sensiveis.",
  execute_workflow: "Executa outro workflow da mesma empresa. Use-o para reaproveitar uma automacao que ja foi testada.",
  capture_lead: "Analisa a conversa com IA e salva os dados do cliente (nome, email, telefone, empresa, cidade e notas) no lead. Coloque-o depois da troca de mensagens que deseja analisar. Os dados ficam em {{ data.lead }}.",
};

function NodeShell({ data, selected }) {
  const cat = data.category || "data";
  const inputHandles = data.input_handles || ["in"];
  const outputHandles = data.output_handles || ["out", "error"];
  return (
    <div className={`rf-node cat-${cat} ${selected ? "selected" : ""}`}>
      {inputHandles.map((handle) => <Handle key={handle} type="target" position={Position.Top} id={handle} />)}
      <div className="rf-node-title"><span className="rf-icon">{ICONS[cat] || "•"}</span>{data.label}</div>
      {data.description && <p className="rf-node-description">{data.description}</p>}
      {data.status === "partial" && <span className="rf-node-status">em revisao</span>}
      <div className="rf-node-ports"><span>entrada</span><span>saida</span></div>
      {outputHandles.includes("out") && <Handle type="source" position={Position.Bottom} id="out" />}
      {outputHandles.includes("error") && <Handle type="source" position={Position.Right} id="error" style={{ background: "#dc2626" }} />}
    </div>
  );
}

function ConditionNode({ data, selected }) {
  const inputHandles = data.input_handles || ["in"];
  const outputHandles = data.output_handles || ["true", "false", "error"];
  return (
    <div className={`rf-node cat-logic condition ${selected ? "selected" : ""}`}>
      {inputHandles.map((handle) => <Handle key={handle} type="target" position={Position.Top} id={handle} />)}
      <div className="rf-node-title"><span className="rf-icon">➜</span>{data.label}</div>
      {data.description && <p className="rf-node-description">{data.description}</p>}
      <div className="condition-handles">
        {outputHandles.includes("true") && <Handle type="source" position={Position.Bottom} id="true" style={{ left: "30%", background: "#16a34a" }} />}
        {outputHandles.includes("false") && <Handle type="source" position={Position.Bottom} id="false" style={{ left: "70%", background: "#dc2626" }} />}
        {outputHandles.includes("error") && <Handle type="source" position={Position.Right} id="error" style={{ background: "#dc2626" }} />}
      </div>
      <div className="rf-node-tags"><span className="tag green">sim</span><span className="tag red">nao</span></div>
    </div>
  );
}

function TriggerNode({ data, selected }) {
  const outputHandles = data.output_handles || ["out"];
  return (
    <div className={`rf-node cat-trigger trigger ${selected ? "selected" : ""}`}>
      <div className="rf-node-title"><span className="rf-icon">▶</span>{data.label}</div>
      {data.description && <p className="rf-node-description">{data.description}</p>}
      <div className="rf-node-ports trigger-port"><span>inicio do fluxo</span><span>saida</span></div>
      {outputHandles.includes("out") && <Handle type="source" position={Position.Bottom} id="out" />}
    </div>
  );
}

function FieldHelp({ children }) {
  return (
    <small className="field-help">
      <span className="field-help-icon" aria-hidden="true">i</span>
      {children}
    </small>
  );
}

function StickyNote({ data, selected }) {
  return (
    <div className={`rf-node sticky-note ${selected ? "selected" : ""}`}>
      <div className="sticky-header">📝 Nota</div>
      <div className="sticky-content">{data.text || "Clique para editar..."}</div>
    </div>
  );
}

const nodeTypes = {
  trigger_message: TriggerNode,
  trigger_webhook: TriggerNode,
  schedule: TriggerNode,
  condition: ConditionNode,
  ai: NodeShell,
  ai_rag: NodeShell,
  set: NodeShell,
  code: NodeShell,
  loop: NodeShell,
  aggregate: NodeShell,
  delay: NodeShell,
  http: NodeShell,
  whatsapp_send: NodeShell,
  filter: NodeShell,
  log: NodeShell,
  execute_workflow: NodeShell,
  transfer_to_agent: NodeShell,
  transfer_to_department: NodeShell,
  capture_lead: NodeShell,
  wait_until_message: NodeShell,
  sticky_note: StickyNote,
};

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const wrapper = useRef(null);

  const [nodeTypesList, setNodeTypesList] = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [wf, setWf] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [editorError, setEditorError] = useState("");
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [showActivationChecklist, setShowActivationChecklist] = useState(false);
  const [integrationChecks, setIntegrationChecks] = useState(null);
  const [checkingIntegrations, setCheckingIntegrations] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getNodeTypes()
      .then((r) => r.node_types || [])
      .catch(() => [])
      .then((types) => {
        setNodeTypesList(types);
        return api.getWorkflow(id).then((w) => ({ types, w }));
      })
      .then(({ types, w }) => {
        if (cancelled) return;
        const byType = new Map(types.map((t) => [t.type, t]));
        const rawNodes = w.data?.nodes || [];
        const nodeTypeById = new Map(rawNodes.map((n) => [n.id, n.type]));
        setWf(w);
        setNodes(rawNodes.map((n) =>
          n.type === "sticky_note"
            ? { ...n, position: Array.isArray(n.position) ? { x: n.position[0], y: n.position[1] } : n.position }
            : {
              ...n,
              position: Array.isArray(n.position) ? { x: n.position[0], y: n.position[1] } : n.position,
              data: nodeData(byType.get(n.type), n.data),
            }
        ));
        setEdges((w.data?.edges || []).map((e) => ({
          ...e,
          sourceHandle: e.sourceHandle === "success" && nodeTypeById.get(e.source) !== "condition"
            ? "out"
            : e.sourceHandle,
          markerEnd: { type: MarkerType.ArrowClosed },
        })));
      })
      .catch((e) => { if (!cancelled) alert("Erro ao carregar fluxo: " + e.message); });
    return () => { cancelled = true; };
  }, [id]);

  const onConnect = useCallback((params) => {
    const issue = connectionIssue(params, nodes, edges);
    if (issue) {
      setEditorError(issue);
      return;
    }
    setEditorError("");
    setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds));
  }, [nodes, edges, setEdges]);

  const onNodeClick = (_, node) => {
    if (node.type === "sticky_note") {
      setSelectedNode({ ...node, spec: { type: "sticky_note", fields: [
        { key: "text", label: "Texto da nota", type: "textarea" },
        { key: "color", label: "Cor", type: "select", options: ["#fef3c7", "#dbeafe", "#dcfce7", "#fce7f3", "#f3e8ff"] },
      ]}});
      return;
    }
    const spec = nodeTypesList.find((s) => s.type === node.type);
    setSelectedNode({ ...node, spec });
  };

  function buildNodeData(spec) {
    const data = nodeData(spec);
    for (const f of spec.fields || []) {
      data[f.key] = f.default ?? "";
    }
    return data;
  }

  function addNode(spec) {
    if (spec.editor_available === false) return;
    const nodeId = `${spec.type}_${Date.now()}`;
    const newNode = {
      id: nodeId,
      type: spec.type,
      position: { x: 80 + Math.random() * 120, y: 80 + Math.random() * 120 },
      data: buildNodeData(spec),
    };
    setNodes((ns) => [...ns, newNode]);
  }

  function addStickyNote() {
    const nodeId = `sticky_${Date.now()}`;
    const colors = ["#fef3c7", "#dbeafe", "#dcfce7", "#fce7f3", "#f3e8ff"];
    const newNode = {
      id: nodeId,
      type: "sticky_note",
      position: { x: 100 + Math.random() * 100, y: 100 + Math.random() * 100 },
      data: { text: "Nova nota...", color: colors[Math.floor(Math.random() * colors.length)] },
    };
    setNodes((ns) => [...ns, newNode]);
  }

  function addSuggestedWhatsAppResponse() {
    if (!responseGuidance) return;
    const spec = nodeTypesList.find((nodeType) => nodeType.type === "whatsapp_send");
    const sourceNode = nodes.find((node) => node.id === responseGuidance.sourceNodeId);
    if (!spec || !sourceNode) {
      setEditorError("Nao foi possivel preparar o envio de resposta. Atualize a pagina e tente novamente.");
      return;
    }

    const nodeId = `whatsapp_send_${Date.now()}`;
    const newNode = {
      id: nodeId,
      type: "whatsapp_send",
      position: { x: sourceNode.position.x + 270, y: sourceNode.position.y },
      data: buildNodeData(spec),
    };
    const newEdge = {
      id: `${sourceNode.id}-${nodeId}`,
      source: sourceNode.id,
      sourceHandle: "out",
      target: nodeId,
      targetHandle: "in",
      markerEnd: { type: MarkerType.ArrowClosed },
    };
    setNodes((currentNodes) => [...currentNodes, newNode]);
    setEdges((currentEdges) => [...currentEdges, newEdge]);
    setSelectedNode({ ...newNode, spec });
    setEditorError("");
  }
  function updateSelectedConfig(key, value) {
    if (!selectedNode) return;
    const updated = {
      ...selectedNode,
      data: { ...selectedNode.data, [key]: value },
    };
    setSelectedNode(updated);
    setNodes((ns) => ns.map((n) => (n.id === selectedNode.id ? updated : n)));
  }

  function deleteSelectedNode() {
    if (!selectedNode) return;
    if (!confirm("Excluir este node?")) return;
    const nodeId = selectedNode.id;
    setNodes((ns) => ns.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
  }

  const deleteNodeById = useCallback((nodeId) => {
    setNodes((ns) => ns.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode((sel) => (sel && sel.id === nodeId ? null : sel));
  }, [setNodes, setEdges]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Delete" && selectedNode) {
        deleteNodeById(selectedNode.id);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedNode, deleteNodeById]);

  async function save(activate) {
    setSaving(true);
    setEditorError("");
    try {
      const body = { data: { nodes, edges } };
      if (wf?.name) body.name = wf.name;
      if (activate !== undefined) body.active = activate;
      const saved = await api.updateWorkflow(id, body);
      setWf(saved);
      return true;
    } catch (e) {
      setEditorError(e.message || "Nao foi possivel salvar este fluxo.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function run() {
    if (running) return;
    setRunning(true);
    setRunResult(null);
    // O teste salva o canvas, mas simula envios, espera e handoff.
    const saved = await save();
    if (!saved) { setRunning(false); return; }
    try {
      const payload = {
        message: { text: "Ola! Preciso de ajuda com os planos." },
        customer: "5511999999999",
        phone: "5511999999999",
      };
      const ex = await api.runWorkflow(id, payload, true);
      setRunResult(ex);
    } catch (e) {
      alert("Erro ao executar: " + e.message);
    } finally {
      setRunning(false);
    }
  }

  async function checkIntegrations() {
    if (checkingIntegrations) return;
    setCheckingIntegrations(true);
    const unavailable = (error, fallback) => ({
      ok: false,
      state: "unavailable",
      detail: error?.message || fallback,
    });
    try {
      const [aiResult, whatsappResult] = await Promise.all([
        api.testAI().catch((error) => unavailable(error, "Nao foi possivel testar a configuracao da IA.")),
        api.getWhatsAppStatus().catch((error) => unavailable(error, "Nao foi possivel consultar o WhatsApp.")),
      ]);
      setIntegrationChecks(integrationChecklist(aiResult, whatsappResult));
    } finally {
      setCheckingIntegrations(false);
    }
  }

  const fields = selectedNode?.spec?.fields || [];
  const responseGuidance = wf?.trigger_type === "message"
    ? workflowGuidance(nodes, edges)
    : null;
  const activationChecks = activationChecklist(nodes, edges, wf?.trigger_type);
  const activationWarnings = activationChecks.filter((item) => item.state === "warning").length;

  const filteredNodes = nodeTypesList.filter((nt) =>
    !searchTerm || nt.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
    nt.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="editor-layout">
      <Header>
        <div className="ed-title">
          <input
            className="ed-name"
            value={wf?.name || ""}
            placeholder="Nome do fluxo"
            onChange={(e) => setWf((prev) => (prev ? { ...prev, name: e.target.value } : prev))}
            onBlur={() => { if (wf?.name) save(); }}
          />
          <span className={`badge ${wf?.active ? "on" : "off"}`}>{wf?.active ? "Ativo" : "Inativo"}</span>
        </div>
        <div className="ed-actions">
          <button className="btn ghost" onClick={() => navigate("/fluxos")}>Voltar</button>
          <button className={wf?.active ? "btn ghost" : "btn secondary"} onClick={() => save(!wf?.active)} disabled={saving || running}>
            {wf?.active ? "Desativar" : "Ativar"}
          </button>
          <button className="btn secondary" onClick={() => run()} disabled={saving || running}>
            {running ? "Testando..." : "Rodar teste"}
          </button>
          <button className="btn primary" onClick={() => save()} disabled={saving || running}>
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </Header>

      <div className="editor-body" ref={wrapper}>
        <aside className="palette">
          <h4>Nodes</h4>
          <input
            type="text"
            className="palette-search"
            placeholder="Buscar node..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div className="palette-list">
            {filteredNodes.map((nt) => (
              <div key={nt.type} className={`palette-item ${nt.editor_available === false ? "unavailable" : ""}`}
                   draggable={nt.editor_available !== false}
                   title={nt.editor_available === false ? "Node em revisao: nao pode ser usado em novos fluxos." : nt.description}
                   onDragStart={(e) => {
                     if (nt.editor_available === false) { e.preventDefault(); return; }
                     e.dataTransfer.setData("application/flow-node", JSON.stringify(nt));
                   }}
                   onClick={() => addNode(nt)}>
                <span className="rf-icon">{ICONS[nt.category] || "•"}</span>
                <div>
                  <strong>{nt.label}</strong>
                  <p>{nt.description}</p>
                  {nt.editor_available === false && <small>Em revisao</small>}
                </div>
              </div>
            ))}
          </div>
          <div className="palette-extras">
            <button className="btn secondary small" onClick={addStickyNote}>+ Nota</button>
          </div>
        </aside>

        <div className="canvas"
          onDrop={(e) => {
            e.preventDefault();
            const raw = e.dataTransfer.getData("application/flow-node");
            if (!raw) return;
            const spec = JSON.parse(raw);
            const rect = e.currentTarget.getBoundingClientRect();
            const position = reactFlowInstance
              ? reactFlowInstance.screenToFlowPosition({ x: e.clientX, y: e.clientY })
              : { x: e.clientX - rect.left - 60, y: e.clientY - rect.top - 20 };
            const nodeId = `${spec.type}_${Date.now()}`;
            setNodes((ns) => [...ns, {
              id: nodeId,
              type: spec.type,
              position,
              data: buildNodeData(spec),
            }]);
          }}
          onDragOver={(e) => e.preventDefault()}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedNode(null)}
            nodeTypes={nodeTypes}
            onInit={setReactFlowInstance}
            fitView
            fitViewOptions={{ padding: 0.2 }}
          >
            <Background />
            <Controls position="bottom-left" showInteractive={false} />
            <MiniMap
              position="bottom-right"
              pannable
              zoomable
              nodeColor={(node) => NODE_COLORS[node.data?.category] || NODE_COLORS.data}
              nodeStrokeColor="#0f1115"
              nodeBorderRadius={4}
              bgColor="#171a21"
              maskColor="rgba(10, 12, 16, 0.72)"
              ariaLabel="Mapa de navegacao do fluxo"
            />
            {editorError && (
              <Panel position="top-center" className="editor-validation" role="alert">
                <span>{editorError}</span>
                <button type="button" onClick={() => setEditorError("")} aria-label="Fechar aviso">×</button>
              </Panel>
            )}
            {(responseGuidance || showActivationChecklist) && (
              <Panel position="top-left" className="workflow-guidance workflow-assistant" role="status">
                {responseGuidance && (
                  <div className="workflow-guidance-section">
                    <strong>Resposta ainda nao e enviada</strong>
                    <span>{responseGuidance.message}</span>
                    <button type="button" className="btn secondary small" onClick={addSuggestedWhatsAppResponse}>
                      Adicionar envio de resposta
                    </button>
                  </div>
                )}
                {showActivationChecklist && (
                  <div className="activation-checklist">
                    <strong>Checklist de ativacao</strong>
                    <span>Confere a estrutura do canvas e permite testar, sob demanda, a conexao com IA e WhatsApp.</span>
                    <ul>
                      {activationChecks.map((item) => (
                        <li key={item.id} className={`check-${item.state}`}>
                          <b>{item.state === "ready" ? "✓" : item.state === "warning" ? "!" : "—"}</b>
                          <span><strong>{item.label}</strong>{item.detail}</span>
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      className="btn secondary small"
                      onClick={checkIntegrations}
                      disabled={checkingIntegrations}
                    >
                      {checkingIntegrations ? "Verificando conexoes..." : "Verificar IA e WhatsApp"}
                    </button>
                    <small className="integration-check-note">A IA recebe um PONG de teste; o WhatsApp nao recebe mensagem.</small>
                    {integrationChecks && (
                      <ul className="integration-checks">
                        {integrationChecks.map((item) => (
                          <li key={item.id} className={`check-${item.state}`}>
                            <b>{item.state === "ready" ? "✓" : "!"}</b>
                            <span><strong>{item.label}</strong>{item.detail}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </Panel>
            )}
            <Panel position="top-right" className="canvas-tools">
              <button
                className={`canvas-fit-button ${activationWarnings ? "has-warnings" : ""}`}
                type="button"
                onClick={() => setShowActivationChecklist((visible) => !visible)}
                title="Conferir a estrutura antes de ativar"
              >
                {showActivationChecklist ? "Fechar checklist" : activationWarnings ? `Checklist (${activationWarnings})` : "Checklist pronto"}
              </button>
              <button
                className="canvas-fit-button"
                type="button"
                onClick={() => reactFlowInstance?.fitView({ padding: 0.2, duration: 250 })}
                title="Centralizar todos os nodes"
              >
                Centralizar fluxo
              </button>
            </Panel>
          </ReactFlow>
        </div>

        <aside className="inspector">
          {!selectedNode ? (
            <div className="empty-panel">
              <h4>Configuracao</h4>
              <p>Clique em um node para configurar suas propriedades.</p>
            </div>
          ) : (
            <>
              <div className="inspector-head">
                <h4>{selectedNode.type === "sticky_note" ? "Nota" : selectedNode.data.label}</h4>
                <button className="btn ghost small danger" onClick={deleteSelectedNode}>Excluir</button>
              </div>
              {selectedNode.spec && (
                <div className="node-explainer">
                  <strong>Como funciona</strong>
                  <p>{selectedNode.spec.description}</p>
                  {NODE_GUIDANCE[selectedNode.type] && <p className="node-tip">{NODE_GUIDANCE[selectedNode.type]}</p>}
                </div>
              )}
              {fields.length === 0 ? (
                <p>Este node nao possui propriedades.</p>
              ) : (
                fields.map((f) => (
                  <label
                    key={f.key}
                    className={`field ${selectedNode.type === "whatsapp_send" && ["phone", "text"].includes(f.key) ? "whatsapp-send-field" : ""}`}
                  >
                    <span>
                      {f.label}
                      {f.required && <small className="field-required">Obrigatorio</small>}
                    </span>
                    {f.type === "textarea" ? (
                      <textarea
                        value={selectedNode.data?.[f.key] ?? ""}
                        onChange={(e) => updateSelectedConfig(f.key, e.target.value)}
                        placeholder={f.placeholder || ""}
                      />
                    ) : f.type === "toggle" ? (
                      <label className="toggle">
                        <input
                          type="checkbox"
                          checked={selectedNode.data?.[f.key] !== "off"}
                          onChange={(e) => updateSelectedConfig(f.key, e.target.checked ? "on" : "off")}
                        />
                        <span>Ligado</span>
                        {f.help && <FieldHelp>{f.help}</FieldHelp>}
                      </label>
                    ) : f.type === "select" ? (
                      <select
                        value={selectedNode.data?.[f.key] ?? ""}
                        onChange={(e) => updateSelectedConfig(f.key, e.target.value)}>
                        <option value="">-</option>
                        {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <>
                        <input
                          value={selectedNode.data?.[f.key] ?? ""}
                          onChange={(e) => updateSelectedConfig(f.key, e.target.value)}
                          placeholder={f.placeholder || ""}
                          type={f.type === "number" ? "number" : "text"}
                        />
                        {f.help && <FieldHelp>{f.help}</FieldHelp>}
                      </>
                    )}
                    {selectedNode.type === "whatsapp_send" && f.key === "phone" && selectedNode.data?.phone !== "{{ data.phone }}" && (
                      <button
                        className="btn ghost small field-suggestion"
                        type="button"
                        onClick={() => updateSelectedConfig("phone", "{{ data.phone }}")}
                      >
                        Responder ao remetente automaticamente
                      </button>
                    )}
                    {selectedNode.type === "whatsapp_send" && f.key === "text" && selectedNode.data?.text !== "{{ data.ai_reply }}" && (
                      <button
                        className="btn ghost small field-suggestion"
                        type="button"
                        onClick={() => updateSelectedConfig("text", "{{ data.ai_reply }}")}
                      >
                        Usar resposta da IA
                      </button>
                    )}
                    {f.key === "prompt" && !String(selectedNode.data?.prompt || "").trim() && suggestedPrompt(selectedNode.type) && (
                      <button
                        className="btn ghost small field-suggestion"
                        type="button"
                        onClick={() => updateSelectedConfig("prompt", suggestedPrompt(selectedNode.type))}
                      >
                        Usar mensagem recebida
                      </button>
                    )}
                  </label>
                ))
              )}
            </>
          )}

          {runResult && (
            <div className="run-result">
              <h4>{runResult.context?.dry_run ? "Resultado do teste" : "Resultado da execucao"}</h4>
              {runResult.context?.dry_run && (
                <p className="test-run-note">Teste seguro: nenhum WhatsApp foi enviado, nenhuma espera ou transferencia foi persistida.</p>
              )}
              <div className={`badge ${runResult.status === "success" ? "on" : "off"}`}>
                Status: {runResult.status}
              </div>
              {runResult.error && <div className="error">{runResult.error}</div>}

              {runResult.context?.logs?.length > 0 && (
                <div className="run-logs">
                  <h5>Log da execucao</h5>
                  {runResult.context.logs.map((line, i) => (
                    <div key={i} className="log-line">{line}</div>
                  ))}
                </div>
              )}

              <h5>Saidas</h5>
              <pre>{JSON.stringify(runResult.node_results, null, 2)}</pre>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

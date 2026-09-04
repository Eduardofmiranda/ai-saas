import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
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

const ICONS = {
  trigger: "▶",
  ai: "✦",
  logic: "➜",
  data: "=",
  integration: "⇄",
  whatsapp: "✆",
  core: "◆",
};

function NodeShell({ data, selected }) {
  const cat = data.category || "data";
  return (
    <div className={`rf-node cat-${cat} ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <div className="rf-node-title"><span className="rf-icon">{ICONS[cat] || "•"}</span>{data.label}</div>
      <Handle type="source" position={Position.Bottom} id="out" />
    </div>
  );
}

function ConditionNode({ data, selected }) {
  return (
    <div className={`rf-node cat-logic condition ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <div className="rf-node-title"><span className="rf-icon">➜</span>{data.label}</div>
      <div className="condition-handles">
        <Handle type="source" position={Position.Bottom} id="true" style={{ left: "30%", background: "#16a34a" }} />
        <Handle type="source" position={Position.Bottom} id="false" style={{ left: "70%", background: "#dc2626" }} />
      </div>
      <div className="rf-node-tags"><span className="tag green">sim</span><span className="tag red">nao</span></div>
    </div>
  );
}

function TriggerNode({ data, selected }) {
  return (
    <div className={`rf-node cat-trigger trigger ${selected ? "selected" : ""}`}>
      <div className="rf-node-title"><span className="rf-icon">▶</span>{data.label}</div>
      <Handle type="source" position={Position.Bottom} id="out" />
    </div>
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
        setWf(w);
        setNodes((w.data?.nodes || []).map((n) =>
          n.type === "sticky_note"
            ? n
            : { ...n, data: { ...n.data, label: byType.get(n.type)?.label || n.type } }
        ));
        setEdges((w.data?.edges || []).map((e) => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed } })));
      })
      .catch((e) => { if (!cancelled) alert("Erro ao carregar fluxo: " + e.message); });
    return () => { cancelled = true; };
  }, [id]);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds));
  }, [setEdges]);

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
    const data = { label: spec.label, category: spec.category };
    for (const f of spec.fields || []) {
      data[f.key] = f.default ?? "";
    }
    return data;
  }

  function addNode(spec) {
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
    try {
      const body = { data: { nodes, edges } };
      if (activate !== undefined) body.active = activate;
      const saved = await api.updateWorkflow(id, body);
      setWf(saved);
      setSaving(false);
      return true;
    } catch (e) {
      setSaving(false);
      alert("Erro ao salvar: " + e.message);
      return false;
    }
  }

  async function run() {
    if (running) return;
    setRunning(true);
    setRunResult(null);
    const saved = await save(false);
    if (!saved) { setRunning(false); return; }
    try {
      const payload = {
        message: { text: "Ola! Preciso de ajuda com os planos." },
        customer: "5511999999999",
        phone: "5511999999999",
      };
      const ex = await api.runWorkflow(id, payload);
      setRunResult(ex);
    } catch (e) {
      alert("Erro ao executar: " + e.message);
    } finally {
      setRunning(false);
    }
  }

  const fields = selectedNode?.spec?.fields || [];

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
          <button className="btn secondary" onClick={() => run()} disabled={saving || running}>
            {running ? "Rodando..." : "Rodar"}
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
              <div key={nt.type} className="palette-item" draggable
                   onDragStart={(e) => e.dataTransfer.setData("application/flow-node", JSON.stringify(nt))}
                   onClick={() => addNode(nt)}>
                <span className="rf-icon">{ICONS[nt.category] || "•"}</span>
                <div>
                  <strong>{nt.label}</strong>
                  <p>{nt.description}</p>
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
            const position = { x: e.clientX - rect.left - 60, y: e.clientY - rect.top - 20 };
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
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
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
              {fields.length === 0 ? (
                <p>Este node nao possui propriedades.</p>
              ) : (
                fields.map((f) => (
                  <label key={f.key} className="field">
                    <span>{f.label}</span>
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
                        {f.help && <small className="field-help">{f.help}</small>}
                      </label>
                    ) : f.type === "select" ? (
                      <select
                        value={selectedNode.data?.[f.key] ?? ""}
                        onChange={(e) => updateSelectedConfig(f.key, e.target.value)}>
                        <option value="">-</option>
                        {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input
                        value={selectedNode.data?.[f.key] ?? ""}
                        onChange={(e) => updateSelectedConfig(f.key, e.target.value)}
                        placeholder={f.placeholder || ""}
                        type={f.type === "number" ? "number" : "text"}
                      />
                    )}
                  </label>
                ))
              )}
            </>
          )}

          {runResult && (
            <div className="run-result">
              <h4>Resultado da execucao</h4>
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

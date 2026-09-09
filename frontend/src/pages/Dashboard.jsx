import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Header from "../components/Header";
import { PageHeader, Alert, Icon, EmptyState, Skeleton } from "../components/ui";

const STATE_LABELS = {
  not_configured: "Não configurado",
  needs_config: "Falta chave/instância",
  open: "Conectado",
  close: "Desconectado",
  connecting: "Conectando",
  unknown: "Desconhecido",
  error: "Erro",
  unreachable: "Sem conexão com a Evolution",
  instance_not_found: "Instância não encontrada",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [wa, setWa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getDashboard(), api.getWhatsAppStatus()])
      .then(([d, w]) => {
        setData(d);
        setWa(w);
        setError("");
      })
      .catch((e) => setError(e.message || "Erro ao carregar painel"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="layout">
        <Header />
        <main className="content"><Skeleton variant="cards" /></main>
      </div>
    );
  }

  const waState = wa?.state || "not_configured";
  const waOpen = waState === "open";
  const isEmpty = (data?.workflows_total || 0) === 0;

  const cards = [
    ["Fluxos", data?.workflows_total || 0, "workflows", `/fluxos`, "workflow", ""],
    ["Fluxos ativos", data?.workflows_active || 0, "ativos", null, "play", "kpi-green"],
    ["Conversas", data?.conversations || 0,
      (data?.pending_conversations || 0) > 0 ? `${data.pending_conversations} aguardando` : "abertas",
      `/conversas`, "message-circle", "kpi-amber"],
    ["Clientes", data?.customers || 0, "cadastrados", null, "user", ""],
    ["Mensagens", data?.messages || 0, "trocadas", null, "mail", "kpi-green"],
    ["Execuções", data?.executions_total || 0, "totais", null, "refresh-cw", ""],
  ];

  const execOk = data?.executions_success || 0;
  const execErr = data?.executions_error || 0;

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader title="Painel" subtitle="Visão geral do seu atendimento com IA.">
          <button className="btn primary" onClick={() => navigate("/fluxos")}>+ Novo fluxo</button>
        </PageHeader>

        {error && <Alert variant="error" onDismiss={() => setError("")}>{error}</Alert>}

        {/* Status WhatsApp */}
        <div className="wa-banner">
          <div className={`state-pill ${waState}`}>
            WhatsApp: {STATE_LABELS[waState] || waState}
            {waOpen && <span className="state-dot" />}
          </div>
          <span className="muted">
            {waOpen
              ? "Atendimento conectado e recebendo mensagens."
              : "Conecte seu WhatsApp para atender automaticamente com IA."}
          </span>
          <button className="btn secondary small" onClick={() => navigate("/whatsapp")}>
            {waOpen ? "Gerenciar" : "Conectar"}
          </button>
        </div>

        {(data?.pending_conversations || 0) > 0 && (
          <div className="notice" style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ flex: 1 }}>
              <strong>{data.pending_conversations} conversa(s)</strong> aguardando atendimento humano.
              Assuma no inbox para responder manualmente.
            </span>
            <button className="btn secondary small" onClick={() => navigate("/conversas")}>
              Ver conversas
            </button>
          </div>
        )}

        {isEmpty ? (
          <EmptyState
            icon={<Icon name="workflow" size={40} />}
            title="Comece criando seu primeiro fluxo"
            action={
              <div className="btn-group">
                <button className="btn primary" onClick={() => navigate("/fluxos")}>Criar fluxo</button>
                <button className="btn ghost" onClick={() => navigate("/whatsapp")}>Conectar WhatsApp</button>
              </div>
            }
          >
            Um fluxo conecta o WhatsApp ao seu atendente de IA: a mensagem chega, a IA responde
            e você acompanha tudo aqui.
          </EmptyState>
        ) : (
          <div className="kpi-grid">
            {cards.map(([label, value, sub, to, icon, tone]) =>
              to ? (
                <button
                  key={label}
                  type="button"
                  className={`kpi-card ${tone || ""}`}
                  onClick={() => navigate(to)}
                >
                  <span className="kpi-icon"><Icon name={icon} size={21} /></span>
                  <div className="kpi-body">
                    <div className="kpi-value">{value}</div>
                    <div className="kpi-label">{label}</div>
                    <div className="kpi-sub">{sub}</div>
                  </div>
                </button>
              ) : (
                <div key={label} className={`kpi-card ${tone || ""}`}>
                  <span className="kpi-icon"><Icon name={icon} size={21} /></span>
                  <div className="kpi-body">
                    <div className="kpi-value">{value}</div>
                    <div className="kpi-label">{label}</div>
                    <div className="kpi-sub">{sub}</div>
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {!isEmpty && (data?.executions_total || 0) > 0 && (
          <div className="detail-panel">
            <h3>Execuções</h3>
            <div className="exec-bar">
              <div className="exec-seg ok" style={{ flex: execOk }} title={`Sucesso: ${execOk}`} />
              <div className="exec-seg err" style={{ flex: execErr }} title={`Erro: ${execErr}`} />
            </div>
            <p className="muted">
              {execOk} com sucesso · {execErr} com erro · {data.executions_total} no total
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

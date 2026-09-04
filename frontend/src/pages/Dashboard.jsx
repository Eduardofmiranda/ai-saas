import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Header from "../components/Header";

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
        <main className="content"><p className="muted">Carregando painel...</p></main>
      </div>
    );
  }

  const waState = wa?.state || "not_configured";
  const waOpen = waState === "open";
  const isEmpty = (data?.workflows_total || 0) === 0;

  const cards = [
    ["Fluxos", data?.workflows_total || 0, "workflows", `/fluxos`],
    ["Fluxos ativos", data?.workflows_active || 0, "ativos", null],
    ["Conversas", data?.conversations || 0, "abertas", `/conversas`],
    ["Clientes", data?.customers || 0, "cadastrados", null],
    ["Mensagens", data?.messages || 0, "trocadas", null],
    ["Execuções", data?.executions_total || 0, "totais", null],
  ];

  const execOk = data?.executions_success || 0;
  const execErr = data?.executions_error || 0;

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <div>
            <h2>Painel</h2>
            <p className="muted">Visão geral do seu atendimento com IA.</p>
          </div>
          <button className="btn primary" onClick={() => navigate("/fluxos")}>+ Novo fluxo</button>
        </div>

        {error && <div className="error">{error}</div>}

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

        {isEmpty ? (
          <div className="empty dash-empty">
            <h3>Comece criando seu primeiro fluxo</h3>
            <p>
              Um fluxo conecta o WhatsApp ao seu atendente de IA: a mensagem chega, a IA responde
              e você acompanha tudo aqui.
            </p>
            <div className="btn-group" style={{ marginTop: 12 }}>
              <button className="btn primary" onClick={() => navigate("/fluxos")}>Criar fluxo</button>
              <button className="btn ghost" onClick={() => navigate("/whatsapp")}>Conectar WhatsApp</button>
            </div>
          </div>
        ) : (
          <div className="kpi-grid">
            {cards.map(([label, value, sub, to]) => (
              <div
                key={label}
                className="kpi-card"
                onClick={to ? () => navigate(to) : undefined}
                style={to ? { cursor: "pointer" } : undefined}
              >
                <div className="kpi-value">{value}</div>
                <div className="kpi-label">{label}</div>
                <div className="kpi-sub">{sub}</div>
              </div>
            ))}
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

import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

const STATE_LABELS = {
  not_configured: "Não configurado",
  open: "Conectado",
  close: "Desconectado",
  connecting: "Conectando",
  unknown: "Desconhecido",
  error: "Erro",
  unreachable: "Sem conexão com a Evolution",
  instance_not_found: "Instância não encontrada",
};

export default function WhatsApp() {
  const { user, logout } = useAuth();
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState({ evolution_base_url: "", evolution_api_key: "", evolution_instance: "" });

  async function load() {
    try {
      const [cfg, st] = await Promise.all([api.getConfig(), api.getWhatsAppStatus()]);
      setConfig(cfg);
      setStatus(st);
      setForm({
        evolution_base_url: cfg.evolution_base_url || "",
        evolution_instance: cfg.evolution_instance || "",
        evolution_api_key: "",
      });
      setError("");
    } catch (e) {
      setError("Erro ao carregar configuração: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        evolution_base_url: form.evolution_base_url,
        evolution_instance: form.evolution_instance,
      };
      // Só envia a chave se o usuário digitou uma nova
      if (form.evolution_api_key) payload.evolution_api_key = form.evolution_api_key;
      await api.updateConfig(payload);
      const [cfg, st] = await Promise.all([api.getConfig(), api.getWhatsAppStatus()]);
      setConfig(cfg);
      setStatus(st);
      setForm((f) => ({ ...f, evolution_api_key: "" }));
      setError("");
      alert("Configuração do WhatsApp salva!");
    } catch (e) {
      setError("Erro ao salvar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError("");
    try {
      const body = {};
      if (form.evolution_base_url) body.base_url = form.evolution_base_url;
      if (form.evolution_api_key) body.api_key = form.evolution_api_key;
      if (form.evolution_instance) body.instance = form.evolution_instance;
      const res = await api.testWhatsApp(body);
      alert(
        res.ok
          ? "Conexão OK! Evolution acessível e autenticação válida."
          : "Falha: " + (res.detail || "não foi possível conectar")
      );
    } catch (e) {
      setError("Erro ao testar: " + e.message);
    } finally {
      setTesting(false);
    }
  }

  const state = status?.state || "not_configured";

  return (
    <div className="layout">
      <header className="topbar">
        <div className="logo">Flow<span>AI</span></div>
        <nav className="topnav">
          <a href="/">Fluxos</a>
          <a href="/knowledge">Conhecimento</a>
          <a href="/whatsapp" className="active">WhatsApp</a>
          {(user?.role === "owner" || user?.role === "admin") && <a href="/admin">Administração</a>}
        </nav>
        <div className="topbar-right">
          <span className="user">{user?.email}</span>
          <button className="btn ghost" onClick={logout}>Sair</button>
        </div>
      </header>

      <main className="content">
        <div className="content-head">
          <div>
            <h2>Conexão WhatsApp</h2>
            <p className="muted">Conecte sua Evolution API para enviar e receber mensagens.</p>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {loading && <p className="muted">Carregando...</p>}

        {!loading && (
          <div className="whatsapp-status">
            <div className={`state-pill ${state}`}>
              Status: {STATE_LABELS[state] || state}
              {state === "open" && <span className="state-dot" />}
            </div>
            {status?.instance && <p className="muted">Instância: {status.instance}</p>}
            {status?.detail && <p className="muted">Detalhe: {status.detail}</p>}
          </div>
        )}

        <form className="whatsapp-form" onSubmit={handleSave}>
          <h3>Configuração da Evolution API</h3>
          <p className="muted">
            A Evolution API é <strong>self-hosted e gratuita</strong>. Você mesmo instala (via Docker na sua VPS) e
            conecta seu número de WhatsApp escaneando o QR Code. A "API Key" é a chave de acesso da sua instância:
            em versões recentes (2.4.0+) ela é obtida ao <strong>ativar a licença gratuita</strong> da instância no
            servidor de licenças da Evolution; em versões antigas é a senha que você define ao instalar
            (<code>AUTHENTICATION_API_KEY</code>).
          </p>

          <label className="field">
            <span>URL da Evolution API</span>
            <input
              type="text"
              placeholder="http://localhost:8080 ou http://SEU_IP:8080"
              value={form.evolution_base_url}
              onChange={(e) => set("evolution_base_url", e.target.value)}
            />
          </label>

          <label className="field">
            <span>Chave da API (API Key)</span>
            <input
              type="password"
              placeholder={config?.evolution_api_key || form.evolution_api_key ? "•••••••• (deixe vazio para manter)" : "API Key da sua instância (veja o guia abaixo)"}
              value={form.evolution_api_key}
              onChange={(e) => set("evolution_api_key", e.target.value)}
            />
          </label>

          <label className="field">
            <span>Nome da instância</span>
            <input
              type="text"
              placeholder="flowai"
              value={form.evolution_instance}
              onChange={(e) => set("evolution_instance", e.target.value)}
            />
          </label>

          <div className="btn-group">
            <button className="btn primary" type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Salvar configuração"}
            </button>
            <button className="btn secondary" type="button" onClick={handleTest} disabled={testing}>
              {testing ? "Testando..." : "Testar conexão"}
            </button>
          </div>
        </form>

        <div className="whatsapp-help">
          <h3>Como conectar seu WhatsApp</h3>
          <ol>
            <li>Instale a Evolution API na sua VPS (Docker).</li>
            <li>
              Obtenha a <strong>API Key</strong>: em versões 2.4.0+ a instância precisa ativar a <strong>licença gratuita</strong> —
              ela exibe uma URL de ativação; você faz login (Magic Link/Google/GitHub) e a instância recebe a chave
              automaticamente. Em versões antigas, a chave é a senha que você define (<code>AUTHENTICATION_API_KEY</code>).
            </li>
            <li>Crie uma instância com o mesmo nome configurado acima (ex: <code>flowai</code>).</li>
            <li>Escaneie o QR Code com o WhatsApp que vai atender.</li>
            <li>Configure o webhook da instância para apontar ao backend:</li>
          </ol>
          <pre>{`curl -X POST http://SEU_IP:8080/webhook/setFlowai \\
  -H "Content-Type: application/json" \\
  -H "apikey: SUA_API_KEY" \\
  -d '{"enabled":true,"url":"http://backend:8000/webhook/whatsapp/1","events":["messages.upsert"]}'`}</pre>
        </div>
      </main>
    </div>
  );
}

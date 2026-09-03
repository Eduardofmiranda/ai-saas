import { useEffect, useState } from "react";
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

export default function WhatsApp() {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState({ evolution_base_url: "", evolution_api_key: "", evolution_instance: "" });
  // Conexao via QR
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [qrBase64, setQrBase64] = useState(null);
  const [qrError, setQrError] = useState("");
  const [qrCountdown, setQrCountdown] = useState(0);

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

  async function handleConnect() {
    setConnecting(true);
    setQrError("");
    setQrBase64(null);
    try {
      const res = await api.connectWhatsApp();
      setQrBase64(res.qr_base64);
      setQrCountdown(45);
    } catch (e) {
      setQrError(e.message || "Erro ao gerar QR Code");
      // Se ja estiver conectado, recarrega o status
      await load();
    } finally {
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    if (!window.confirm("Desconectar o WhatsApp deste número?")) return;
    setDisconnecting(true);
    setError("");
    try {
      await api.disconnectWhatsApp();
      setQrBase64(null);
      await load();
      alert("WhatsApp desconectado.");
    } catch (e) {
      setError("Erro ao desconectar: " + e.message);
    } finally {
      setDisconnecting(false);
    }
  }

  // Auto-renova e re-verifica o QR (expira em ~20-60s)
  useEffect(() => {
    if (!qrBase64) return;
    if (qrCountdown <= 0) {
      handleConnect();
      return;
    }
    const refreshStatus = setInterval(async () => {
      try {
        const st = await api.getWhatsAppStatus();
        if (st.state === "open") {
          setQrBase64(null);
          setStatus(st);
        }
      } catch {}
    }, 3000);
    const timer = setInterval(() => setQrCountdown((c) => c - 1), 1000);
    return () => {
      clearInterval(refreshStatus);
      clearInterval(timer);
    };
  }, [qrBase64, qrCountdown]);

  return (
    <div className="layout">
      <Header />
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

        {!loading && (
          <div className="whatsapp-connect">
            {state === "open" ? (
              <>
                <h3>WhatsApp conectado</h3>
                <p className="muted">Seu número está pareado e recebe mensagens.</p>
                <button className="btn secondary" onClick={handleDisconnect} disabled={disconnecting}>
                  {disconnecting ? "Desconectando..." : "Desconectar WhatsApp"}
                </button>
              </>
            ) : (
              <>
                <h3>Conectar seu WhatsApp</h3>
                <p className="muted">Gere o QR Code e escaneie com o WhatsApp do seu celular (Aparelhos conectados → Conectar aparelho).</p>

                {qrError && <div className="error">{qrError}</div>}

                {!qrBase64 && (
                  <button className="btn primary" onClick={handleConnect} disabled={connecting}>
                    {connecting ? "Gerando QR..." : "Conectar WhatsApp"}
                  </button>
                )}

                {qrBase64 && (
                  <>
                    <div className="qr-box">
                      <img src={`data:image/png;base64,${qrBase64}`} alt="QR Code do WhatsApp" />
                    </div>
                    <p className="muted">Escanee com o WhatsApp do número que você quer conectar.</p>
                    <div className="qr-timer">O QR expira em breve — renovando automaticamente...</div>
                    <button className="btn ghost" onClick={handleConnect} disabled={connecting} style={{ marginTop: 8 }}>
                      Gerar novo QR
                    </button>
                  </>
                )}
              </>
            )}
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
              placeholder={config?.has_evolution_key || form.evolution_api_key ? "•••••••• (deixe vazio para manter)" : "API Key da sua instância (veja o guia abaixo)"}
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
          <h3>Como conectar seu WhatsApp (passo a passo)</h3>

          <h4>Fase 1 — Instalar a Evolution e conectar o número (uma vez, fora do nosso sistema)</h4>
          <ol>
            <li>Instale a <strong>Evolution API</strong> via Docker na sua VPS (ou localmente). Feito pelo <code>docker-compose.evolution.yml</code>.</li>
            <li>Obtenha a <strong>API Key</strong>: em versões 2.4.0+ a instância pede a <strong>ativação da licença gratuita</strong> e gera a chave; em versões antigas a chave é a senha que você define (<code>AUTHENTICATION_API_KEY</code>).</li>
            <li><strong>Crie uma instância</strong> com o MESMO nome que você digitou acima (ex: <code>flowai</code>):
              <pre>{`curl -X POST http://SEU_IP:8080/instance/createFlowAi \\
  -H "Content-Type: application/json" \\
  -H "apikey: SUA_API_KEY" \\
  -d '{"instanceName":"flowai","integration":"WHATSAPP-BAILEYS","qrcode":true}'`}</pre>
            </li>
            <li>No celular: WhatsApp → <strong>Aparelhos conectados</strong> → <strong>Conectar aparelho</strong> → escaneie o <strong>QR Code</strong>.</li>
            <li>Configure o <strong>webhook</strong> da instância para apontar ao backend (é assim que as mensagens <em>entram</em>):
              <pre>{`curl -X POST http://SEU_IP:8080/webhook/setFlowai \\
  -H "Content-Type: application/json" \\
  -H "apikey: SUA_API_KEY" \\
  -d '{"enabled":true,"url":"http://SEU_BACKEND:8000/webhook/whatsapp/1","events":["messages.upsert"]}'`}</pre>
              <span className="muted">Substitua <code>1</code> pela id da sua empresa e <code>SEU_BACKEND</code> pela URL do backend.</span>
            </li>
          </ol>

          <h4>Fase 2 — Configurar no nosso sistema</h4>
          <ol>
            <li>Preencha <strong>URL</strong> (ex: <code>http://localhost:8080</code>), <strong>API Key</strong> e <strong>instância</strong> no formulário acima.</li>
            <li>Clique em <strong>Salvar configuração</strong>.</li>
            <li>Clique em <strong>Testar conexão</strong> — confirma se a Evolution está acessível e a chave é válida.</li>
            <li>O <strong>Status</strong> mostra a conexão do número:
              <ul>
                <li><strong>Conectado</strong> → tudo certo, já pode usar.</li>
                <li><strong>Desconectado</strong> → a instância existe, mas o celular saiu (escaneie o QR de novo).</li>
                <li><strong>Instância não encontrada</strong> → crie a instância com esse nome na Evolution.</li>
                <li><strong>Sem conexão com a Evolution</strong> → a Evolution não está rodando ou a URL está errada.</li>
                <li><strong>Não configurado</strong> → você ainda não salvou nada.</li>
              </ul>
            </li>
          </ol>
        </div>
      </main>
    </div>
  );
}

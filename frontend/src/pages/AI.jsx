import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import KnowledgeSummaryCard from "../components/KnowledgeSummaryCard";
import Alert from "../components/ui/Alert";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import Skeleton from "../components/ui/Skeleton";

const PROVIDER_LABELS = { groq: "Groq", openai: "OpenAI", deepseek: "DeepSeek", mistral: "Mistral", ollama: "Ollama" };

function label(value) {
  return PROVIDER_LABELS[value] || value || "Não definido";
}

const PRESETS = [
  {
    name: "Atendente Amigável",
    prompt: `Você é um atendente virtual amigável e prestativo de uma empresa.
Responda de forma cordial e profissional, mas com um toque humano.
Use linguagem simples e acessível. Evite jargões técnicos.
Se não souber algo, diga honestamente e ofereça transferir para um humano.`,
    icon: "smile",
  },
  {
    name: "Vendedor Consultivo",
    prompt: `Você é um consultor de vendas consultivo e experiente.
Escute primeiro, entenda a necessidade do cliente, e só depois apresente soluções.
Destaque benefícios, não características técnicas.
Seja honesto sobre limitações. Nunca pressione — guie o cliente a melhor decisão.
Ao final de cada interação, sugira uma ação concreta.`,
    icon: "briefcase",
  },
  {
    name: "Suporte Técnico",
    prompt: `Você é um especialista em suporte técnico.
Seja preciso, objetivo e eficiente. Use passos numerados quando explicar processos.
Se o problema for complexo, colete informações antes de resolver.
Sempre confirme se a solução funcionou. Documente o que foi feito.`,
    icon: "wrench",
  },
  {
    name: "Recepcionista Virtual",
    prompt: `Você é a recepcionista virtual da empresa.
Seu papel é acolher, informar e direcionar.
Responda sobre horários, localização, serviços e FAQ.
Seja breve mas calorosa. Encaminhe dúvidas específicas para o setor correto.`,
    icon: "heart-pulse",
  },
];

export default function AI() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const [form, setForm] = useState({
    ai_on: false,
    ai_provider: "",
    ai_model: "",
    system_prompt: "",
  });

  useEffect(() => {
    api.getConfig()
      .then((cfg) => {
        setConfig(cfg);
        setForm({
          ai_on: cfg.ai_on ?? false,
          ai_provider: cfg.resolved_ai_provider || cfg.ai_provider || "",
          ai_model: cfg.resolved_ai_model || cfg.ai_model || "",
          system_prompt: cfg.system_prompt || "",
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const payload = {
        ai_on: form.ai_on,
        system_prompt: form.system_prompt,
      };
      const updated = await api.updateConfig(payload);
      setConfig(updated);
      setForm((f) => ({
        ...f,
        ai_on: updated.ai_on ?? f.ai_on,
        ai_provider: updated.resolved_ai_provider || f.ai_provider,
        ai_model: updated.resolved_ai_model || f.ai_model,
        system_prompt: updated.system_prompt ?? f.system_prompt,
      }));
      setSuccess("Configuração salva.");
      setTimeout(() => setSuccess(""), 3000);
    } catch (e) {
      setError("Erro ao salvar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  function applyPreset(preset) {
    set("system_prompt", preset.prompt);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    setError("");
    try {
      const res = await api.testAI();
      if (res.ok) {
        const reply = res.reply ? `"${res.reply.substring(0, 120)}${res.reply.length > 120 ? "..." : ""}"` : "";
        setTestResult({ ok: true, detail: `${res.detail}${reply ? " — " + reply : ""}` });
      } else {
        setTestResult({ ok: false, detail: res.detail || "Erro ao testar a IA." });
      }
    } catch (e) {
      setTestResult({ ok: false, detail: e.message });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="layout">
        <Header />
        <main className="content"><Skeleton variant="cards" /></main>
      </div>
    );
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <PageHeader
          title="Gerenciador de IA"
          subtitle="Configure como sua IA responde aos clientes no WhatsApp."
        >
          <button className="btn primary" onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </PageHeader>

        {error && <Alert variant="error">{error}</Alert>}
        {success && (
          <Alert variant="success" onDismiss={() => setSuccess("")}>
            {success}
          </Alert>
        )}

        {/* Status da IA */}
        <div className="ai-config">
          <div className="ai-status-bar">
            <span className={`ai-status-dot ${form.ai_on ? "on" : "off"}`} />
            <span className="u-strong">
              IA {form.ai_on ? "ativada" : "desativada"}
            </span>
            <label className="toggle u-push">
              <input
                type="checkbox"
                checked={form.ai_on}
                onChange={(e) => set("ai_on", e.target.checked)}
              />
              <span>{form.ai_on ? "Ligada" : "Desligada"}</span>
            </label>
          </div>
        </div>

        {/* Provedor e Modelo — definidos pelo superadmin, somente leitura */}
        <div className="ai-config">
          <h3>Provedor e Modelo</h3>
          <p className="muted">O provedor e modelo são definidos pelo administrador da plataforma.</p>
          <div className="ai-grid">
            <label className="field">
              <span>Provedor de IA</span>
              <input value={label(form.ai_provider)} disabled readOnly />
            </label>
            <label className="field">
              <span>Modelo</span>
              <input value={form.ai_model} disabled readOnly />
            </label>
          </div>
          <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <button className="btn ghost" onClick={handleTest} disabled={testing || !form.ai_provider}>
              {testing ? "Testando..." : "Testar conexão com IA"}
            </button>
            {testResult && (
              <span
                className={testResult.ok ? "test-result-ok" : "test-result-err"}
                style={{ fontSize: 13, flex: 1 }}
              >
                {testResult.detail}
              </span>
            )}
          </div>
        </div>

        {config?.ai_credential_source === "missing" && (
          <Alert variant="error">
            {!form.ai_provider
              ? "Nenhum provedor de IA foi configurado pelo administrador da plataforma."
              : `Não há chave disponível para ${label(form.ai_provider)}. Peça ao administrador para cadastrar a chave.`
            }
          </Alert>
        )}
        {config?.ai_credential_source === "platform" && (
          <Alert variant="success">A chave deste provedor é administrada pela plataforma.</Alert>
        )}

        {/* Base de Conhecimento */}
        <KnowledgeSummaryCard />

        {/* Personalidade da IA */}
        <div className="ai-config">
          <h3>Personalidade da IA</h3>
          <p className="muted" style={{ marginBottom: 12 }}>
            Defina como sua IA se comporta. Escolha um preset ou escreva sua própria personalidade.
          </p>

          <div className="ai-presets">
            {PRESETS.map((preset) => (
              <button
                key={preset.name}
                type="button"
                className={`ai-preset ${form.system_prompt === preset.prompt ? "active" : ""}`}
                onClick={() => applyPreset(preset)}
              >
                <h5><Icon name={preset.icon} size={18} /> {preset.name}</h5>
                <p>{preset.prompt.slice(0, 60)}...</p>
              </button>
            ))}
          </div>

          <label className="field" style={{ marginTop: 16 }}>
            <span>Instruções do sistema (System Prompt)</span>
            <textarea
              value={form.system_prompt}
              onChange={(e) => set("system_prompt", e.target.value)}
              placeholder="Ex: Você é um atendente virtual da empresa X. Responda de forma amigável e profissional..."
              rows={8}
            />
            <small className="field-help">
              Este texto define o comportamento da sua IA. Quanto mais específico, melhor a resposta.
            </small>
          </label>
        </div>
      </main>
    </div>
  );
}

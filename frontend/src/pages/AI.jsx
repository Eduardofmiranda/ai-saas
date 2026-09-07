import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import KnowledgeSummaryCard from "../components/KnowledgeSummaryCard";

const PROVIDERS = [
  { value: "groq", label: "Groq", hint: "Rápido e gratuito (GPT-OSS, Qwen)" },
  { value: "openai", label: "OpenAI", hint: "GPT-4o, GPT-4o-mini" },
  { value: "deepseek", label: "DeepSeek", hint: "Custo-benefício" },
  { value: "mistral", label: "Mistral", hint: "Europeu, rápido" },
  { value: "ollama", label: "Ollama", hint: "Local, sem custo" },
];

const PRESETS = [
  {
    name: "Atendente Amigável",
    prompt: `Você é um atendente virtual amigável e prestativo de uma empresa.
Responda de forma cordial e profissional, mas com um toque humano.
Use linguagem simples e acessível. Evite jargões técnicos.
Se não souber algo, diga honestamente e ofereça transferir para um humano.`,
    icon: "😊",
  },
  {
    name: "Vendedor Consultivo",
    prompt: `Você é um consultor de vendas consultivo e experiente.
Escute primeiro, entenda a necessidade do cliente, e só depois apresente soluções.
Destaque benefícios, não características técnicas.
Seja honesto sobre limitações. Nunca pressione — guie o cliente a melhor decisão.
Ao final de cada interação, sugira uma ação concreta.`,
    icon: "💼",
  },
  {
    name: "Suporte Técnico",
    prompt: `Você é um especialista em suporte técnico.
Seja preciso, objetivo e eficiente. Use passos numerados quando explicar processos.
Se o problema for complexo, colete informações antes de resolver.
Sempre confirme se a solução funcionou. Documente o que foi feito.`,
    icon: "🔧",
  },
  {
    name: "Recepcionista Virtual",
    prompt: `Você é a recepcionista virtual da empresa.
Seu papel é acolher, informar e direcionar.
Responda sobre horários, localização, serviços e FAQ.
Seja breve mas calorosa. Encaminhe dúvidas específicas para o setor correto.`,
    icon: "🏥",
  },
];

const MODELS = {
  groq: ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "qwen/qwen3.8-27b"],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
  deepseek: ["deepseek-v4-flash", "deepseek-v4-pro"],
  mistral: ["mistral-large-latest", "mistral-small-latest"],
  ollama: ["llama3.1", "mistral", "codellama"],
};

export default function AI() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [aiFieldsChanged, setAiFieldsChanged] = useState(false);
  const [resetAiDefaults, setResetAiDefaults] = useState(false);
  const [allowedProviders, setAllowedProviders] = useState([]);

  const [form, setForm] = useState({
    ai_on: false,
    ai_provider: "groq",
    ai_model: MODELS.groq[0],
    system_prompt: "",
  });

  useEffect(() => {
    Promise.all([api.getConfig(), api.getAllowedAI()])
      .then(([cfg, allowed]) => {
        setConfig(cfg);
        setAllowedProviders(allowed.allowed_providers || []);
        setForm({
          ai_on: cfg.ai_on ?? false,
          ai_provider: cfg.resolved_ai_provider || cfg.ai_provider || "groq",
          ai_model: cfg.resolved_ai_model || cfg.ai_model || "",
          system_prompt: cfg.system_prompt || "",
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function set(field, value) {
    if (field === "ai_provider" || field === "ai_model") {
      setAiFieldsChanged(true);
      setResetAiDefaults(false);
    }
    setForm((f) => ({ ...f, [field]: value }));
  }

  function useEnvironmentDefaults() {
    setAiFieldsChanged(false);
    setResetAiDefaults(true);
    setForm((f) => ({
      ...f,
      ai_provider: config?.resolved_ai_provider || f.ai_provider,
      ai_model: config?.resolved_ai_model || f.ai_model,
    }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const payload = { ...form };
      if (resetAiDefaults) {
        payload.ai_provider = "";
        payload.ai_model = "";
      } else if (!aiFieldsChanged) {
        // Salvar prompt/status nao deve transformar o default do .env em override.
        delete payload.ai_provider;
        delete payload.ai_model;
      }
      const updated = await api.updateConfig(payload);
      setConfig(updated);
      setAiFieldsChanged(false);
      setResetAiDefaults(false);
      setForm((f) => ({
        ...f,
        ai_provider: updated.resolved_ai_provider || f.ai_provider,
        ai_model: updated.resolved_ai_model || f.ai_model,
      }));
      setSuccess("Configuração salva.");
      setTimeout(() => setSuccess(""), 3000);
    } catch (e) {
      setError("Erro ao salvar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    setError("");
    try {
      const res = await api.testAI({ ai_provider: form.ai_provider, ai_model: form.ai_model });
      if (res.ok) {
        setTestResult({ ok: true, detail: `${res.detail} Resposta: "${res.reply}"` });
      } else {
        setTestResult({ ok: false, detail: `Falhou via ${res.provider || form.ai_provider} / ${res.model || form.ai_model}: ${res.detail || "Erro ao testar a IA."}` });
      }
    } finally {
      setTesting(false);
    }
  }

  function applyPreset(preset) {
    set("system_prompt", preset.prompt);
  }

  if (loading) {
    return (
      <div className="layout">
        <Header />
        <main className="content"><p className="muted">Carregando configurações da IA...</p></main>
      </div>
    );
  }

  const provider = PROVIDERS.find((p) => p.value === form.ai_provider);
  const hasRestriction = allowedProviders.length > 0;
  const visibleProviders = hasRestriction
    ? PROVIDERS.filter((p) => allowedProviders.includes(p.value))
    : PROVIDERS;
  const models = [...new Set([form.ai_model, ...(MODELS[form.ai_provider] || [])].filter(Boolean))];
  const visibleModels = hasRestriction
    ? models.filter((m) => {
        const providerModels = MODELS[form.ai_provider] || [];
        return providerModels.includes(m);
      })
    : models;

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <div>
            <h2>Gerenciador de IA</h2>
            <p className="muted">Configure como sua IA responde aos clientes no WhatsApp.</p>
          </div>
          <button className="btn primary" onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </div>

        {error && <div className="error">{error}</div>}
        {success && <div className="success-msg">{success}</div>}

        {/* Status da IA */}
        <div className="ai-config">
          <div className="ai-status-bar">
            <span className={`ai-status-dot ${form.ai_on ? "on" : "off"}`} />
            <span style={{ fontWeight: 600 }}>
              IA {form.ai_on ? "ativada" : "desativada"}
            </span>
            <label className="toggle" style={{ marginLeft: "auto" }}>
              <input
                type="checkbox"
                checked={form.ai_on}
                onChange={(e) => set("ai_on", e.target.checked)}
              />
              <span>{form.ai_on ? "Ligada" : "Desligada"}</span>
            </label>
          </div>
        </div>

        {/* Provedor e Modelo */}
        <div className="ai-config">
          <h3>Provedor e Modelo</h3>
          {hasRestriction && <p className="muted" style={{ marginBottom: 8 }}>Mostrando apenas provedores e modelos liberados pelo administrador.</p>}
          <div className="ai-grid">
            <label className="field">
              <span>Provedor de IA</span>
              <select
                value={form.ai_provider}
                onChange={(e) => {
                  set("ai_provider", e.target.value);
                  const newModels = MODELS[e.target.value] || [];
                  if (newModels.length > 0) set("ai_model", newModels[0]);
                }}
              >
                {visibleProviders.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              {provider && <small className="field-help">{provider.hint}</small>}
            </label>

            <label className="field">
              <span>Modelo</span>
              <select
                value={form.ai_model}
                onChange={(e) => set("ai_model", e.target.value)}
              >
                {visibleModels.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </label>
          </div>

          <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <button className="btn ghost" onClick={useEnvironmentDefaults}>
              Usar padrões do .env
            </button>
            <button className="btn ghost" onClick={handleTest} disabled={testing}>
              {testing ? "Testando..." : "Testar resposta da IA"}
            </button>
            {testResult && (
              <span className={testResult.ok ? "success-msg" : "error"} style={{ flex: 1 }}>
                {testResult.detail}
              </span>
            )}
          </div>
        </div>

        {config?.ai_credential_source === "missing" && (
          <div className="error">
            Não há chave disponível para o provedor selecionado. Peça ao administrador da plataforma para cadastrar a chave de {form.ai_provider}.
          </div>
        )}
        {config?.ai_credential_source === "platform" && (
          <div className="success-msg">A chave deste provedor é administrada pela plataforma.</div>
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
              <div
                key={preset.name}
                className={`ai-preset ${form.system_prompt === preset.prompt ? "active" : ""}`}
                onClick={() => applyPreset(preset)}
              >
                <h5>{preset.icon} {preset.name}</h5>
                <p>{preset.prompt.slice(0, 60)}...</p>
              </div>
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

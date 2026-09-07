import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import KnowledgeSummaryCard from "../components/KnowledgeSummaryCard";

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

export default function AI() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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

  if (loading) {
    return (
      <div className="layout">
        <Header />
        <main className="content"><p className="muted">Carregando configurações da IA...</p></main>
      </div>
    );
  }

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
        </div>

        {config?.ai_credential_source === "missing" && (
          <div className="error">
            {!form.ai_provider
              ? "Nenhum provedor de IA foi configurado pelo administrador da plataforma."
              : `Não há chave disponível para ${label(form.ai_provider)}. Peça ao administrador para cadastrar a chave.`
            }
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

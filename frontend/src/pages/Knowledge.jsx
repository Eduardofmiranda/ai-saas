import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

export default function Knowledge() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formContent, setFormContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  async function load() {
    try {
      const data = await api.getKnowledge();
      setItems(data);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!formName.trim() || !formContent.trim()) {
      setError("Nome e conteudo sao obrigatorios");
      return;
    }
    setSaving(true);
    try {
      await api.createKnowledge({ name: formName, description: formDesc, content: formContent });
      setFormName(""); setFormDesc(""); setFormContent(""); setShowForm(false);
      load();
    } catch (e) {
      setError("Erro ao criar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Excluir este item e todos os chunks?")) return;
    try {
      await api.deleteKnowledge(id);
      if (selected === id) { setSelected(null); setDetail(null); }
      load();
    } catch (e) {
      setError("Erro ao excluir: " + e.message);
    }
  }

  async function viewDetail(id) {
    try {
      const data = await api.getKnowledgeDetail(id);
      setDetail(data);
      setSelected(id);
    } catch (e) {
      setError("Erro ao carregar detalhe: " + e.message);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <h2>Base de Conhecimento</h2>
          <button className="btn primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancelar" : "+ Novo documento"}
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {showForm && (
          <form className="knowledge-form" onSubmit={handleCreate}>
            <input
              type="text"
              placeholder="Nome do documento"
              value={formName}
              onChange={e => setFormName(e.target.value)}
            />
            <input
              type="text"
              placeholder="Descricao (opcional)"
              value={formDesc}
              onChange={e => setFormDesc(e.target.value)}
            />
            <textarea
              placeholder="Conteudo do documento (sera dividido em chunks para busca semantica)"
              value={formContent}
              onChange={e => setFormContent(e.target.value)}
              rows={8}
            />
            <button className="btn primary" type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Salvar e indexar"}
            </button>
          </form>
        )}

        {loading && <p className="muted">Carregando...</p>}

        {!loading && items.length === 0 && !showForm && (
          <div className="empty">
            <p>Nenhum documento na base de conhecimento.</p>
            <p>Adicione documentos para usar com o no IA RAG nos fluxos.</p>
          </div>
        )}

        <div className="wf-grid">
          {items.map((item) => (
            <div
              key={item.id}
              className={`wf-card ${selected === item.id ? "selected" : ""}`}
              onClick={() => viewDetail(item.id)}
            >
              <h3>{item.name}</h3>
              <p>{item.description || "Sem descricao"}</p>
              <div className="wf-meta">
                <span className="muted">{item.chunk_count} chunks</span>
                <button className="btn ghost small danger" onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }}>
                  Excluir
                </button>
              </div>
            </div>
          ))}
        </div>

        {detail && (
          <div className="detail-panel">
            <h3>{detail.name}</h3>
            <p className="muted">{detail.description}</p>
            <h4>Chunks ({detail.chunks.length})</h4>
            <div className="chunks-list">
              {detail.chunks.map((ch) => (
                <div key={ch.id} className="chunk-card">
                  <span className="muted">#{ch.chunk_index} ({ch.tokens} tokens)</span>
                  <p>{ch.content.substring(0, 200)}{ch.content.length > 200 ? "..." : ""}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

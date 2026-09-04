import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

export default function Knowledge() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [editingId, setEditingId] = useState(null);

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

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function resetForm() {
    setForm({ name: "", description: "", content: "" });
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(item) {
    setForm({
      name: item.name,
      description: item.description || "",
      content: "",
    });
    setEditingId(item.id);
    setShowForm(true);
    setSelected(null);
    setDetail(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim() || (!editingId && !form.content.trim())) {
      setError("Nome e conteúdo são obrigatórios");
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await api.updateKnowledge(editingId, {
          name: form.name,
          description: form.description,
        });
      } else {
        await api.createKnowledge(form);
      }
      resetForm();
      load();
    } catch (e) {
      setError("Erro ao salvar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Excluir este documento e todos os chunks?")) return;
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

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.searchKnowledge(searchQuery, 5);
      setSearchResults(res);
    } catch (e) {
      setError("Erro na busca: " + e.message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="content-head">
          <div>
            <h2>Base de Conhecimento</h2>
            <p className="muted">Adicione documentos para sua IA usar como referência nas respostas (RAG).</p>
          </div>
          <div className="btn-group">
            <button className="btn ghost" onClick={() => { resetForm(); setSearchResults(null); }}>
              {searchResults ? "Limpar busca" : "Buscar"}
            </button>
            <button className="btn primary" onClick={() => { resetForm(); setShowForm(!showForm); }}>
              {showForm ? "Cancelar" : "+ Novo documento"}
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {/* Formulário */}
        {showForm && (
          <form className="knowledge-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>Nome do documento</span>
              <input
                type="text"
                placeholder="Ex: FAQ do atendimento"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Descrição (opcional)</span>
              <input
                type="text"
                placeholder="Resumo do conteúdo"
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
              />
            </label>
            {!editingId && (
              <label className="field">
                <span>Conteúdo</span>
                <textarea
                  placeholder="Cole ou digite o conteúdo que a IA usará como referência..."
                  value={form.content}
                  onChange={(e) => set("content", e.target.value)}
                  rows={8}
                  required
                />
                <small className="field-help">
                  O conteúdo será dividido em pedaços (chunks) para busca semantica.
                </small>
              </label>
            )}
            <button className="btn primary" type="submit" disabled={saving}>
              {saving ? "Salvando..." : editingId ? "Atualizar" : "Salvar e indexar"}
            </button>
          </form>
        )}

        {/* Busca */}
        {!showForm && (
          <form className="knowledge-search" onSubmit={handleSearch}>
            <input
              type="text"
              placeholder="Buscar no conhecimento..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button className="btn secondary" type="submit" disabled={searching}>
              {searching ? "Buscando..." : "Buscar"}
            </button>
          </form>
        )}

        {/* Resultados da busca */}
        {searchResults && (
          <div className="search-results">
            <h3>Resultados da busca</h3>
            {searchResults.length === 0 ? (
              <p className="muted">Nenhum resultado encontrado.</p>
            ) : (
              <div className="chunks-list">
                {searchResults.map((r, i) => (
                  <div key={i} className="chunk-card">
                    <span className="muted">
                      Similaridade: {(r.similarity * 100).toFixed(0)}% · {r.tokens} tokens
                    </span>
                    <p>{r.content.substring(0, 300)}{r.content.length > 300 ? "..." : ""}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {loading && <p className="muted">Carregando...</p>}

        {/* Lista de documentos */}
        {!loading && items.length === 0 && !showForm && !searchResults && (
          <div className="empty">
            <h3>Nenhum documento ainda</h3>
            <p>Adicione documentos para sua IA usar como referência. Você pode configurar o comportamento da IA em <strong>IA → Personalidade</strong>.</p>
            <button className="btn primary" onClick={() => setShowForm(true)}>
              + Adicionar primeiro documento
            </button>
          </div>
        )}

        {!searchResults && (
          <div className="wf-grid">
            {items.map((item) => (
              <div
                key={item.id}
                className={`wf-card ${selected === item.id ? "selected" : ""}`}
                onClick={() => viewDetail(item.id)}
              >
                <h3>{item.name}</h3>
                <p>{item.description || "Sem descrição"}</p>
                <div className="wf-meta">
                  <span className="muted">{item.chunk_count} chunks</span>
                  <div className="btn-group">
                    <button className="btn ghost small" onClick={(e) => { e.stopPropagation(); startEdit(item); }}>
                      Editar
                    </button>
                    <button className="btn ghost small danger" onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }}>
                      Excluir
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Detalhe do documento */}
        {detail && (
          <div className="detail-panel">
            <div className="detail-header">
              <div>
                <h3>{detail.name}</h3>
                <p className="muted">{detail.description}</p>
              </div>
              <div className="btn-group">
                <button className="btn ghost small" onClick={() => startEdit(detail)}>
                  Editar
                </button>
                <button className="btn ghost small" onClick={() => { setSelected(null); setDetail(null); }}>
                  Fechar
                </button>
              </div>
            </div>
            <h4>Pedidos ({detail.chunks.length})</h4>
            <div className="chunks-list">
              {detail.chunks.map((ch) => (
                <div key={ch.id} className="chunk-card">
                  <span className="muted">#{ch.chunk_index} · {ch.tokens} tokens</span>
                  <p>{ch.content.substring(0, 300)}{ch.content.length > 300 ? "..." : ""}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

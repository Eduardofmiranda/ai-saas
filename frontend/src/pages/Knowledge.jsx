import { useEffect, useState, useRef } from "react";
import { api } from "../api";
import Header from "../components/Header";
import Alert from "../components/ui/Alert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import PageHeader from "../components/ui/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import Skeleton from "../components/ui/Skeleton";
import Pagination from "../components/ui/Pagination";

const PAGE_SIZE = 12;

export default function Knowledge() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const fileInputRef = useRef(null);

  async function load() {
    try {
      const res = await api.getKnowledge({ q, limit: PAGE_SIZE, offset: page * PAGE_SIZE });
      setItems(res.items || []);
      setTotal(res.total || 0);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [q, page]);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function resetForm() {
    setForm({ name: "", description: "", content: "" });
    setEditingId(null);
    setShowForm(false);
    setUploadFile(null);
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
    if (uploadFile) {
      await handleUpload();
      return;
    }
    if (!form.name.trim() || (!editingId && !form.content.trim())) {
      setError("Nome e conteudo sao obrigatorios");
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
      setSuccess(editingId ? "Documento atualizado com sucesso!" : "Documento criado com sucesso!");
      load();
    } catch (e) {
      setError("Erro ao salvar: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadKnowledge(uploadFile, form.name, form.description);
      resetForm();
      setSuccess("Arquivo enviado e indexado com sucesso!");
      load();
    } catch (e) {
      setError("Erro no upload: " + e.message);
    } finally {
      setUploading(false);
    }
  }

  async function confirmDeleteDoc() {
    const id = confirmDelete;
    setConfirmDelete(null);
    try {
      await api.deleteKnowledge(id);
      if (selected === id) { setSelected(null); setDetail(null); }
      setSuccess("Documento excluido com sucesso!");
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
        <PageHeader
          title="Base de Conhecimento"
          subtitle="Adicione documentos para sua IA usar como referencia nas respostas (RAG)."
        >
          <button className="btn primary" onClick={() => { resetForm(); setShowForm(!showForm); }}>
            {showForm ? "Cancelar" : "+ Novo documento"}
          </button>
        </PageHeader>

        {error && <Alert variant="error" onDismiss={() => setError("")}>{error}</Alert>}
        {success && <Alert variant="success" onDismiss={() => setSuccess("")}>{success}</Alert>}

        {/* Formulario */}
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
              <span>Descricao (opcional)</span>
              <input
                type="text"
                placeholder="Resumo do conteudo"
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
              />
            </label>
            {!editingId && (
              <>
                <div className="field">
                  <span>Arquivo</span>
                  <label
                    htmlFor="kb-file-input"
                    className="knowledge-dropzone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setUploadFile(e.dataTransfer.files[0]); }}
                  >
                    <input
                      id="kb-file-input"
                      type="file"
                      className="sr-only"
                      accept=".pdf,.docx,.doc,.txt,.csv,.md,.markdown,.json,.xml,.html"
                      onChange={(e) => { if (e.target.files[0]) setUploadFile(e.target.files[0]); }}
                    />
                    {uploadFile ? (
                      <p style={{ margin: 0 }}>
                        <strong>{uploadFile.name}</strong>
                        <br />
                        <small className="muted">{(uploadFile.size / 1024).toFixed(1)} KB - Clique para trocar</small>
                      </p>
                    ) : (
                      <p style={{ margin: 0 }}>
                        Arraste um arquivo aqui ou <strong>clique para selecionar</strong>
                        <br />
                        <small className="muted">PDF, DOCX, TXT, CSV, Markdown (max 10MB)</small>
                      </p>
                    )}
                  </label>
                </div>
                <label className="field">
                  <span>Ou cole o conteudo como texto</span>
                  <textarea
                    placeholder="Se preferir, cole o conteudo diretamente..."
                    value={form.content}
                    onChange={(e) => { set("content", e.target.value); if (e.target.value) setUploadFile(null); }}
                    rows={6}
                  />
                  <small className="field-help">
                    O conteudo sera dividido em pedacos (chunks) para busca semantica.
                  </small>
                </label>
              </>
            )}
            <button className="btn primary" type="submit" disabled={saving || uploading}>
              {uploading ? "Enviando..." : saving ? "Salvando..." : editingId ? "Atualizar" : "Salvar e indexar"}
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
              aria-label="Buscar no conhecimento"
            />
            <button className="btn secondary" type="submit" disabled={searching}>
              {searching ? "Buscando..." : "Buscar"}
            </button>
            {searchResults && (
              <button className="btn ghost" type="button" onClick={() => { setSearchResults(null); setSearchQuery(""); }}>
                Limpar
              </button>
            )}
          </form>
        )}

        {/* Resultados da busca */}
        {searchResults && (
          <div className="search-results">
            <h3>Resultados da busca</h3>
            {searchResults.length === 0 ? (
              <EmptyState icon={<Icon name="search" size={40} />} title="Nenhum resultado encontrado">
                Tente outros termos de busca.
              </EmptyState>
            ) : (
              <div className="chunks-list">
                {searchResults.map((r, i) => (
                  <div key={r.chunk_id || `${r.doc_name || ""}-${i}`} className="chunk-card">
                    <span className="muted">
                      Similaridade: {(r.similarity * 100).toFixed(0)}% - {r.tokens} tokens
                    </span>
                    <p>{r.content.substring(0, 300)}{r.content.length > 300 ? "..." : ""}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {loading && <Skeleton variant="cards" />}

        {!searchResults && !showForm && !loading && (
          <div className="list-toolbar">
            <input
              className="list-search"
              placeholder="Filtrar por nome..."
              aria-label="Filtrar documentos por nome"
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(0); }}
            />
          </div>
        )}

        {/* Lista de documentos */}
        {!loading && items.length === 0 && !showForm && !searchResults && (
          <EmptyState
            icon={<Icon name="book-open" size={40} />}
            title={q ? "Nenhum documento encontrado" : "Nenhum documento ainda"}
            action={
              q ? (
                <button className="btn ghost" onClick={() => { setQ(""); setPage(0); }}>
                  Limpar filtro
                </button>
              ) : (
                <button className="btn primary" onClick={() => setShowForm(true)}>
                  Adicionar primeiro documento
                </button>
              )
            }
          >
            {q
              ? "Nenhum documento corresponde ao filtro informado."
              : "Adicione documentos (PDF, Word, texto) ou cole conteudo para sua IA usar como referencia."}
          </EmptyState>
        )}

        {!searchResults && (
          <div className="wf-grid">
            {items.map((item) => (
              <button
                type="button"
                key={item.id}
                className={`wf-card ${selected === item.id ? "selected" : ""}`}
                onClick={() => viewDetail(item.id)}
              >
                <h3>{item.name}</h3>
                <p>{item.description || "Sem descricao"}</p>
                <div className="wf-meta">
                  <span className="muted">{item.chunk_count} pedacos</span>
                  <div className="btn-group">
                    <button type="button" className="btn ghost small" onClick={(e) => { e.stopPropagation(); startEdit(item); }}>
                      Editar
                    </button>
                    <button type="button" className="btn ghost small danger" onClick={(e) => { e.stopPropagation(); setConfirmDelete(item.id); }}>
                      Excluir
                    </button>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {!searchResults && !showForm && total > PAGE_SIZE && (
          <Pagination total={total} page={page} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="documento(s)" />
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
            <h4>Pedacos ({detail.chunks.length})</h4>
            <div className="chunks-list">
              {detail.chunks.map((ch) => (
                <div key={ch.id} className="chunk-card">
                  <span className="muted">#{ch.chunk_index} - {ch.tokens} tokens</span>
                  <p>{ch.content.substring(0, 300)}{ch.content.length > 300 ? "..." : ""}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {confirmDelete && (
        <ConfirmDialog
          title="Excluir documento"
          message="Excluir este documento e todos os chunks? Esta acao nao pode ser desfeita."
          confirmLabel="Excluir"
          onConfirm={confirmDeleteDoc}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}

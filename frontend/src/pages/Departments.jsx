import { useEffect, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";

export default function Departments() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  async function load() {
    try {
      const res = await api.getDepartments();
      setDepartments(Array.isArray(res) ? res : []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createDepartment({ name: name.trim(), description: desc.trim() });
      setName(""); setDesc("");
      load();
    } catch (e) { setError(e.message); }
  }

  async function save(id) {
    try {
      await api.updateDepartment(id, { name: editName.trim(), description: editDesc.trim() });
      setEditId(null);
      load();
    } catch (e) { setError(e.message); }
  }

  async function remove(id) {
    if (!confirm("Remover este setor?")) return;
    try {
      await api.deleteDepartment(id);
      load();
    } catch (e) { setError(e.message); }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="page-header">
          <h1>Setores</h1>
          <p className="muted">Configure setores para encaminhamento de atendimento.</p>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="card" style={{ maxWidth: 500 }}>
          <h3>Novo Setor</h3>
          <form onSubmit={create} className="stack">
            <input
              className="input"
              placeholder="Nome do setor"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="input"
              placeholder="Descricao (opcional)"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
            <button className="btn primary" type="submit" disabled={!name.trim()}>Criar</button>
          </form>
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <h3>Setores Existentes</h3>
          {loading ? (
            <p className="muted">Carregando...</p>
          ) : departments.length === 0 ? (
            <p className="muted">Nenhum setor configurado.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Descricao</th>
                  <th style={{ width: 140 }}></th>
                </tr>
              </thead>
              <tbody>
                {departments.map((d) => (
                  <tr key={d.id}>
                    {editId === d.id ? (
                      <>
                        <td><input className="input" value={editName} onChange={(e) => setEditName(e.target.value)} /></td>
                        <td><input className="input" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} /></td>
                        <td>
                          <button className="btn primary small" onClick={() => save(d.id)}>Salvar</button>{" "}
                          <button className="btn ghost small" onClick={() => setEditId(null)}>Cancelar</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td><strong>{d.name}</strong></td>
                        <td className="muted">{d.description || "—"}</td>
                        <td>
                          <button className="btn ghost small" onClick={() => { setEditId(d.id); setEditName(d.name); setEditDesc(d.description); }}>Editar</button>{" "}
                          <button className="btn danger small" onClick={() => remove(d.id)}>Remover</button>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}

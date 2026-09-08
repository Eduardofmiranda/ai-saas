import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Header from "../components/Header";
import { useAuth } from "../context/AuthContext";

const DAYS = [
  ["mon", "Segunda", "Seg"],
  ["tue", "Terça", "Ter"],
  ["wed", "Quarta", "Qua"],
  ["thu", "Quinta", "Qui"],
  ["fri", "Sexta", "Sex"],
  ["sat", "Sábado", "Sáb"],
  ["sun", "Domingo", "Dom"],
];

const TIMEZONES = [
  "America/Sao_Paulo",
  "America/Manaus",
  "America/Cuiaba",
  "America/Fortaleza",
  "America/Recife",
  "America/Santarem",
  "UTC",
];

const STATUS_META = {
  scheduled: { label: "Agendado", cls: "scheduled" },
  confirmed: { label: "Confirmado", cls: "confirmed" },
  completed: { label: "Concluído", cls: "completed" },
  canceled: { label: "Cancelado", cls: "canceled" },
};

const ORIGIN_LABEL = {
  whatsapp: "WhatsApp",
  manual: "Manual",
  workflow: "Fluxo",
};

function defaultSchedule() {
  return Object.fromEntries(DAYS.map(([key]) => [key, ["09:00", "18:00"]]));
}

function addMinutes(hhmm, mins) {
  const [h, m] = hhmm.split(":").map(Number);
  const total = (h * 60 + m + mins) % (24 * 60);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function todayDate() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function Agenda() {
  const { user } = useAuth();
  const isManager = user?.role === "owner" || user?.role === "admin";

  const [cfg, setCfg] = useState(null);
  const [appts, setAppts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  const [filters, setFilters] = useState({ status: "", dateFrom: "", dateTo: "", query: "" });

  const [configOpen, setConfigOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState(null);

  async function load() {
    try {
      const [c, list] = await Promise.all([
        api.getAgendaConfig(),
        api.getAgendaAppointments({ limit: 200 }),
      ]);
      setCfg(c);
      setAppts(Array.isArray(list) ? list : []);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") {
        setConfigOpen(false);
        setCreateOpen(false);
        setCancelTarget(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = useMemo(() => {
    const q = filters.query.trim().toLowerCase();
    let rows = appts;
    if (filters.status) rows = rows.filter((a) => a.status === filters.status);
    if (filters.dateFrom) rows = rows.filter((a) => a.date >= filters.dateFrom);
    if (filters.dateTo) rows = rows.filter((a) => a.date <= filters.dateTo);
    if (q) {
      rows = rows.filter(
        (a) =>
          (a.customer_name || "").toLowerCase().includes(q) ||
          (a.phone || "").includes(q) ||
          (a.service || "").toLowerCase().includes(q)
      );
    }
    return [...rows].sort((a, b) =>
      a.date === b.date ? a.start_time.localeCompare(b.start_time) : a.date.localeCompare(b.date)
    );
  }, [appts, filters]);

  const activeDayCount = useMemo(() => {
    if (!cfg?.schedule) return 0;
    return Object.values(cfg.schedule).filter((w) => Array.isArray(w) && w[0] && w[1]).length;
  }, [cfg]);

  const activeCount = useMemo(
    () => appts.filter((a) => a.status === "scheduled" || a.status === "confirmed").length,
    [appts]
  );
  const canceledCount = useMemo(() => appts.filter((a) => a.status === "canceled").length, [appts]);

  const openDays = DAYS
    .map(([key, , short]) => {
      const w = cfg?.schedule?.[key];
      return Array.isArray(w) && w[0] && w[1] ? `${short} ${w[0]}-${w[1]}` : null;
    })
    .filter(Boolean);

  async function toggleEnabled() {
    if (!isManager || !cfg) return;
    setError("");
    setOk("");
    try {
      const saved = await api.updateAgendaConfig({ enabled: !cfg.enabled });
      setCfg(saved);
      setOk(saved.enabled ? "Agenda ativada. A secretária IA já pode criar agendamentos." : "Agenda desativada.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function confirmCancel(appt) {
    setError("");
    setOk("");
    try {
      await api.cancelAgendaAppointment(appt.id);
      setOk(`Agendamento de ${appt.customer_name || appt.phone} cancelado.`);
      setCancelTarget(null);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="layout">
      <Header />
      <main className="content">
        <div className="page-header page-header-row">
          <div className="page-header">
            <h1>Agenda</h1>
            <p className="muted">
              Compromissos e agendamentos da empresa — inclusive os criados pela Secretaria IA no WhatsApp.
            </p>
          </div>
          <button className="btn primary" onClick={() => setCreateOpen(true)}>+ Novo agendamento</button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {ok && (
          <div className="alert alert-success" role="status">
            {ok}
            <button
              aria-label="Fechar aviso"
              style={{ marginLeft: "auto", background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 14 }}
              onClick={() => setOk("")}
            >✕</button>
          </div>
        )}

        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-icon">📅</span>
            <div>
              <div className="stat-value">{activeCount}</div>
              <div className="stat-label">Compromissos ativos</div>
            </div>
          </div>
          <div className="stat-card green">
            <span className="stat-icon">🗓️</span>
            <div>
              <div className="stat-value">{activeDayCount}</div>
              <div className="stat-label">Dias de agenda</div>
            </div>
          </div>
          <div className="stat-card amber">
            <span className="stat-icon">✖️</span>
            <div>
              <div className="stat-value">{canceledCount}</div>
              <div className="stat-label">Cancelados</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="bh-header">
            <div>
              <h3 style={{ margin: 0 }}>Secretaria IA</h3>
              <p className="muted" style={{ margin: "4px 0 0" }}>
                Quando ativa, a IA usa a agenda para consultar disponibilidade e criar, alterar e cancelar agendamentos pelo WhatsApp.
              </p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={Boolean(cfg?.enabled)}
                  onChange={toggleEnabled}
                  disabled={!isManager || !cfg}
                />
                <span>Ativar agenda</span>
              </label>
              {isManager && (
                <button className="btn ghost small" onClick={() => setConfigOpen(true)} disabled={!cfg}>
                  Configurar
                </button>
              )}
            </div>
          </div>
          {loading ? (
            <p className="muted" style={{ margin: "12px 0 0" }}>Carregando configuração...</p>
          ) : (
            <div className="bh-fields" style={{ marginTop: 12 }}>
              <p style={{ margin: 0 }}>
                <b>{cfg?.enabled ? "Agenda ativa" : "Agenda inativa"}</b>
                <span className="muted">
                  {" "}· duração padrão {cfg?.slot_duration} min · antecedência mínima {cfg?.min_advance} min
                  {cfg?.timezone ? ` · fuso ${cfg.timezone}` : ""}
                </span>
              </p>
              <p className="muted" style={{ margin: "6px 0 0" }}>
                {openDays.length
                  ? "Horários: " + openDays.join(", ")
                  : "Nenhum dia de agenda configurado."}
              </p>
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Mensagem de confirmação: “{cfg?.confirmation_message || ""}”
              </p>
            </div>
          )}
        </div>

        <div className="toolbar" style={{ marginTop: 20 }}>
          <div className="search-box grow">
            <span className="search-icon">🔎</span>
            <input
              className="input"
              placeholder="Buscar por cliente, telefone ou serviço..."
              value={filters.query}
              onChange={(e) => setFilters((f) => ({ ...f, query: e.target.value }))}
            />
          </div>
          <select
            className="input"
            style={{ width: 170 }}
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">Todos os status</option>
            {Object.entries(STATUS_META).map(([key, meta]) => (
              <option key={key} value={key}>{meta.label}</option>
            ))}
          </select>
          <input
            className="input"
            type="date"
            value={filters.dateFrom}
            onChange={(e) => setFilters((f) => ({ ...f, dateFrom: e.target.value }))}
            title="De"
          />
          <input
            className="input"
            type="date"
            value={filters.dateTo}
            onChange={(e) => setFilters((f) => ({ ...f, dateTo: e.target.value }))}
            title="Até"
          />
          <span className="count-pill">
            {filtered.length} de <b>{appts.length}</b>
          </span>
        </div>

        {loading ? (
          <div className="card">
            <p className="muted">Carregando agenda...</p>
          </div>
        ) : appts.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📅</div>
            <h3>Nenhum agendamento</h3>
            <p>
              Crie o primeiro compromisso manualmente ou deixe a Secretaria IA marcar pelo WhatsApp.
            </p>
            <button className="btn primary" onClick={() => setCreateOpen(true)}>+ Novo agendamento</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔎</div>
            <h3>Nada encontrado</h3>
            <p>Ajuste os filtros ou a busca para localizar os agendamentos.</p>
            <button
              className="btn ghost"
              onClick={() => setFilters({ status: "", dateFrom: "", dateTo: "", query: "" })}
            >
              Limpar filtros
            </button>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 110 }}>Data</th>
                  <th style={{ width: 110 }}>Horário</th>
                  <th>Cliente</th>
                  <th style={{ width: 130 }}>Telefone</th>
                  <th>Serviço</th>
                  <th style={{ width: 110 }}>Status</th>
                  <th style={{ width: 110 }}>Origem</th>
                  <th style={{ width: 110 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => {
                  const meta = STATUS_META[a.status] || { label: a.status, cls: "scheduled" };
                  return (
                    <tr key={a.id}>
                      <td className="cell-strong">{a.date}</td>
                      <td>{a.start_time}–{a.end_time}</td>
                      <td>
                        <span className="cell-strong">{a.customer_name || "—"}</span>
                        {a.notes && <div className="muted">{a.notes}</div>}
                      </td>
                      <td className="muted">{a.phone}</td>
                      <td className="muted">{a.service || "—"}</td>
                      <td>
                        <span className={`state-pill ${meta.cls}`}>{meta.label}</span>
                      </td>
                      <td className="muted">{ORIGIN_LABEL[a.origin] || a.origin}</td>
                      <td>
                        {a.status !== "canceled" && (
                          <div className="row-actions">
                            <button
                              className="btn ghost small danger"
                              onClick={() => setCancelTarget(a)}
                            >
                              Cancelar
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {configOpen && cfg && <ConfigModal cfg={cfg} onClose={() => setConfigOpen(false)} onSaved={(saved) => { setCfg(saved); setOk("Configuração da agenda salva."); }} />}

      {createOpen && (
        <CreateModal
          cfg={cfg}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setOk("Agendamento criado.");
            setCreateOpen(false);
            load();
          }}
        />
      )}

      {cancelTarget && (
        <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) setCancelTarget(null); }}>
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-title">Cancelar agendamento</div>
              <button className="modal-close" onClick={() => setCancelTarget(null)} aria-label="Fechar">✕</button>
            </div>
            <div className="modal-body">
              <p style={{ margin: "0 0 6px", lineHeight: 1.5 }}>
                Deseja cancelar o agendamento de <strong>{cancelTarget.customer_name || cancelTarget.phone}</strong> em{" "}
                <strong>{cancelTarget.date} às {cancelTarget.start_time}</strong>?
              </p>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                O compromisso ficará com status “cancelado” e o histórico registra quem cancelou.
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn ghost" onClick={() => setCancelTarget(null)}>Manter</button>
              <button className="btn solid-danger" onClick={() => confirmCancel(cancelTarget)}>Cancelar agendamento</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigModal({ cfg, onClose, onSaved }) {
  const [data, setData] = useState(() => {
    const schedule = defaultSchedule();
    for (const [key] of DAYS) {
      const w = cfg.schedule?.[key];
      if (Array.isArray(w) && w.length === 2) schedule[key] = w;
      else schedule[key] = ["", ""];
    }
    return {
      enabled: Boolean(cfg.enabled),
      timezone: cfg.timezone || "America/Sao_Paulo",
      schedule,
      slot_duration: cfg.slot_duration,
      min_advance: cfg.min_advance,
      confirmation_message: cfg.confirmation_message || "",
      blocked: (cfg.blocked || []).map((b) => ({ ...b })),
    };
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  function setSchedule(key, idx, value) {
    setData((d) => {
      const schedule = { ...d.schedule, [key]: [...d.schedule[key]] };
      schedule[key][idx] = value;
      return { ...d, schedule };
    });
  }

  function toggleDay(key, active) {
    setData((d) => {
      const schedule = { ...d.schedule, [key]: active ? ["09:00", "18:00"] : ["", ""] };
      return { ...d, schedule };
    });
  }

  function setBlocked(i, field, value) {
    setData((d) => {
      const blocked = d.blocked.map((b, idx) => (idx === i ? { ...b, [field]: value } : b));
      return { ...d, blocked };
    });
  }

  async function handleSave(e) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setErr("");
    try {
      const schedule = {};
      for (const [key] of DAYS) {
        const [start, end] = data.schedule[key];
        schedule[key] = start && end ? [start, end] : [];
      }
      const saved = await api.updateAgendaConfig({
        enabled: data.enabled,
        timezone: data.timezone,
        schedule,
        slot_duration: Number(data.slot_duration),
        min_advance: Number(data.min_advance),
        confirmation_message: data.confirmation_message,
        blocked: data.blocked.filter((b) => b.date && b.start && b.end),
      });
      onSaved(saved);
      onClose();
    } catch (e) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !saving) onClose(); }}>
      <div className="modal" style={{ width: 560, maxWidth: "100%" }} role="dialog" aria-modal="true">
        <div className="modal-header">
          <div className="modal-title">Configurar agenda</div>
          <button className="modal-close" onClick={onClose} aria-label="Fechar">✕</button>
        </div>
        <form onSubmit={handleSave}>
          <div className="modal-body">
            {err && <div className="alert alert-error">{err}</div>}
            <div className="stack" style={{ gap: 14 }}>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={data.enabled}
                  onChange={(e) => setData((d) => ({ ...d, enabled: e.target.checked }))}
                />
                <span>Agenda ativa</span>
              </label>

              <div className="field">
                <span>Fuso horário</span>
                <select
                  className="input"
                  value={data.timezone}
                  onChange={(e) => setData((d) => ({ ...d, timezone: e.target.value }))}
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <span>Horários por dia</span>
                <div className="bh-days">
                  {DAYS.map(([key, label]) => {
                    const [start, end] = data.schedule[key];
                    const active = !!(start && end);
                    return (
                      <div key={key} className={`bh-day ${active ? "active" : ""}`}>
                        <label className="bh-day-toggle">
                          <input
                            type="checkbox"
                            checked={active}
                            onChange={(e) => toggleDay(key, e.target.checked)}
                          />
                          <span>{label}</span>
                        </label>
                        {active && (
                          <div className="bh-day-times">
                            <input
                              type="time"
                              value={start}
                              onChange={(e) => setSchedule(key, 0, e.target.value)}
                            />
                            <span>até</span>
                            <input
                              type="time"
                              value={end}
                              onChange={(e) => setSchedule(key, 1, e.target.value)}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <label className="field">
                  <span>Duração padrão (min)</span>
                  <input
                    className="input"
                    type="number"
                    min="5"
                    max="240"
                    value={data.slot_duration}
                    onChange={(e) => setData((d) => ({ ...d, slot_duration: e.target.value }))}
                  />
                </label>
                <label className="field">
                  <span>Antecedência mínima (min)</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    value={data.min_advance}
                    onChange={(e) => setData((d) => ({ ...d, min_advance: e.target.value }))}
                  />
                </label>
              </div>

              <div className="field">
                <span>Mensagem de confirmação</span>
                <textarea
                  className="input"
                  rows="3"
                  maxLength={500}
                  placeholder="Ex.: Agendamento confirmado! 🎉 Obrigado por escolher a gente."
                  value={data.confirmation_message}
                  onChange={(e) => setData((d) => ({ ...d, confirmation_message: e.target.value }))}
                />
              </div>

              <div className="field">
                <span>Datas bloqueadas</span>
                {data.blocked.map((b, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                    <input
                      className="input"
                      type="date"
                      value={b.date}
                      onChange={(e) => setBlocked(i, "date", e.target.value)}
                    />
                    <input
                      className="input"
                      type="time"
                      value={b.start}
                      onChange={(e) => setBlocked(i, "start", e.target.value)}
                      title="Início"
                    />
                    <input
                      className="input"
                      type="time"
                      value={b.end}
                      onChange={(e) => setBlocked(i, "end", e.target.value)}
                      title="Fim"
                    />
                    <button
                      type="button"
                      className="btn ghost small danger"
                      onClick={() => setData((d) => ({ ...d, blocked: d.blocked.filter((_, idx) => idx !== i) }))}
                    >
                      Remover
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() =>
                    setData((d) => ({ ...d, blocked: [...d.blocked, { date: "", start: "", end: "" }] }))
                  }
                >
                  + Adicionar bloqueio
                </button>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn ghost" onClick={onClose} disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn primary" disabled={saving}>
              {saving ? "Salvando..." : "Salvar configuração"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CreateModal({ cfg, onClose, onCreated }) {
  const [data, setData] = useState({
    date: todayDate(),
    start_time: "",
    customer_name: "",
    phone: "",
    service: "",
    notes: "",
  });
  const [slots, setSlots] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!data.date) {
      setSlots([]);
      return;
    }
    let cancelled = false;
    api
      .getAgendaAvailability(data.date)
      .then((res) => { if (!cancelled) setSlots(Array.isArray(res.slots) ? res.slots : []); })
      .catch(() => { if (!cancelled) setSlots([]); });
    return () => { cancelled = true; };
  }, [data.date]);

  const duration = Number(cfg?.slot_duration) || 60;
  const endTime = data.start_time ? addMinutes(data.start_time, duration) : "";

  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;
    if (!data.phone.trim() || !data.start_time) {
      setErr("Informe o telefone do cliente e o horário.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await api.createAgendaAppointment({
        date: data.date,
        start_time: data.start_time,
        end_time: endTime,
        phone: data.phone.trim(),
        customer_name: data.customer_name.trim() || null,
        service: data.service.trim() || null,
        notes: data.notes.trim() || null,
        origin: "manual",
      });
      onCreated();
    } catch (e) {
      setErr(e.message);
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !saving) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-header">
          <div className="modal-title">Novo agendamento</div>
          <button className="modal-close" onClick={onClose} aria-label="Fechar">✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {err && <div className="alert alert-error">{err}</div>}
            <div className="stack" style={{ gap: 14 }}>
              <div className="field">
                <span>Data</span>
                <input
                  className="input"
                  type="date"
                  value={data.date}
                  min={todayDate()}
                  onChange={(e) => setData((d) => ({ ...d, date: e.target.value, start_time: "" }))}
                />
              </div>

              <div className="field">
                <span>Horário de início</span>
                <input
                  className="input"
                  type="time"
                  value={data.start_time}
                  onChange={(e) => setData((d) => ({ ...d, start_time: e.target.value }))}
                />
                <span className="field-help">Fim automático: {endTime || "—"} ({duration} min)</span>
                {slots.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                    {slots.map((s) => (
                      <button
                        key={s}
                        type="button"
                        className={`btn small ${data.start_time === s ? "primary" : "ghost"}`}
                        onClick={() => setData((d) => ({ ...d, start_time: s }))}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                {slots.length === 0 && cfg?.enabled && data.date && (
                  <span className="field-help">Sem horários livres nesta data.</span>
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <label className="field">
                  <span>Nome do cliente</span>
                  <input
                    className="input"
                    value={data.customer_name}
                    maxLength={120}
                    onChange={(e) => setData((d) => ({ ...d, customer_name: e.target.value }))}
                  />
                </label>
                <label className="field">
                  <span>Telefone <span className="field-required">obrigatório</span></span>
                  <input
                    className="input"
                    placeholder="(11) 99999-9999"
                    value={data.phone}
                    onChange={(e) => setData((d) => ({ ...d, phone: e.target.value }))}
                  />
                </label>
              </div>

              <label className="field">
                <span>Serviço</span>
                <input
                  className="input"
                  placeholder="Ex.: Consulta, Corte, Avaliação"
                  value={data.service}
                  maxLength={120}
                  onChange={(e) => setData((d) => ({ ...d, service: e.target.value }))}
                />
              </label>

              <label className="field">
                <span>Observações</span>
                <textarea
                  className="input"
                  rows="2"
                  maxLength={500}
                  value={data.notes}
                  onChange={(e) => setData((d) => ({ ...d, notes: e.target.value }))}
                />
              </label>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn ghost" onClick={onClose} disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn primary" disabled={saving}>
              {saving ? "Criando..." : "Criar agendamento"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
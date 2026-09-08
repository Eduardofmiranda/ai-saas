import { useEffect, useState } from "react";
import { api } from "../api";

const DAYS = [
  ["mon", "Segunda"],
  ["tue", "Terça"],
  ["wed", "Quarta"],
  ["thu", "Quinta"],
  ["fri", "Sexta"],
  ["sat", "Sábado"],
  ["sun", "Domingo"],
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

function emptySchedule() {
  return Object.fromEntries(DAYS.map(([key]) => [key, ["09:00", "18:00"]]));
}

export default function BusinessHoursPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  async function load() {
    try {
      const bh = await api.getBusinessHours();
      const schedule = emptySchedule();
      for (const [key] of DAYS) {
        const window = bh.schedule?.[key];
        if (Array.isArray(window) && window.length === 2) schedule[key] = window;
        else schedule[key] = ["", ""];
      }
      setData({
        enabled: Boolean(bh.enabled),
        timezone: bh.timezone || "America/Sao_Paulo",
        schedule,
        message: bh.message || "",
      });
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <p className="muted">Carregando horário...</p>;

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

  function hasConfiguredDay() {
    return Object.values(data.schedule).some((w) => w[0] && w[1]);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setOk("");
    try {
      const schedule = {};
      for (const [key] of DAYS) {
        const [start, end] = data.schedule[key];
        schedule[key] = start && end ? [start, end] : [];
      }
      const saved = await api.updateBusinessHours({
        enabled: data.enabled,
        timezone: data.timezone,
        schedule,
        message: data.message,
      });
      setOk("Horário de atendimento salvo.");
      setData((d) => ({ ...d, enabled: Boolean(saved.enabled), timezone: saved.timezone || d.timezone }));
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bh-panel">
      <div className="bh-header">
        <div>
          <h3>Horário de atendimento</h3>
          <p className="muted">
            Fora do expediente, respondemos com uma mensagem automática e não
            geramos respostas da IA.
          </p>
        </div>
        <label className="toggle">
          <input
            type="checkbox"
            checked={data.enabled}
            onChange={(e) => setData((d) => ({ ...d, enabled: e.target.checked, ok: "" }))}
          />
          <span>Respeitar horário</span>
        </label>
      </div>

      <div className="bh-fields">
        <label>
          Fuso horário
          <select
            value={data.timezone}
            onChange={(e) => setData((d) => ({ ...d, timezone: e.target.value }))}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </select>
        </label>

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

        {data.enabled && !hasConfiguredDay() && (
          <p className="bh-warning">Marque pelos menos um dia de atendimento para o horário valer.</p>
        )}

        <label className="bh-message">
          Mensagem fora do horário
          <textarea
            rows="3"
            value={data.message}
            placeholder="Estamos fora do horário de atendimento. Retornaremos em breve!"
            onChange={(e) => setData((d) => ({ ...d, message: e.target.value }))}
          />
        </label>
      </div>

      {error && <div className="error">{error}</div>}
      {ok && <div className="bh-ok">{ok}</div>}

      <div className="bh-actions">
        <button className="btn primary" onClick={handleSave} disabled={saving}>
          {saving ? "Salvando..." : "Salvar horário"}
        </button>
      </div>
    </div>
  );
}
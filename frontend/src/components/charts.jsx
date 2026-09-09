const DAY_LABEL = (iso) => {
  const d = iso.split("-");
  return `${parseInt(d[2], 10)}/${parseInt(d[1], 10)}`;
};

export function DonutChart({ segments, size = 150, thickness = 18 }) {
  const total = segments.reduce((acc, s) => acc + s.value, 0);
  const r = (size - thickness) / 2;
  const c = Math.PI * 2 * r;
  const cx = size / 2;
  const cy = size / 2;

  if (total === 0) {
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Sem dados">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--panel2)" strokeWidth={thickness} />
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="donut-zero">0</text>
      </svg>
    );
  }

  let acc = 0;
  const arcs = segments.map((s) => {
    const frac = s.value / total;
    const arc = { ...s, offsetPct: acc, len: frac * c };
    acc += frac;
    return arc;
  });

  const label = segments
    .filter((s) => s.value > 0)
    .map((s) => `${s.label}: ${s.value}`)
    .join(", ");

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Conversas por status: ${label}`} className="donut-chart">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--panel2)" strokeWidth={thickness} />
      {arcs.map((s) => (
        <circle
          key={s.key}
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={s.color}
          strokeWidth={thickness}
          strokeDasharray={`${s.len} ${c - s.len}`}
          strokeDashoffset={-s.offsetPct * c}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      ))}
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="donut-total">{total}</text>
    </svg>
  );
}

export function BarChart({ data, height = 130, labelEvery = 1, dense = false }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className={`chart-bars${dense ? " dense" : ""}`} style={{ height }}>
      {data.map((d, i) => (
        <div key={d.key} className="chart-col">
          <div className="chart-bar-track">
            <div
              className="chart-bar"
              style={{ height: `${Math.round((d.value / max) * 100)}%`, background: d.color || "var(--accent)" }}
              title={`${d.label}: ${d.value}`}
            />
          </div>
          {i % labelEvery === 0 && <span className="chart-bar-label">{d.label}</span>}
        </div>
      ))}
    </div>
  );
}

export function StackedBarChart({ data, height = 130, labelEvery = 1, dense = false }) {
  const max = Math.max(1, ...data.map((d) => d.success + d.error));
  return (
    <div className={`chart-bars${dense ? " dense" : ""}`} style={{ height }}>
      {data.map((d, i) => {
        const total = d.success + d.error;
        const okPct = Math.round((d.success / max) * 100);
        const errPct = Math.round((d.error / max) * 100);
        return (
          <div key={d.key} className="chart-col">
            <div className="chart-bar-track">
              <div className="chart-bar-stack" title={`${d.label}: ${total} (${d.success} ok · ${d.error} erro)`}>
                <div className="chart-bar seg ok" style={{ height: `${okPct}%` }} />
                <div className="chart-bar seg err" style={{ height: `${errPct}%` }} />
              </div>
            </div>
            {i % labelEvery === 0 && <span className="chart-bar-label">{d.label}</span>}
          </div>
        );
      })}
    </div>
  );
}

export function ChartLegend({ items }) {
  return (
    <div className="chart-legend">
      {items.map((it) => (
        <span key={it.key} className="chart-legend-item">
          <span className="chart-dot" style={{ background: it.color }} />
          {it.label}
          <strong>{it.value}</strong>
        </span>
      ))}
    </div>
  );
}

export { DAY_LABEL };
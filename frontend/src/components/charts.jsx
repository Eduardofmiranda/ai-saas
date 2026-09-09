import {
  Bar,
  BarChart as ReBarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const DAY_LABEL = (iso) => {
  const d = iso.split("-");
  return `${parseInt(d[2], 10)}/${parseInt(d[1], 10)}`;
};

const fmt = (n) => (Number(n) || 0).toLocaleString("pt-BR");
const fmtAxis = (v) => (v >= 1000 ? `${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}k` : `${v}`);

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const items = payload.filter((p) => p.value != null && p.value !== 0);
  return (
    <div className="rtip">
      <div className="rtip-title">
        {label} <span className="rtip-total">{fmt(items.reduce((a, p) => a + (Number(p.value) || 0), 0))}</span>
      </div>
      {items.map((p) => (
        <div key={p.name || p.dataKey} className="rtip-row">
          <span className="chart-dot" style={{ background: p.color || p.fill }} />
          {p.name}
          <strong>{fmt(p.value)}</strong>
        </div>
      ))}
    </div>
  );
}

export function BarChart({ data = [], height = 180, labelEvery = 1, name = "Valor", color = "var(--accent)" }) {
  if (!data.length) return <div className="muted">Sem dados no período</div>;
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <ReBarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval={labelEvery > 1 ? labelEvery - 1 : 0}
            tick={{ fontSize: 10.5 }}
            tickMargin={4}
          />
          <YAxis
            width={34}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            tick={{ fontSize: 10.5 }}
            tickFormatter={fmtAxis}
          />
          <Tooltip cursor={{ fill: "var(--panel2)" }} content={<ChartTooltip />} />
          <Bar dataKey="value" name={name} fill={color} radius={[4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StackedBarChart({ data = [], height = 180, labelEvery = 1 }) {
  if (!data.length) return <div className="muted">Sem dados no período</div>;
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <ReBarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval={labelEvery > 1 ? labelEvery - 1 : 0}
            tick={{ fontSize: 10.5 }}
            tickMargin={4}
          />
          <YAxis
            width={34}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            tick={{ fontSize: 10.5 }}
            tickFormatter={fmtAxis}
          />
          <Tooltip cursor={{ fill: "var(--panel2)" }} content={<ChartTooltip />} />
          <Bar dataKey="ok" name="Sucesso" stackId="s" fill="var(--green)" radius={[4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false} />
          <Bar dataKey="err" name="Erro" stackId="s" fill="var(--red)" radius={[4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  );
}

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
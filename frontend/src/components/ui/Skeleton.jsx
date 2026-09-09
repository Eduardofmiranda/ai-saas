export default function Skeleton({ variant = "lines", rows = 3, cards = 6 }) {
  if (variant === "cards") {
    return (
      <div className="skeleton-cards" role="status" aria-label="Carregando...">
        {Array.from({ length: cards }).map((_, i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton skeleton-avatar" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line short" />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="skeleton-lines" role="status" aria-label="Carregando...">
      <div className="skeleton skeleton-title" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className={`skeleton skeleton-line ${i % 2 ? "short" : ""}`} />
      ))}
    </div>
  );
}
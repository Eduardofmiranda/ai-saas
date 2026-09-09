export default function Pagination({ total, page, pageSize, onChange, itemLabel = "itens" }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span className="pageno">{total} {itemLabel} no total</span>
      <div className="btn-group">
        <button className="btn ghost small" disabled={page === 0} onClick={() => onChange(page - 1)}>
          Anterior
        </button>
        <span className="pageno">Página {page + 1} de {pages}</span>
        <button
          className="btn ghost small"
          disabled={(page + 1) * pageSize >= total}
          onClick={() => onChange(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
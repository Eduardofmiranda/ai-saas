import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import Icon from "./ui/Icon";

export default function KnowledgeSummaryCard() {
  const [count, setCount] = useState(0);
  const [chunks, setChunks] = useState(0);

  useEffect(() => {
    api
      .getKnowledge()
      .then((res) => {
        const items = res.items || [];
        setCount(items.length);
        setChunks(items.reduce((acc, i) => acc + (i.chunk_count || 0), 0));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="ai-kb-summary">
      <div>
        <h4><Icon name="book-open" size={18} /> Base de Conhecimento</h4>
        <p>
          Sua IA usa documentos de referência para responder clientes. Adicione
          mais documentos para melhorar as respostas.
        </p>
        <span className="ai-kb-stats">
          <Icon name="file-text" size={14} /> {count}{" "}
          {count === 1 ? "documento" : "documentos"} · {chunks}{" "}
          {chunks === 1 ? "chunk" : "chunks"} indexados
        </span>
      </div>
      <Link to="/knowledge" className="btn ghost">
        Gerenciar base →
      </Link>
    </div>
  );
}

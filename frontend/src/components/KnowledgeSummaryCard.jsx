import { useEffect, useState } from "react";
import { api } from "../api";

export default function KnowledgeSummaryCard() {
  const [count, setCount] = useState(0);
  const [chunks, setChunks] = useState(0);

  useEffect(() => {
    api
      .getKnowledge()
      .then((items) => {
        setCount(items.length);
        setChunks(items.reduce((acc, i) => acc + (i.chunk_count || 0), 0));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="ai-kb-summary">
      <div>
        <h4>📚 Base de Conhecimento</h4>
        <p>
          Sua IA usa documentos de referência para responder clientes. Adicione
          mais documentos para melhorar as respostas.
        </p>
        <span className="ai-kb-stats">
          📄 {count} {count === 1 ? "documento" : "documentos"} · {chunks}{" "}
          {chunks === 1 ? "chunk" : "chunks"} indexados
        </span>
      </div>
      <a href="/knowledge" className="btn ghost">
        Gerenciar base →
      </a>
    </div>
  );
}

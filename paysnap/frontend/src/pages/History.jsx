import { useState, useEffect } from "react";
import { api } from "../api/client";

const card = {
  background: "#111827",
  border: "1px solid #1f2937",
  borderRadius: "12px",
  padding: "20px",
  marginBottom: "16px"
};

export default function History() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.getHistory();
      if (res.success) setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: "16px" }}>
        <div>
          <div style={{ fontSize: "1.2rem", fontWeight: "700" }}>
            Mi Historial
          </div>
          <div style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: "2px" }}>
            Guardado localmente, encriptado
          </div>
        </div>
        <button
          onClick={load}
          style={{
            background: "#1f2937", border: "1px solid #374151",
            borderRadius: "8px", padding: "8px 14px",
            color: "#d1d5db", cursor: "pointer", fontSize: "0.82rem"
          }}
        >
          🔄 Actualizar
        </button>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: "40px", color: "#6b7280" }}>
          Cargando...
        </div>
      )}

      {data && (
        <>
          {/* Summary */}
          {data.summary && (
            <div style={{
              ...card,
              background: "rgba(249,115,22,0.08)",
              border: "1px solid rgba(249,115,22,0.3)"
            }}>
              <div style={{ color: "#fb923c", fontSize: "0.88rem" }}>
                {data.summary.message_es}
              </div>
              {data.summary.total_money_owed > 0 && (
                <div style={{ color: "#f97316", fontWeight: "800",
                              fontSize: "1.6rem", marginTop: "8px" }}>
                  ${data.summary.total_money_owed.toFixed(2)}
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {(!data.records || data.records.length === 0) && (
            <div style={{ textAlign: "center", padding: "48px 16px", color: "#6b7280" }}>
              <div style={{ fontSize: "3rem", marginBottom: "12px" }}>📋</div>
              <div style={{ fontWeight: "600", marginBottom: "6px" }}>
                No hay recibos todavía
              </div>
              <div style={{ fontSize: "0.82rem" }}>
                Analiza tu primer recibo para comenzar
              </div>
            </div>
          )}

          {/* Records */}
          {data.records?.map((r, i) => (
            <div key={i} style={{
              borderRadius: "10px",
              padding: "14px 16px",
              marginBottom: "10px",
              border: r.has_violation
                ? "1px solid rgba(239,68,68,0.3)"
                : "1px solid rgba(34,197,94,0.3)",
              background: r.has_violation
                ? "rgba(239,68,68,0.07)"
                : "rgba(34,197,94,0.07)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between",
                            alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: "600", fontSize: "0.9rem" }}>
                    {r.has_violation ? "🚨" : "✅"} {r.employer}
                  </div>
                  <div style={{ color: "#6b7280", fontSize: "0.75rem", marginTop: "3px" }}>
                    {r.timestamp?.slice(0, 10)} · {r.state} ·{" "}
                    {r.hours_worked}h @ ${r.hourly_rate}/hr
                  </div>
                </div>
                {r.has_violation && (
                  <div style={{ color: "#f87171", fontWeight: "800", fontSize: "1rem" }}>
                    ${r.money_owed?.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Export */}
          {data.records?.length > 0 && (
            <button
              onClick={() => api.exportEvidence()}
              style={{
                width: "100%", background: "#1f2937",
                border: "1px solid #374151", borderRadius: "10px",
                padding: "14px", color: "#d1d5db",
                cursor: "pointer", fontSize: "0.9rem",
                fontWeight: "600", marginTop: "8px"
              }}
            >
              📤 Exportar evidencia para abogado
            </button>
          )}
        </>
      )}
    </div>
  );
}
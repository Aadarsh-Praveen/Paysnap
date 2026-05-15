import { useState, useEffect } from "react";
import { api } from "../api/client";

const ORANGE = "#F97316";
const TEXT   = "#0F172A";
const MUTED  = "#64748B";
const BORDER = "#E2E8F0";
const LIGHT  = "#F1F5F9";

export default function History({ t, language }) {
  const [records,  setRecords]  = useState([]);
  const [summary,  setSummary]  = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const res = await api.getHistory(language);
      if (res.success) {
        setRecords(res.data?.records || []);
        setSummary(res.data?.summary || null);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [language]);

  // Build summary text using translations
  const buildSummaryText = (s) => {
    if (!s) return "";
    const count      = s.total_paystubs   || 0;
    const violations = s.total_violations || 0;
    const total      = s.total_potential  || 0;

    // Use translated template if available, else English
    if (t.history_summary) {
      return t.history_summary
        .replace("{count}", count)
        .replace("{violations}", violations)
        .replace("{total}", `$${total.toFixed(2)}`);
    }
    return `${count} paystub${count !== 1 ? "s" : ""} analyzed · ${violations} violation${violations !== 1 ? "s" : ""} found · $${total.toFixed(2)} total potential`;
  };

  return (
    <div style={{ color: TEXT }}>

      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: "16px",
      }}>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", margin: 0, color: TEXT }}>
            {t.history_title || "Your paystub history"}
          </h2>
          <p style={{ fontSize: "0.78rem", color: MUTED, margin: "4px 0 0" }}>
            {t.history_sub || "Saved locally on your device, encrypted"}
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={load} disabled={loading} style={{
            background: LIGHT, border: `1px solid ${BORDER}`,
            borderRadius: "8px", padding: "8px 14px",
            fontSize: "0.78rem", fontWeight: "600",
            color: TEXT, cursor: "pointer",
            display: "flex", alignItems: "center", gap: "6px",
          }}>
            {loading ? (
              <span style={{
                width:"12px", height:"12px",
                border:`2px solid ${ORANGE}`, borderTopColor:"transparent",
                borderRadius:"50%", animation:"spin 0.8s linear infinite",
                display:"inline-block",
              }} />
            ) : "↻"}
            {t.refresh_btn || "Refresh"}
          </button>
          <button onClick={() => api.exportEvidence()} style={{
            background: `linear-gradient(135deg, ${ORANGE}, #EA580C)`,
            border: "none", borderRadius: "8px",
            padding: "8px 14px", fontSize: "0.78rem",
            fontWeight: "600", color: "white", cursor: "pointer",
          }}>
            📤 {t.export_btn || "Export"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background:"rgba(239,68,68,0.07)", border:"1px solid rgba(239,68,68,0.25)",
          borderRadius:"10px", padding:"12px 16px",
          color:"#dc2626", fontSize:"0.88rem", marginBottom:"12px",
        }}>❌ {error}</div>
      )}

      {/* Summary — translated */}
      {summary && (
        <div style={{
          background: "rgba(249,115,22,0.06)",
          border: "1px solid rgba(249,115,22,0.2)",
          borderRadius: "14px", padding: "16px 20px",
          marginBottom: "16px",
        }}>
          <div style={{ fontSize: "0.78rem", color: MUTED, marginBottom: "6px" }}>
            {buildSummaryText(summary)}
          </div>
          <div style={{
            fontFamily: "monospace", fontWeight: "800",
            fontSize: "1.8rem", color: ORANGE,
          }}>
            ${(summary.total_potential || 0).toFixed(2)}
          </div>
          <div style={{ fontSize: "0.75rem", color: MUTED, marginTop: "2px" }}>
            {t.violation_found || "potentially owed"}
          </div>
        </div>
      )}

      {/* Records */}
      {records.length === 0 ? (
        <div style={{
          background: "#fff", border: `1px solid ${BORDER}`,
          borderRadius: "16px", padding: "40px 20px",
          textAlign: "center",
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "12px" }}>📋</div>
          <div style={{ color: MUTED, fontSize: "0.88rem", whiteSpace: "pre-line" }}>
            {t.no_history || "No paystubs analyzed yet.\nUpload your first paystub to begin."}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {records.map((r, i) => (
            <div key={i} style={{
              background: "#fff", border: `1px solid ${BORDER}`,
              borderRadius: "14px", padding: "16px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{
                  width: "36px", height: "36px", borderRadius: "10px",
                  background: r.has_violation
                    ? "rgba(249,115,22,0.1)" : "rgba(34,197,94,0.1)",
                  display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: "1.1rem",
                }}>
                  {r.has_violation ? "🚨" : "✅"}
                </div>
                <div>
                  <div style={{ fontWeight: "700", fontSize: "0.9rem", color: TEXT }}>
                    {r.employer_name || "Unknown"}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: MUTED, marginTop: "2px" }}>
                    {r.date} · {r.state}
                  </div>
                </div>
              </div>
              {r.has_violation && (
                <div style={{
                  fontFamily: "monospace", fontWeight: "700",
                  fontSize: "1rem", color: ORANGE,
                }}>
                  ${(r.total_owed || 0).toFixed(2)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
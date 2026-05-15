import React from "react";

const ORANGE = "#F97316";
const TEXT   = "#0F172A";
const MUTED  = "#64748B";
const BORDER = "#E2E8F0";
const LIGHT  = "#F1F5F9";

export default function Rights({ t }) {
  const wages = [
    { state: "🏖️ California", wage: "$16.50/hr" },
    { state: "🗽 New York",   wage: "$16.00/hr" },
    { state: "🌾 Illinois",   wage: "$14.00/hr" },
    { state: "☀️ Florida",    wage: "$13.00/hr" },
    { state: "⭐ Texas",      wage: "$7.25/hr"  },
  ];

  const rights = [
    { icon:"💰", title: t.right_1_title, desc: t.right_1_desc },
    { icon:"⏰", title: t.right_2_title, desc: t.right_2_desc },
    { icon:"🛡️", title: t.right_3_title, desc: t.right_3_desc },
    { icon:"📋", title: t.right_4_title, desc: t.right_4_desc },
  ];

  const privacyItems = [
    t.privacy_1, t.privacy_2, t.privacy_3, t.privacy_4
  ];

  return (
    <div style={{ color: TEXT }}>

      {/* Rights card */}
      <div style={{
        background: "#fff",
        border: `1px solid ${BORDER}`,
        borderRadius: "16px",
        overflow: "hidden",
        marginBottom: "16px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        {/* Header */}
        <div style={{
          background: `linear-gradient(135deg, ${ORANGE}, #EA580C)`,
          padding: "16px 20px",
        }}>
          <div style={{
            fontSize: "0.72rem", fontWeight: "700",
            textTransform: "uppercase", letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.8)", marginBottom: "4px",
          }}>
            {t.rights_sub || "Regardless of immigration status"}
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: "800", color: "white" }}>
            {t.rights_title || "Your Rights as a Worker"}
          </div>
        </div>

        {/* Rights items */}
        {rights.map((r, i) => (
          <div key={i} style={{
            padding: "16px 20px",
            borderBottom: i < rights.length - 1 ? `1px solid ${BORDER}` : "none",
            display: "flex", gap: "14px", alignItems: "flex-start",
          }}>
            <div style={{
              width: "40px", height: "40px", borderRadius: "10px",
              background: "rgba(249,115,22,0.08)",
              display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: "1.2rem", flexShrink: 0,
            }}>
              {r.icon}
            </div>
            <div>
              <div style={{ fontWeight: "700", fontSize: "0.92rem", color: TEXT, marginBottom: "3px" }}>
                {r.title}
              </div>
              <div style={{ fontSize: "0.82rem", color: MUTED, lineHeight: "1.5" }}>
                {r.desc}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Minimum wages */}
      <div style={{
        background: "#fff", border: `1px solid ${BORDER}`,
        borderRadius: "16px", overflow: "hidden",
        marginBottom: "16px", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        <div style={{ padding: "14px 20px", borderBottom: `1px solid ${BORDER}` }}>
          <div style={{
            fontSize: "0.72rem", fontWeight: "700",
            textTransform: "uppercase", letterSpacing: "0.1em",
            color: ORANGE,
          }}>
            💰 {t.wages_title || "Minimum Wages 2025"}
          </div>
        </div>
        {wages.map((w, i) => (
          <div key={i} style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", padding: "14px 20px",
            borderBottom: i < wages.length - 1 ? `1px solid ${BORDER}` : "none",
            background: i % 2 === 0 ? "#fff" : LIGHT,
          }}>
            <span style={{ fontSize: "0.92rem", fontWeight: "600", color: TEXT }}>
              {w.state}
            </span>
            <span style={{
              fontFamily: "monospace", fontWeight: "800",
              fontSize: "0.95rem", color: ORANGE,
            }}>
              {w.wage}
            </span>
          </div>
        ))}
      </div>

      {/* Report violation */}
      <div style={{
        background: "rgba(59,130,246,0.04)",
        border: "1px solid rgba(59,130,246,0.2)",
        borderRadius: "16px", padding: "20px",
        marginBottom: "16px", textAlign: "center",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        <div style={{
          fontSize: "0.72rem", fontWeight: "700",
          textTransform: "uppercase", letterSpacing: "0.1em",
          color: "#2563eb", marginBottom: "10px",
        }}>
          📞 {t.report_title || "Report a Violation"}
        </div>
        <div style={{
          fontFamily: "monospace", fontWeight: "800",
          fontSize: "1.8rem", color: ORANGE, marginBottom: "6px",
        }}>
          1-866-487-9243
        </div>
        <div style={{ fontSize: "0.82rem", color: MUTED }}>
          {t.report_free || "Free · Bilingual · Regardless of immigration status"}
        </div>
      </div>

      {/* Privacy */}
      <div style={{
        background: "#fff", border: `1px solid ${BORDER}`,
        borderRadius: "16px", padding: "20px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        <div style={{
          fontSize: "0.72rem", fontWeight: "700",
          textTransform: "uppercase", letterSpacing: "0.1em",
          color: ORANGE, marginBottom: "14px",
        }}>
          🔒 {t.privacy_title || "Your Privacy in PaySnap"}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {privacyItems.map((item, i) => (
            <div key={i} style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
              <div style={{
                width: "20px", height: "20px", borderRadius: "50%",
                background: "rgba(34,197,94,0.1)",
                display: "flex", alignItems: "center",
                justifyContent: "center", flexShrink: 0, marginTop: "1px",
              }}>
                <span style={{ color: "#16a34a", fontSize: "0.7rem", fontWeight: "700" }}>✓</span>
              </div>
              <span style={{ fontSize: "0.88rem", color: TEXT, lineHeight: "1.5" }}>
                {item}
              </span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
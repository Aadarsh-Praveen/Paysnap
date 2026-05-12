import { useState } from "react";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import Rights from "./pages/Rights";

export default function App() {
  const [tab, setTab] = useState("analyze");

  const tabs = [
    { id: "analyze", emoji: "📋", label: "Analizar" },
    { id: "history", emoji: "📊", label: "Historial" },
    { id: "rights",  emoji: "⚖️", label: "Derechos" },
  ];

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0a0a0f" }}>

      {/* Top Header */}
      <div style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        borderBottom: "1px solid #f97316",
        padding: "20px 16px 16px",
        textAlign: "center"
      }}>
        <div style={{ fontSize: "2.4rem", fontWeight: "800", color: "#ffffff" }}>
          💼 PaySnap
        </div>
        <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginTop: "4px" }}>
          Tu recibo · Tu derecho · En tu teléfono
        </div>

        {/* Disclaimer */}
        <div style={{
          marginTop: "12px",
          background: "rgba(251, 191, 36, 0.1)",
          border: "1px solid rgba(251, 191, 36, 0.3)",
          borderRadius: "8px",
          padding: "8px 12px",
          fontSize: "0.78rem",
          color: "#fbbf24",
          maxWidth: "500px",
          margin: "12px auto 0"
        }}>
          ⚖️ <strong>Aviso:</strong> No es consejo legal.
          Tus datos <strong>nunca salen de tu dispositivo.</strong>
        </div>
      </div>

      {/* Tab Bar */}
      <div style={{
        display: "flex",
        borderBottom: "1px solid #1f2937",
        backgroundColor: "#111827",
        position: "sticky",
        top: 0,
        zIndex: 10
      }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flex: 1,
              padding: "14px 8px",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: tab === t.id ? "700" : "400",
              color: tab === t.id ? "#f97316" : "#6b7280",
              borderBottom: tab === t.id ? "2px solid #f97316" : "2px solid transparent",
              transition: "all 0.2s",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px"
            }}
          >
            <span>{t.emoji}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Page Content */}
      <div style={{ maxWidth: "600px", margin: "0 auto", padding: "20px 16px 40px" }}>
        {tab === "analyze" && <Analyze />}
        {tab === "history" && <History />}
        {tab === "rights"  && <Rights />}
      </div>

    </div>
  );
}
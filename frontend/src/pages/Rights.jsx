const card = {
  background: "#111827",
  border: "1px solid #1f2937",
  borderRadius: "12px",
  padding: "20px",
  marginBottom: "16px"
};

const WAGES = [
  { state: "California", flag: "🏖️", amount: "$16.50" },
  { state: "New York",   flag: "🗽", amount: "$16.00" },
  { state: "Illinois",   flag: "🌾", amount: "$14.00" },
  { state: "Florida",    flag: "☀️", amount: "$13.00" },
  { state: "Texas",      flag: "⭐", amount: "$7.25"  },
];

export default function Rights({ t }) {
  if (!t) return null;

  const rights = [
    {
      icon: "💰",
      title: t.right_1_title || "Minimum wage",
      desc:  t.right_1_desc  || "Your employer MUST pay at least the state minimum wage"
    },
    {
      icon: "⏰",
      title: t.right_2_title || "Overtime",
      desc:  t.right_2_desc  || "Over 40 hours/week = 1.5x your regular rate"
    },
    {
      icon: "🛡️",
      title: t.right_3_title || "No retaliation",
      desc:  t.right_3_desc  || "Illegal to fire you for reporting wage violations"
    },
    {
      icon: "📋",
      title: t.right_4_title || "Federal FLSA Law",
      desc:  t.right_4_desc  || "Protects all workers in the United States"
    },
  ];

  const privacy = [
    t.privacy_1 || "Zero cloud data — everything on your device",
    t.privacy_2 || "No account or password required",
    t.privacy_3 || "No telemetry or tracking",
    t.privacy_4 || "History encrypted locally",
  ];

  return (
    <div>

      {/* Rights */}
      <div style={card}>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "6px" }}>
          {t.rights_title || "Your Rights"}
        </div>
        <div style={{ color: "#9ca3af", fontSize: "0.82rem", marginBottom: "16px" }}>
          {t.rights_sub || "Regardless of immigration status:"}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {rights.map((r) => (
            <div key={r.title} style={{
              display: "flex", gap: "12px", alignItems: "flex-start"
            }}>
              <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>{r.icon}</span>
              <div>
                <div style={{ fontWeight: "600", fontSize: "0.9rem" }}>
                  {r.title}
                </div>
                <div style={{ color: "#9ca3af", fontSize: "0.8rem",
                              marginTop: "3px", lineHeight: "1.5" }}>
                  {r.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Minimum Wages */}
      <div style={card}>
        <div style={{ fontWeight: "700", marginBottom: "14px", fontSize: "0.95rem" }}>
          💰 {t.wages_title || "Minimum wages 2025"}
        </div>
        {WAGES.map((w, i) => (
          <div key={w.state} style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", padding: "10px 0",
            borderBottom: i < WAGES.length - 1 ? "1px solid #1f2937" : "none"
          }}>
            <span style={{ fontSize: "0.88rem", color: "#d1d5db" }}>
              {w.flag} {w.state}
            </span>
            <span style={{ color: "#f97316", fontWeight: "700" }}>
              {w.amount}/hr
            </span>
          </div>
        ))}
      </div>

      {/* Report */}
      <div style={{
        ...card,
        background: "rgba(59,130,246,0.08)",
        border: "1px solid rgba(59,130,246,0.3)"
      }}>
        <div style={{ color: "#60a5fa", fontWeight: "700",
                      fontSize: "0.85rem", textTransform: "uppercase",
                      letterSpacing: "0.08em", marginBottom: "12px" }}>
          📞 {t.report_title || "Report a violation"}
        </div>
        <div style={{ color: "#f97316", fontWeight: "800",
                      fontSize: "1.8rem", marginBottom: "6px" }}>
          1-866-487-9243
        </div>
        <div style={{ color: "#9ca3af", fontSize: "0.82rem" }}>
          {t.report_free || "Free · Bilingual · Regardless of immigration status"}
        </div>
      </div>

      {/* Privacy */}
      <div style={card}>
        <div style={{ fontWeight: "700", marginBottom: "12px" }}>
          🔒 {t.privacy_title || "Your privacy in PaySnap"}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {privacy.map((item, i) => (
            <div key={i} style={{ display: "flex", gap: "10px",
                                  fontSize: "0.85rem", color: "#d1d5db" }}>
              <span style={{ color: "#4ade80" }}>✓</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
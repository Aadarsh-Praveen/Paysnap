const card = {
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: "12px",
    padding: "20px",
    marginBottom: "16px"
  };
  
  export default function Rights() {
    const wages = [
      { state: "California",  amount: "$16.50", flag: "🏖️" },
      { state: "Nueva York",  amount: "$16.00", flag: "🗽" },
      { state: "Illinois",    amount: "$14.00", flag: "🌾" },
      { state: "Florida",     amount: "$13.00", flag: "☀️" },
      { state: "Texas",       amount: "$7.25",  flag: "⭐" },
    ];
  
    const rights = [
      { icon: "💰", title: "Salario mínimo",
        desc: "Tu empleador DEBE pagarte al menos el mínimo de tu estado" },
      { icon: "⏰", title: "Tiempo extra",
        desc: "Más de 40 horas por semana = 1.5x tu tarifa normal" },
      { icon: "🛡️", title: "Sin represalias",
        desc: "Es ilegal despedirte por reportar violaciones de salario" },
      { icon: "📋", title: "Ley federal FLSA",
        desc: "Protege a todos los trabajadores en EE.UU." },
    ];
  
    return (
      <div>
  
        <div style={{ ...card }}>
          <div style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "6px" }}>
            Tus Derechos
          </div>
          <div style={{ color: "#9ca3af", fontSize: "0.82rem", marginBottom: "16px" }}>
            Sin importar tu estatus migratorio:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {rights.map((r) => (
              <div key={r.title} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <span style={{ fontSize: "1.4rem", flexShrink: 0 }}>{r.icon}</span>
                <div>
                  <div style={{ fontWeight: "600", fontSize: "0.9rem" }}>{r.title}</div>
                  <div style={{ color: "#9ca3af", fontSize: "0.8rem", marginTop: "3px",
                                lineHeight: "1.5" }}>
                    {r.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
  
        <div style={card}>
          <div style={{ fontWeight: "700", marginBottom: "14px", fontSize: "0.95rem" }}>
            💰 Salarios mínimos 2025
          </div>
          {wages.map((w, i) => (
            <div key={w.state} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 0",
              borderBottom: i < wages.length - 1 ? "1px solid #1f2937" : "none"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>{w.flag}</span>
                <span style={{ fontSize: "0.88rem", color: "#d1d5db" }}>{w.state}</span>
              </div>
              <span style={{ color: "#f97316", fontWeight: "700", fontSize: "0.95rem" }}>
                {w.amount}/hr
              </span>
            </div>
          ))}
        </div>
  
        <div style={{
          ...card,
          background: "rgba(59,130,246,0.08)",
          border: "1px solid rgba(59,130,246,0.3)"
        }}>
          <div style={{ color: "#60a5fa", fontWeight: "700", fontSize: "0.85rem",
                        textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
            📞 Reportar una violación
          </div>
          <div style={{ fontWeight: "600", marginBottom: "6px" }}>
            DOL Wage and Hour Division
          </div>
          <div style={{ color: "#f97316", fontWeight: "800", fontSize: "1.8rem",
                        marginBottom: "6px" }}>
            1-866-487-9243
          </div>
          <div style={{ color: "#9ca3af", fontSize: "0.82rem", lineHeight: "1.6" }}>
            ✓ Gratis<br />
            ✓ En español<br />
            ✓ Sin importar tu estatus migratorio<br />
            ✓ Confidencial
          </div>
        </div>
  
        <div style={card}>
          <div style={{ fontWeight: "700", marginBottom: "12px", fontSize: "0.95rem" }}>
            🔒 Tu privacidad en PaySnap
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {[
              "Cero datos en la nube — todo en tu dispositivo",
              "Sin cuenta ni contraseña requerida",
              "Sin telemetría ni rastreo",
              "Historial encriptado localmente",
            ].map((t) => (
              <div key={t} style={{ display: "flex", gap: "10px",
                                    fontSize: "0.85rem", color: "#d1d5db" }}>
                <span style={{ color: "#4ade80" }}>✓</span>
                <span>{t}</span>
              </div>
            ))}
          </div>
        </div>
  
      </div>
    );
  }
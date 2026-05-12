import { useState, useRef } from "react";
import { api } from "../api/client";

const STATES = ["TX", "CA", "NY", "FL", "IL"];

const card = {
  background: "#111827",
  border: "1px solid #1f2937",
  borderRadius: "12px",
  padding: "20px",
  marginBottom: "16px"
};

const label = {
  display: "block",
  fontSize: "0.78rem",
  color: "#9ca3af",
  marginBottom: "6px",
  fontWeight: "500",
  textTransform: "uppercase",
  letterSpacing: "0.05em"
};

const input = {
  width: "100%",
  background: "#1f2937",
  border: "1px solid #374151",
  borderRadius: "8px",
  padding: "12px 14px",
  color: "#f1f1f1",
  fontSize: "0.95rem",
  outline: "none",
  transition: "border-color 0.2s"
};

const btn = (color = "#f97316") => ({
  width: "100%",
  background: color,
  border: "none",
  borderRadius: "10px",
  padding: "14px",
  color: "white",
  fontWeight: "700",
  fontSize: "1rem",
  cursor: "pointer",
  transition: "opacity 0.2s",
  marginTop: "8px"
});

export default function Analyze() {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [employer, setEmployer] = useState("");
  const [regularHours, setRegularHours] = useState(0);
  const [overtimeHours, setOvertimeHours] = useState(0);
  const [hourlyRate, setHourlyRate] = useState(0);
  const [state, setState] = useState("TX");
  const [deductions, setDeductions] = useState([]);
  const [dedName, setDedName] = useState("");
  const [dedAmount, setDedAmount] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [letter, setLetter] = useState("");
  const [letterLoading, setLetterLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f) setFile(f);
  };

  const handleExtract = async () => {
    if (!file) return;
    setExtracting(true);
    setError("");
    try {
      const res = await api.extract(file);
      if (res.success) {
        const d = res.data;
        setEmployer(d.employer_name || "");
        setRegularHours(d.regular_hours || 0);
        setOvertimeHours(d.overtime_hours || 0);
        setHourlyRate(d.hourly_rate || 0);
        setState(d.state || "TX");
        setDeductions(d.deductions || []);
      } else {
        setError(res.error || "Error reading file");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setExtracting(false);
    }
  };

  const addDed = () => {
    if (dedName && dedAmount) {
      setDeductions([...deductions, { name: dedName, amount: parseFloat(dedAmount) }]);
      setDedName("");
      setDedAmount("");
    }
  };

  const handleAnalyze = async () => {
    if (!hourlyRate || hourlyRate <= 0) {
      setError("Por favor ingresa tu tarifa por hora.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setLetter("");
    try {
      const res = await api.analyze({ employer, regularHours, overtimeHours, hourlyRate, state, deductions });
      if (res.success) setResult(res.data);
      else setError(res.error || "Error en el análisis");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLetter = async () => {
    if (!result) return;
    setLetterLoading(true);
    try {
      const res = await api.demandLetter({
        employer, regularHours, overtimeHours, hourlyRate, state,
        totalOwed: result.total_money_owed,
        breakdown: result.breakdown,
        statute: result.statute
      });
      if (res.success) setLetter(res.data.letter);
    } catch (e) {
      setLetter("Error: " + e.message);
    } finally {
      setLetterLoading(false);
    }
  };

  return (
    <div>

      {/* Step 1 — Upload */}
      <div style={card}>
        <div style={{ fontSize: "0.7rem", color: "#f97316", fontWeight: "700",
                      textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>
          Paso 1
        </div>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "4px" }}>
          Sube tu recibo de pago
        </div>
        <div style={{ fontSize: "0.82rem", color: "#6b7280", marginBottom: "14px" }}>
          Acepta foto, PDF, Word o Excel
        </div>

        <input ref={fileRef} type="file"
               accept=".jpg,.jpeg,.png,.pdf,.docx,.xlsx"
               onChange={handleFile} style={{ display: "none" }} />

        <div
          onClick={() => fileRef.current?.click()}
          style={{
            border: "2px dashed " + (file ? "#f97316" : "#374151"),
            borderRadius: "10px",
            padding: "28px 16px",
            textAlign: "center",
            cursor: "pointer",
            transition: "border-color 0.2s",
            background: file ? "rgba(249,115,22,0.05)" : "transparent"
          }}
        >
          {file ? (
            <>
              <div style={{ fontSize: "2rem", marginBottom: "6px" }}>📄</div>
              <div style={{ color: "#f97316", fontWeight: "600", fontSize: "0.9rem" }}>
                {file.name}
              </div>
              <div style={{ color: "#6b7280", fontSize: "0.75rem", marginTop: "4px" }}>
                Toca para cambiar
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: "2.5rem", marginBottom: "8px" }}>📤</div>
              <div style={{ color: "#d1d5db", fontWeight: "600" }}>
                Toca aquí para subir tu recibo
              </div>
              <div style={{ color: "#6b7280", fontSize: "0.78rem", marginTop: "4px" }}>
                Foto · PDF · Word · Excel
              </div>
            </>
          )}
        </div>

        {file && (
          <button
            onClick={handleExtract}
            disabled={extracting}
            style={{ ...btn("#374151"), marginTop: "12px", opacity: extracting ? 0.6 : 1 }}
          >
            {extracting ? "⏳ Leyendo con Gemma 4..." : "📖 Leer recibo automáticamente"}
          </button>
        )}
      </div>

      {/* Step 2 — Form */}
      <div style={card}>
        <div style={{ fontSize: "0.7rem", color: "#f97316", fontWeight: "700",
                      textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "10px" }}>
          Paso 2
        </div>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "4px" }}>
          Verifica o ingresa tus datos
        </div>
        <div style={{ fontSize: "0.82rem", color: "#6b7280", marginBottom: "16px" }}>
          Si subiste archivo, revisa que los datos sean correctos
        </div>

        {/* Employer */}
        <div style={{ marginBottom: "14px" }}>
          <label style={label}>Nombre del empleador</label>
          <input style={input} type="text" value={employer}
                 onChange={e => setEmployer(e.target.value)}
                 placeholder="ABC Construction LLC" />
        </div>

        {/* Hours */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
          <div>
            <label style={label}>Horas regulares</label>
            <input style={input} type="number" value={regularHours}
                   onChange={e => setRegularHours(parseFloat(e.target.value) || 0)}
                   min="0" step="0.5" />
          </div>
          <div>
            <label style={label}>Horas extras en recibo</label>
            <input style={input} type="number" value={overtimeHours}
                   onChange={e => setOvertimeHours(parseFloat(e.target.value) || 0)}
                   min="0" step="0.5" />
          </div>
        </div>

        {/* Rate + State */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
          <div>
            <label style={label}>Tarifa por hora ($)</label>
            <input style={input} type="number" value={hourlyRate}
                   onChange={e => setHourlyRate(parseFloat(e.target.value) || 0)}
                   min="0" step="0.01" />
          </div>
          <div>
            <label style={label}>Estado</label>
            <select style={input} value={state} onChange={e => setState(e.target.value)}>
              {STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Deductions */}
        <div>
          <label style={label}>Deducciones del recibo</label>

          {deductions.map((d, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              background: "#1f2937", borderRadius: "8px", padding: "10px 12px",
              marginBottom: "8px"
            }}>
              <span style={{ fontSize: "0.88rem" }}>
                {d.name}:{" "}
                <span style={{ color: "#f97316", fontWeight: "600" }}>
                  ${Number(d.amount).toFixed(2)}
                </span>
              </span>
              <button
                onClick={() => setDeductions(deductions.filter((_, idx) => idx !== i))}
                style={{ background: "none", border: "none", color: "#ef4444",
                         cursor: "pointer", fontSize: "1rem", padding: "0 4px" }}
              >
                ✕
              </button>
            </div>
          ))}

          <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
            <input
              style={{ ...input, flex: 1, padding: "10px 12px", fontSize: "0.85rem" }}
              type="text" value={dedName}
              onChange={e => setDedName(e.target.value)}
              placeholder="Ej: TOOLS"
            />
            <input
              style={{ ...input, width: "90px", padding: "10px 12px", fontSize: "0.85rem" }}
              type="number" value={dedAmount}
              onChange={e => setDedAmount(e.target.value)}
              placeholder="75.00" min="0"
            />
            <button
              onClick={addDed}
              style={{
                background: "#1f2937", border: "1px solid #374151",
                borderRadius: "8px", padding: "10px 14px",
                color: "#f1f1f1", cursor: "pointer", fontSize: "1.1rem",
                whiteSpace: "nowrap"
              }}
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.4)",
          borderRadius: "10px", padding: "12px 16px",
          color: "#fca5a5", fontSize: "0.88rem", marginBottom: "16px"
        }}>
          ❌ {error}
        </div>
      )}

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={loading}
        style={{ ...btn(), opacity: loading ? 0.7 : 1, fontSize: "1.05rem", padding: "16px" }}
      >
        {loading ? "⏳ Analizando con Gemma 4..." : "🔍 Paso 3: Analizar mi recibo"}
      </button>

      {/* Results */}
      {result && (
        <div style={{ marginTop: "20px" }}>

          {/* Status Banner */}
          <div style={{
            borderRadius: "12px",
            padding: "16px 20px",
            marginBottom: "16px",
            background: result.has_violation
              ? "rgba(239,68,68,0.12)"
              : "rgba(34,197,94,0.12)",
            border: result.has_violation
              ? "1px solid rgba(239,68,68,0.4)"
              : "1px solid rgba(34,197,94,0.4)"
          }}>
            <div style={{ fontWeight: "700", fontSize: "1.05rem" }}>
              {result.has_violation
                ? `🚨 $${result.total_money_owed.toFixed(2)} potencialmente adeudado`
                : "✅ No detectamos problemas en este recibo"}
            </div>
          </div>

          {/* Spanish Explanation */}
          <div style={card}>
            <div style={{ color: "#f97316", fontWeight: "700", fontSize: "0.78rem",
                          textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "10px" }}>
              📝 Explicación en español
            </div>
            <div style={{ color: "#d1d5db", fontSize: "0.9rem",
                          lineHeight: "1.7", whiteSpace: "pre-wrap" }}>
              {result.explanation_es}
            </div>
          </div>

          {/* Math */}
          <div style={card}>
            <div style={{ color: "#f97316", fontWeight: "700", fontSize: "0.78rem",
                          textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "10px" }}>
              🧮 Cálculo matemático
            </div>
            <div style={{
              background: "#0a0a0f", borderRadius: "8px", padding: "14px",
              fontFamily: "monospace", fontSize: "0.85rem",
              color: "#a3e635", lineHeight: "1.8", whiteSpace: "pre-wrap"
            }}>
              {result.breakdown}
            </div>
          </div>

          {/* Illegal Deductions */}
          {result.illegal_deductions?.length > 0 && (
            <div style={{
              ...card,
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.3)"
            }}>
              <div style={{ color: "#f87171", fontWeight: "700", fontSize: "0.78rem",
                            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
                ⚠️ Deducciones ilegales detectadas
              </div>
              {result.illegal_deductions.map((d, i) => (
                <div key={i} style={{
                  borderBottom: "1px solid rgba(239,68,68,0.2)",
                  paddingBottom: "10px", marginBottom: "10px"
                }}>
                  <div style={{ fontWeight: "600", color: "#fca5a5", fontSize: "0.9rem" }}>
                    {d.name} — ${d.amount}
                  </div>
                  <div style={{ color: "#9ca3af", fontSize: "0.82rem", marginTop: "4px" }}>
                    {d.reason_es}
                  </div>
                  <div style={{ color: "#6b7280", fontSize: "0.75rem", marginTop: "3px",
                                fontFamily: "monospace" }}>
                    {d.statute}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Legal Aid */}
          {result.legal_aid?.length > 0 && (
            <div style={{
              ...card,
              background: "rgba(59,130,246,0.08)",
              border: "1px solid rgba(59,130,246,0.3)"
            }}>
              <div style={{ color: "#60a5fa", fontWeight: "700", fontSize: "0.78rem",
                            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>
                📞 Ayuda legal gratuita
              </div>
              {result.legal_aid.map((c, i) => (
                <div key={i} style={{ marginBottom: "14px" }}>
                  <div style={{ fontWeight: "600", fontSize: "0.9rem" }}>
                    {c.organization_name_es || c.organization_name}
                  </div>
                  <div style={{ color: "#f97316", fontWeight: "700",
                                fontSize: "1.1rem", marginTop: "4px" }}>
                    {c.phone}
                  </div>
                  <div style={{ color: "#9ca3af", fontSize: "0.78rem", marginTop: "2px" }}>
                    {c.phone_note_es}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Demand Letter */}
          {result.has_violation && (
            <div style={card}>
              <div style={{ color: "#f97316", fontWeight: "700", fontSize: "0.78rem",
                            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "10px" }}>
                ✉️ Carta de reclamo
              </div>
              <button
                onClick={handleLetter}
                disabled={letterLoading}
                style={{ ...btn("#1f2937"), border: "1px solid #374151",
                         opacity: letterLoading ? 0.6 : 1 }}
              >
                {letterLoading
                  ? "⏳ Generando carta..."
                  : "✉️ Generar carta formal para el empleador"}
              </button>
              {letter && (
                <div style={{
                  marginTop: "14px", background: "#0a0a0f",
                  borderRadius: "8px", padding: "16px",
                  fontFamily: "monospace", fontSize: "0.8rem",
                  color: "#d1d5db", whiteSpace: "pre-wrap",
                  lineHeight: "1.7", border: "1px solid #1f2937"
                }}>
                  {letter}
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
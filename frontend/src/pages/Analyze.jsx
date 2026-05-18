import { useState, useRef, useCallback } from "react";
import { api } from "../api/client";

const STATES = ["TX", "CA", "NY", "FL", "IL"];

const SURFACE = "#FFFFFF";
const BORDER  = "#E2E8F0";
const ORANGE  = "#F97316";
const ORANGE2 = "#EA580C";
const TEXT    = "#0F172A";
const MUTED   = "#64748B";
const LIGHT   = "#F1F5F9";

const card = {
  background: SURFACE, border: `1px solid ${BORDER}`,
  borderRadius: "16px", padding: "20px", marginBottom: "16px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
};
const inputStyle = {
  width: "100%", background: LIGHT, border: `1px solid ${BORDER}`,
  borderRadius: "10px", padding: "12px 14px", color: TEXT,
  fontSize: "0.95rem", outline: "none", boxSizing: "border-box",
};
const labelStyle = {
  display: "block", fontSize: "0.72rem", color: MUTED,
  marginBottom: "6px", fontWeight: "600",
  textTransform: "uppercase", letterSpacing: "0.06em",
};
const orangeBtn = {
  width: "100%",
  background: `linear-gradient(135deg, ${ORANGE}, ${ORANGE2})`,
  border: "none", borderRadius: "12px", padding: "16px",
  color: "white", fontWeight: "700", fontSize: "1rem", cursor: "pointer",
  boxShadow: "0 4px 14px rgba(249,115,22,0.3)",
};
const ghostBtn = {
  background: LIGHT, border: `1px solid ${BORDER}`,
  borderRadius: "10px", padding: "12px 16px",
  color: TEXT, fontWeight: "600", fontSize: "0.88rem", cursor: "pointer",
};

// Clean markdown asterisks from Gemma output
function cleanExplanation(text) {
  if (!text) return "";
  return text
    .replace(/\*\*([^*]+)\*\*/g, "$1")   // **bold** → plain
    .replace(/\*([^*]+)\*/g, "$1")        // *italic* → plain
    .replace(/^\s*[\*\-]\s+/gm, "• ")    // * item → • item
    .replace(/#{1,6}\s+/g, "")            // ### heading → plain
    .replace(/\n{3,}/g, "\n\n")           // max 2 newlines
    .trim();
}

export default function Analyze({ t, language, languageName }) {
  const fileRef = useRef(null);
  const [mode,          setMode]          = useState("options");
  const [voiceText,     setVoiceText]     = useState("");
  const [isListening,   setIsListening]   = useState(false);
  const [recRef,        setRecRef]        = useState(null);
  const [employer,      setEmployer]      = useState("");
  const [regularHours,  setRegularHours]  = useState("");
  const [overtimeHours, setOvertimeHours] = useState("0");
  const [hourlyRate,    setHourlyRate]    = useState("");
  const [state,         setState]         = useState("TX");
  const [deductions,    setDeductions]    = useState([]);
  const [dedName,       setDedName]       = useState("");
  const [dedAmount,     setDedAmount]     = useState("");
  const [extracting,    setExtracting]    = useState(false);
  const [loading,       setLoading]       = useState(false);
  const [result,        setResult]        = useState(null);
  const [letter,        setLetter]        = useState("");
  const [letterLoading, setLetterLoading] = useState(false);
  const [error,         setError]         = useState("");
  const [statusMsg,     setStatusMsg]     = useState("");

  const fillForm = useCallback((data) => {
    if (!data) return;
    if (data.employer_name)  setEmployer(data.employer_name);
    if (data.regular_hours)  setRegularHours(String(data.regular_hours));
    if (data.overtime_hours) setOvertimeHours(String(data.overtime_hours));
    if (data.hourly_rate)    setHourlyRate(String(data.hourly_rate));
    if (data.state)          setState(data.state);
    if (data.deductions?.length) setDeductions(data.deductions);
    setMode("form");
    setStatusMsg(t.upload_success || "✅ Data extracted! Please verify below.");
  }, [t]);

  const handleFile = async (file) => {
    if (!file) return;
    setExtracting(true); setError("");
    setStatusMsg(t.reading || "📄 Gemma 4 is reading your paystub...");
    try {
      const res = await api.extract(file);
      if (res.success && res.data) { fillForm(res.data); }
      else { setError(t.upload_error || "Could not read file. Please fill manually."); setMode("form"); setStatusMsg(""); }
    } catch (e) { setError(e.message); setMode("form"); setStatusMsg(""); }
    finally { setExtracting(false); }
  };

  const startVoice = () => {
    setError(""); setVoiceText("");
    const handle = api.transcribeAudio(
      (text, isFinal) => {
        setVoiceText(text);
        if (isFinal && text.trim()) { setIsListening(false); handleTextInput(text); }
      },
      (finalText) => { setIsListening(false); if (finalText.trim()) handleTextInput(finalText); },
      (err) => { setIsListening(false); setError("Voice error: " + err); }
    );
    if (handle) { setRecRef(handle); setIsListening(true); }
  };

  const stopVoice = () => {
    recRef?.stop?.();
    setIsListening(false);
    const text = recRef?.getTranscript?.() || voiceText;
    if (text.trim()) handleTextInput(text);
  };

  const handleTextInput = async (text) => {
    if (!text.trim()) return;
    setExtracting(true); setError("");
    setStatusMsg(t.reading || "🤖 Gemma 4 is understanding your situation...");
    try {
      const res = await api.extractFromText(text);
      if (res.success && res.data && (res.data.regular_hours > 0 || res.data.hourly_rate > 0)) {
        fillForm(res.data);
        setMode("form");
        const d = res.data;
        const analyzeRes = await api.analyze({
          employer: d.employer_name || "",
          regularHours: d.regular_hours || 0,
          overtimeHours: d.overtime_hours || 0,
          hourlyRate: d.hourly_rate || 0,
          state: d.state || "TX",
          deductions: d.deductions || [],
          language, languageName,
        });
        if (analyzeRes.success) { setResult(analyzeRes.data); setStatusMsg(""); }
      } else { setMode("form"); setStatusMsg(""); }
    } catch (e) { setMode("form"); setStatusMsg(""); }
    finally { setExtracting(false); }
  };

  const handleAnalyze = async () => {
    const rate = parseFloat(hourlyRate);
    const reg  = parseFloat(regularHours);
    if (!rate || rate <= 0 || !reg || reg <= 0) {
      setError(t.rate + "?"); return;
    }
    setLoading(true); setError(""); setResult(null); setLetter("");
    setStatusMsg(t.analyzing || "🔍 Analyzing with Gemma 4...");
    try {
      const res = await api.analyze({
        employer, regularHours: reg,
        overtimeHours: parseFloat(overtimeHours) || 0,
        hourlyRate: rate, state, deductions, language, languageName,
      });
      if (res.success) { setResult(res.data); setStatusMsg(""); }
      else setError(res.error || "Analysis failed");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleLetter = async () => {
    if (!result) return;
    setLetterLoading(true);
    try {
      const res = await api.demandLetter({
        employer, regularHours: parseFloat(regularHours)||0,
        overtimeHours: parseFloat(overtimeHours)||0,
        hourlyRate: parseFloat(hourlyRate)||0,
        state, totalOwed: result.total_money_owed,
        breakdown: result.breakdown, statute: result.statute,
      });
      if (res.success) setLetter(res.data.letter);
    } catch (e) { setLetter("Error: " + e.message); }
    finally { setLetterLoading(false); }
  };

  const addDed = () => {
    if (dedName && dedAmount) {
      setDeductions([...deductions, { name: dedName, amount: parseFloat(dedAmount) }]);
      setDedName(""); setDedAmount("");
    }
  };

  const Spinner = () => (
    <span style={{
      width:"14px", height:"14px",
      border:`2px solid ${ORANGE}`, borderTopColor:"transparent",
      borderRadius:"50%", animation:"spin 0.8s linear infinite",
      display:"inline-block", flexShrink:0,
    }} />
  );

  // ─── INPUT OPTIONS ───
  const renderOptions = () => (
    <div style={card}>
      <div style={{
        background: `linear-gradient(135deg, ${ORANGE}, ${ORANGE2})`,
        borderRadius:"12px", padding:"16px 20px", marginBottom:"20px",
      }}>
        <div style={{ fontSize:"1.2rem", fontWeight:"800", color:"white" }}>
          💼 {t.ask_paysnap || "Ask PaySnap"}
        </div>
        <div style={{ color:"rgba(255,255,255,0.85)", fontSize:"0.82rem", marginTop:"3px" }}>
          {t.ask_sub || "Upload, speak, or type — Gemma 4 does the rest"}
        </div>
      </div>

      <input ref={fileRef} type="file" accept="image/*,.pdf"
        onChange={e => handleFile(e.target.files[0])} style={{ display:"none" }} />

      <div style={{ display:"flex", flexDirection:"column", gap:"10px" }}>
        {/* Upload */}
        <button onClick={() => fileRef.current?.click()} style={{
          ...ghostBtn, display:"flex", alignItems:"center", gap:"12px",
          border:`1px solid ${ORANGE}`, color:ORANGE,
          background:"rgba(249,115,22,0.04)",
        }}>
          <span style={{ fontSize:"1.8rem" }}>📄</span>
          <div style={{ textAlign:"left" }}>
            <div style={{ fontWeight:"700", fontSize:"0.92rem" }}>
              {t.upload_title || "Upload Paystub"}
            </div>
            <div style={{ fontSize:"0.72rem", color:MUTED, marginTop:"2px" }}>
              {t.upload_sub || "Photo, PDF, or image — Gemma 4 reads it automatically"}
            </div>
          </div>
        </button>

        {/* Voice */}
        <button onClick={() => setMode("voice")} style={{
          ...ghostBtn, display:"flex", alignItems:"center", gap:"12px",
        }}>
          <span style={{ fontSize:"1.8rem" }}>🎤</span>
          <div style={{ textAlign:"left" }}>
            <div style={{ fontWeight:"700", fontSize:"0.92rem" }}>
              {t.speak_title || "Speak your situation"}
            </div>
            <div style={{ fontSize:"0.72rem", color:MUTED, marginTop:"2px" }}>
              {t.speak_sub || "Talk in Hindi, Spanish, or any language"}
            </div>
          </div>
        </button>

        {/* Type */}
        <button onClick={() => setMode("text")} style={{
          ...ghostBtn, display:"flex", alignItems:"center", gap:"12px",
        }}>
          <span style={{ fontSize:"1.8rem" }}>✏️</span>
          <div style={{ textAlign:"left" }}>
            <div style={{ fontWeight:"700", fontSize:"0.92rem" }}>
              {t.describe_title || "Describe your situation"}
            </div>
            <div style={{ fontSize:"0.72rem", color:MUTED, marginTop:"2px" }}>
              {t.describe_sub || '"I worked 52 hours at $23/hr in Texas..."'}
            </div>
          </div>
        </button>

        {/* Manual form */}
        <button onClick={() => setMode("form")} style={{
          ...ghostBtn, display:"flex", alignItems:"center", gap:"12px",
          background:"transparent", border:`1px dashed ${BORDER}`,
        }}>
          <span style={{ fontSize:"1.8rem" }}>📋</span>
          <div style={{ textAlign:"left" }}>
            <div style={{ fontWeight:"700", fontSize:"0.92rem" }}>
              {t.manual_title || "Fill form manually"}
            </div>
            <div style={{ fontSize:"0.72rem", color:MUTED, marginTop:"2px" }}>
              {t.manual_sub || "Enter hours, rate, and deductions directly"}
            </div>
          </div>
        </button>
      </div>
    </div>
  );

  // ─── VOICE ───
  const renderVoice = () => (
    <div style={card}>
      <button onClick={() => { setMode("options"); setVoiceText(""); setIsListening(false); recRef?.stop?.(); }}
        style={{ ...ghostBtn, marginBottom:"16px", padding:"8px 14px", fontSize:"0.82rem" }}>
        ← {t.back || "Back"}
      </button>
      <div style={{ textAlign:"center", padding:"16px 0" }}>
        <div onClick={isListening ? stopVoice : startVoice} style={{
          width:"90px", height:"90px", borderRadius:"50%",
          background: isListening ? `linear-gradient(135deg, ${ORANGE}, ${ORANGE2})` : LIGHT,
          border: isListening ? "none" : `2px solid ${BORDER}`,
          display:"flex", alignItems:"center", justifyContent:"center",
          fontSize:"2.8rem", margin:"0 auto 16px", cursor:"pointer",
          boxShadow: isListening
            ? "0 0 0 14px rgba(249,115,22,0.15),0 0 0 28px rgba(249,115,22,0.07)" : "none",
          animation: isListening ? "pulse 1.5s ease-in-out infinite" : "none",
          transition:"all 0.3s",
        }}>🎤</div>
        <div style={{ fontWeight:"700", fontSize:"1rem", marginBottom:"6px", color:TEXT }}>
          {isListening
            ? (t.listening || "Listening... tap to stop")
            : (t.tap_mic || "Tap microphone to speak")}
        </div>
        <div style={{ color:MUTED, fontSize:"0.82rem", lineHeight:"1.5" }}>
          {t.speak_sub || "Speak in your language — Hindi, Spanish, English"}
        </div>
        {voiceText && (
          <div style={{
            margin:"16px auto 0", background:LIGHT, borderRadius:"12px",
            padding:"14px 16px", fontSize:"0.9rem", color:TEXT,
            textAlign:"left", lineHeight:"1.6", maxWidth:"420px",
            border:`1px solid ${BORDER}`,
          }}>
            <div style={{ fontSize:"0.7rem", color:MUTED, marginBottom:"6px", fontWeight:"600" }}>
              {t.transcript || "TRANSCRIPT"}
            </div>
            "{voiceText}"
          </div>
        )}
        <div style={{ marginTop:"20px", display:"flex", gap:"10px", justifyContent:"center" }}>
          {!isListening ? (
            <>
              <button onClick={startVoice} style={{ ...orangeBtn, width:"auto", padding:"12px 24px" }}>
                🎤 {t.start_speaking || "Start Speaking"}
              </button>
              {voiceText && (
                <button onClick={() => handleTextInput(voiceText)} style={ghostBtn}>
                  {t.use_this || "Use This"} →
                </button>
              )}
            </>
          ) : (
            <button onClick={stopVoice} style={{
              ...ghostBtn, border:`1px solid ${ORANGE}`, color:ORANGE,
            }}>
              ⏹ {t.stop_analyze || "Stop & Analyze"}
            </button>
          )}
        </div>
      </div>
    </div>
  );

  // ─── TEXT ───
  const renderText = () => (
    <div style={card}>
      <button onClick={() => setMode("options")}
        style={{ ...ghostBtn, marginBottom:"16px", padding:"8px 14px", fontSize:"0.82rem" }}>
        ← {t.back || "Back"}
      </button>
      <div style={{ fontSize:"0.72rem", color:ORANGE, fontWeight:"700",
        textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"8px" }}>
        🤖 {t.describe_title || "Describe Your Situation"}
      </div>
      <div style={{ fontSize:"0.82rem", color:MUTED, marginBottom:"12px" }}>
        {t.describe_hint || "Type in your language. Gemma 4 extracts the details automatically."}
      </div>
      <div style={{ display:"flex", gap:"6px", flexWrap:"wrap", marginBottom:"12px" }}>
        {[
          { flag:"🇺🇸", text:"I worked 52 hours at $23/hr in Texas. They deducted $75 for tools." },
          { flag:"🇲🇽", text:"Trabajé 52 horas a $23/hora en Texas. Me descontaron $75 por herramientas." },
          { flag:"🇮🇳", text:"मैंने Texas में 52 घंटे $23/घंटा पर काम किया।" },
          { flag:"🇨🇳", text:"我在德克萨斯州工作了52小时，每小时23美元。" },
        ].map((ex, i) => (
          <button key={i} onClick={() => {
            const el = document.getElementById("situation-input");
            if (el) el.value = ex.text;
          }} style={{
            background:LIGHT, border:`1px solid ${BORDER}`,
            borderRadius:"20px", padding:"4px 12px",
            fontSize:"0.75rem", cursor:"pointer", color:TEXT,
          }}>
            {ex.flag} {t.example || "Example"}
          </button>
        ))}
      </div>
      <textarea id="situation-input" rows={4}
        placeholder={t.describe_placeholder || "I worked 52 hours this week in Texas at $23/hour..."}
        style={{ ...inputStyle, resize:"none", lineHeight:"1.6", marginBottom:"12px" }} />
      <button onClick={() => {
        const val = document.getElementById("situation-input")?.value;
        if (val?.trim()) handleTextInput(val);
      }} style={orangeBtn} disabled={extracting}>
        {extracting
          ? <span style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"10px" }}>
              <Spinner /> {t.reading || "Gemma 4 is reading..."}
            </span>
          : `🤖 ${t.describe_btn || "Let Gemma 4 Analyze"}`
        }
      </button>
    </div>
  );

  // ─── FORM ───
  const renderForm = () => (
    <div>
      <button onClick={() => setMode("options")}
        style={{ ...ghostBtn, width:"100%", marginBottom:"12px", fontSize:"0.82rem" }}>
        ← {t.change_input || "Change Input Method"}
      </button>
      <div style={card}>
        <div style={{ fontSize:"0.72rem", color:ORANGE, fontWeight:"700",
          textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"8px" }}>
          {t.step2 || "Step 2"} — {t.form_title || "Verify Your Details"}
        </div>
        <div style={{ fontSize:"0.82rem", color:MUTED, marginBottom:"16px" }}>
          {t.form_sub || "Check the data is correct, then click Analyze"}
        </div>

        <div style={{ marginBottom:"14px" }}>
          <label style={labelStyle}>{t.employer_label || "Employer"}</label>
          <input style={inputStyle} type="text" value={employer}
            onChange={e => setEmployer(e.target.value)}
            placeholder={t.employer_placeholder || "ABC Construction LLC"} />
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"12px", marginBottom:"14px" }}>
          <div>
            <label style={labelStyle}>{t.reg_hours || "Regular Hours"}</label>
            <input style={inputStyle} type="number" value={regularHours}
              onChange={e => setRegularHours(e.target.value)} placeholder="40" min="0" step="0.5" />
          </div>
          <div>
            <label style={labelStyle}>{t.ot_hours || "OT Hours"}</label>
            <input style={inputStyle} type="number" value={overtimeHours}
              onChange={e => setOvertimeHours(e.target.value)} placeholder="0" min="0" step="0.5" />
          </div>
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"12px", marginBottom:"14px" }}>
          <div>
            <label style={labelStyle}>{t.rate || "Hourly Rate ($)"}</label>
            <input style={inputStyle} type="number" value={hourlyRate}
              onChange={e => setHourlyRate(e.target.value)} placeholder="15.00" min="0" step="0.01" />
          </div>
          <div>
            <label style={labelStyle}>{t.state_label || "State"}</label>
            <select style={inputStyle} value={state} onChange={e => setState(e.target.value)}>
              {STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label style={labelStyle}>{t.deductions_label || "Deductions"}</label>
          {deductions.map((d, i) => (
            <div key={i} style={{
              display:"flex", justifyContent:"space-between", alignItems:"center",
              background:LIGHT, borderRadius:"8px", padding:"10px 12px", marginBottom:"8px",
            }}>
              <span style={{ fontSize:"0.88rem" }}>
                {d.name}: <span style={{ color:ORANGE, fontWeight:"600" }}>
                  ${Number(d.amount).toFixed(2)}
                </span>
              </span>
              <button onClick={() => setDeductions(deductions.filter((_,idx) => idx !== i))}
                style={{ background:"none", border:"none", color:"#ef4444", cursor:"pointer" }}>
                ✕
              </button>
            </div>
          ))}
          <div style={{ display:"flex", gap:"8px", marginTop:"8px" }}>
            <input style={{ ...inputStyle, flex:1, padding:"10px 12px", fontSize:"0.85rem" }}
              type="text" value={dedName} onChange={e => setDedName(e.target.value)}
              placeholder={t.ded_placeholder || "e.g. TOOLS"} />
            <input style={{ ...inputStyle, width:"90px", padding:"10px 12px", fontSize:"0.85rem" }}
              type="number" value={dedAmount} onChange={e => setDedAmount(e.target.value)}
              placeholder="75.00" min="0" />
            <button onClick={addDed} style={{
              background:LIGHT, border:`1px solid ${BORDER}`,
              borderRadius:"8px", padding:"10px 14px", color:TEXT, cursor:"pointer", fontSize:"1.1rem",
            }}>+</button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          background:"rgba(239,68,68,0.07)", border:"1px solid rgba(239,68,68,0.25)",
          borderRadius:"10px", padding:"12px 16px",
          color:"#dc2626", fontSize:"0.88rem", marginBottom:"12px",
        }}>❌ {error}</div>
      )}

      <button onClick={handleAnalyze} disabled={loading}
        style={{ ...orangeBtn, opacity: loading ? 0.7 : 1, fontSize:"1.05rem" }}>
        {loading
          ? <span style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"10px" }}>
              <Spinner /> {t.analyzing || "Analyzing with Gemma 4..."}
            </span>
          : `🔍 ${t.analyze_btn || "Analyze My Paystub"}`
        }
      </button>
    </div>
  );

  // ─── RESULTS ───
  const renderResults = () => (
    <div style={{ marginTop:"20px" }}>
      {/* Banner */}
      <div style={{
        borderRadius:"16px", padding:"20px", marginBottom:"16px",
        background: result.has_violation ? "rgba(249,115,22,0.06)" : "rgba(34,197,94,0.06)",
        border: result.has_violation ? "1px solid rgba(249,115,22,0.3)" : "1px solid rgba(34,197,94,0.3)",
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:"16px" }}>
          <div style={{
            width:"56px", height:"56px", borderRadius:"14px",
            background: result.has_violation ? "rgba(249,115,22,0.12)" : "rgba(34,197,94,0.12)",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:"1.8rem", flexShrink:0,
          }}>
            {result.has_violation ? "🚨" : "✅"}
          </div>
          <div>
            <div style={{
              fontSize:"0.72rem", fontWeight:"700", textTransform:"uppercase",
              letterSpacing:"0.1em",
              color: result.has_violation ? "#dc2626" : "#16a34a", marginBottom:"4px",
            }}>
              {result.has_violation ? "VIOLATION DETECTED" : "NO ISSUES FOUND"}
            </div>
            {result.has_violation && (
              <>
                <div style={{ fontSize:"2.2rem", fontWeight:"800", color:ORANGE, lineHeight:"1" }}>
                  ${result.total_money_owed.toFixed(2)}
                </div>
                <div style={{ fontSize:"0.82rem", color:MUTED, marginTop:"2px" }}>
                  {t.violation_found || "potentially owed"}
                </div>
              </>
            )}
            {!result.has_violation && (
              <div style={{ fontSize:"0.95rem", color:"#16a34a", fontWeight:"600" }}>
                {t.no_violation || "No issues detected"}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Explanation — clean formatted */}
      <div style={card}>
        <div style={{ fontSize:"0.72rem", color:ORANGE, fontWeight:"700",
          textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"12px" }}>
          💬 {t.explanation_title || "AI Explanation"}
        </div>
        <div style={{ color:TEXT, fontSize:"0.9rem", lineHeight:"1.8" }}>
          {cleanExplanation(result.explanation_es)
            .split("\n")
            .map((line, i) => {
              if (!line.trim()) return <div key={i} style={{ height:"8px" }} />;
              const isBullet = line.startsWith("• ");
              return (
                <div key={i} style={{
                  display:"flex", gap: isBullet ? "8px" : "0",
                  marginBottom: isBullet ? "6px" : "0",
                  paddingLeft: isBullet ? "4px" : "0",
                }}>
                  {isBullet && (
                    <span style={{ color:ORANGE, fontWeight:"700", flexShrink:0 }}>•</span>
                  )}
                  <span>{isBullet ? line.substring(2) : line}</span>
                </div>
              );
            })
          }
        </div>
      </div>

      {/* Math */}
      {result.breakdown && (
        <div style={card}>
          <div style={{ fontSize:"0.72rem", color:ORANGE, fontWeight:"700",
            textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"12px" }}>
            🧮 {t.math_title || "Math Breakdown"}
          </div>
          <div style={{
            background:"#0F172A", borderRadius:"10px", padding:"16px",
            fontFamily:"monospace", fontSize:"0.85rem",
            color:"#4ade80", lineHeight:"1.8", whiteSpace:"pre-wrap",
          }}>
            {result.breakdown}
          </div>
        </div>
      )}

      {/* Illegal Deductions */}
      {result.illegal_deductions?.length > 0 && (
        <div style={{
          ...card, background:"rgba(239,68,68,0.04)",
          border:"1px solid rgba(239,68,68,0.2)",
        }}>
          <div style={{ fontSize:"0.72rem", color:"#dc2626", fontWeight:"700",
            textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"12px" }}>
            ⚠️ {t.illegal_ded_title || "Illegal Deductions"}
          </div>
          {result.illegal_deductions.map((d, i) => (
            <div key={i} style={{
              borderBottom: i < result.illegal_deductions.length-1
                ? "1px solid rgba(239,68,68,0.15)" : "none",
              paddingBottom:"10px", marginBottom:"10px",
            }}>
              <div style={{ fontWeight:"700", color:"#dc2626", fontSize:"0.92rem" }}>
                {d.name} — ${d.amount}
              </div>
              <div style={{ color:MUTED, fontSize:"0.82rem", marginTop:"4px" }}>
                {cleanExplanation(d.reason_es)}
              </div>
              <div style={{ color:"#94a3b8", fontSize:"0.72rem", marginTop:"3px", fontFamily:"monospace" }}>
                {d.statute}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legal Aid */}
      {result.legal_aid?.length > 0 && (
        <div style={{
          ...card, background:"rgba(59,130,246,0.04)",
          border:"1px solid rgba(59,130,246,0.2)",
        }}>
          <div style={{ fontSize:"0.72rem", color:"#2563eb", fontWeight:"700",
            textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"12px" }}>
            📞 {t.legal_aid_title || "Free Legal Help"}
          </div>
          {result.legal_aid.map((c, i) => (
            <div key={i} style={{ marginBottom: i < result.legal_aid.length-1 ? "16px" : 0 }}>
              <div style={{ fontWeight:"600", fontSize:"0.88rem", color:TEXT }}>
                {c.organization_name_es || c.organization_name}
              </div>
              <div style={{ color:ORANGE, fontWeight:"800", fontSize:"1.3rem", marginTop:"4px" }}>
                {c.phone}
              </div>
              <div style={{ color:MUTED, fontSize:"0.75rem", marginTop:"2px" }}>
                {c.phone_note_es}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Demand Letter */}
      {result.has_violation && (
        <div style={card}>
          <div style={{ fontSize:"0.72rem", color:ORANGE, fontWeight:"700",
            textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"12px" }}>
            ✉️ {t.letter_title || "Demand Letter"}
          </div>
          <button onClick={handleLetter} disabled={letterLoading}
            style={{ ...ghostBtn, width:"100%", opacity: letterLoading ? 0.6 : 1 }}>
            {letterLoading
              ? (t.letter_loading || "Generating...")
              : `✉️ ${t.letter_btn || "Generate Demand Letter"}`}
          </button>
          {letter && (
            <div style={{
              marginTop:"14px", background:"#0F172A", borderRadius:"10px",
              padding:"16px", fontFamily:"monospace", fontSize:"0.78rem",
              color:"#d1d5db", whiteSpace:"pre-wrap", lineHeight:"1.7",
            }}>
              {cleanExplanation(letter)}
            </div>
          )}
        </div>
      )}

      <button onClick={() => { setResult(null); setMode("options"); setStatusMsg(""); }}
        style={{ ...ghostBtn, width:"100%", marginTop:"8px" }}>
        ← {t.analyze_another || "Analyze Another Paystub"}
      </button>
    </div>
  );

  return (
    <div style={{ color:TEXT }}>
      {statusMsg && (
        <div style={{
          background:"rgba(249,115,22,0.07)", border:`1px solid rgba(249,115,22,0.2)`,
          borderRadius:"12px", padding:"12px 16px", color:ORANGE2,
          fontSize:"0.88rem", marginBottom:"16px", textAlign:"center",
          display:"flex", alignItems:"center", justifyContent:"center", gap:"8px",
        }}>
          {(extracting || loading) && <Spinner />}
          {statusMsg}
        </div>
      )}

      {mode === "options" && renderOptions()}
      {mode === "voice"   && renderVoice()}
      {mode === "text"    && renderText()}
      {mode === "form"    && renderForm()}
      {result             && renderResults()}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse {
          0%,100% { box-shadow:0 0 0 14px rgba(249,115,22,0.15),0 0 0 28px rgba(249,115,22,0.07); }
          50%      { box-shadow:0 0 0 18px rgba(249,115,22,0.2),0 0 0 36px rgba(249,115,22,0.05); }
        }
      `}</style>
    </div>
  );
}
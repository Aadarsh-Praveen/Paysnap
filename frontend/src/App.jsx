import { useState, Component } from "react";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import Rights from "./pages/Rights";
import { LANGUAGES } from "./data/languages";
import { api } from "./api/client";

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding:"24px", background:"#F8FAFC", minHeight:"100vh" }}>
          <div style={{ color:"#f97316", fontWeight:"700", marginBottom:"8px" }}>
            ⚠️ Something went wrong
          </div>
          <pre style={{
            color:"#dc2626", fontSize:"0.75rem", whiteSpace:"pre-wrap",
            background:"#fff", padding:"12px", borderRadius:"8px",
            border:"1px solid #fee2e2"
          }}>
            {this.state.error?.toString()}
          </pre>
          <button
            onClick={() => { this.setState({ hasError:false, error:null }); window.location.reload(); }}
            style={{
              marginTop:"16px", background:"#f97316", border:"none",
              borderRadius:"8px", padding:"10px 20px", color:"white", cursor:"pointer"
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const EN_FALLBACK = {
  // ── Core ──
  tagline: "Your paystub. Your rights. On your phone.",
  disclaimer: "PaySnap helps you understand your paystub. Not legal advice. Your data never leaves your device.",
  tab_analyze: "Analyze", tab_history: "History", tab_rights: "Rights",
  step1: "Step 1", step2: "Step 2", step3: "Step 3",

  // ── Input options ──
  ask_paysnap: "Ask PaySnap",
  ask_sub: "Upload, speak, or type — Gemma 4 does the rest",
  speak_title: "Speak your situation",
  speak_sub: "Talk in Hindi, Spanish, or any language",
  describe_title: "Describe your situation",
  describe_sub: '"I worked 52 hours at $23/hr in Texas..."',
  describe_hint: "Type in your language. Gemma 4 extracts details automatically.",
  describe_placeholder: "I worked 52 hours this week in Texas at $23/hour...",
  describe_btn: "Let Gemma 4 Analyze",
  manual_title: "Fill form manually",
  manual_sub: "Enter hours, rate, and deductions directly",
  back: "Back",
  change_input: "Change Input Method",
  example: "Example",
  listening: "Listening... tap to stop",
  tap_mic: "Tap microphone to speak",
  transcript: "TRANSCRIPT",
  start_speaking: "Start Speaking",
  use_this: "Use This",
  stop_analyze: "Stop & Analyze",
  analyze_another: "Analyze Another Paystub",
  upload_success: "✅ Data extracted! Please verify below.",
  upload_error: "Could not read file. Please fill manually.",

  // ── Upload ──
  upload_title: "Upload Paystub",
  upload_sub: "Photo, PDF, or image — Gemma 4 reads it automatically",
  upload_tap: "Tap here to upload your paystub",
  upload_formats: "Photo · PDF · Word · Excel",
  upload_change: "Tap to change",
  read_btn: "Read paystub automatically",
  reading: "Reading with Gemma 4...",

  // ── Form ──
  form_title: "Verify or enter your data",
  form_sub: "If you uploaded a file, check the data is correct",
  employer_label: "Employer name",
  employer_placeholder: "ABC Construction LLC",
  reg_hours: "Regular hours",
  ot_hours: "Overtime hours on stub",
  rate: "Hourly rate ($)",
  state_label: "State",
  deductions_label: "Paystub deductions",
  ded_placeholder: "e.g. TOOLS",
  amount_placeholder: "75.00",
  analyze_btn: "Analyze my paystub",
  analyzing: "Analyzing with Gemma 4...",

  // ── Results ──
  violation_found: "potentially owed",
  no_violation: "No issues detected in this paystub",
  explanation_title: "Explanation",
  math_title: "Math breakdown",
  illegal_ded_title: "Illegal deductions detected",
  legal_aid_title: "Free legal help",
  letter_title: "Demand letter",
  letter_btn: "Generate formal letter to employer",
  letter_loading: "Generating letter...",

  // ── History ──
  history_title: "Your paystub history",
  history_sub: "Saved locally on your device, encrypted",
  history_summary: "{count} paystubs analyzed · {violations} violations found · {total} total potential",
  refresh_btn: "Refresh",
  export_btn: "Export for attorney",
  no_history: "No paystubs analyzed yet.\nUpload your first paystub to begin.",

  // ── Rights ──
  rights_title: "Your Rights",
  rights_sub: "Regardless of immigration status:",
  wages_title: "Minimum wages 2025",
  report_title: "Report a violation",
  report_free: "Free · Bilingual · Regardless of immigration status",
  privacy_title: "Your privacy in PaySnap",
  privacy_1: "Zero cloud data — everything on your device",
  privacy_2: "No account or password required",
  privacy_3: "No telemetry or tracking",
  privacy_4: "History encrypted locally",
  right_1_title: "Minimum wage",
  right_1_desc: "Your employer MUST pay at least the state minimum wage",
  right_2_title: "Overtime",
  right_2_desc: "Over 40 hours/week = 1.5x your regular rate",
  right_3_title: "No retaliation",
  right_3_desc: "Illegal to fire you for reporting wage violations",
  right_4_title: "Federal FLSA Law",
  right_4_desc: "Protects all workers in the United States",
};

const BG      = "#F8FAFC";
const SURFACE = "#FFFFFF";
const BORDER  = "#E2E8F0";
const ORANGE  = "#F97316";
const TEXT    = "#0F172A";
const MUTED   = "#64748B";
const LIGHT   = "#F1F5F9";

function AppContent() {
  const [screen,       setScreen]       = useState("picker");
  const [language,     setLanguage]     = useState(null);
  const [langName,     setLangName]     = useState("");
  const [translations, setTranslations] = useState(EN_FALLBACK);
  const [tab,          setTab]          = useState("analyze");

  const handleSelectLanguage = async (lang) => {
    if (lang.code === "en") {
      setLanguage(lang.code);
      setLangName(lang.name);
      setTranslations({ ...EN_FALLBACK });
      setScreen("app");
      return;
    }

    // Check localStorage cache first — instant load
    const cacheKey = `paysnap_ui_${lang.code}`;
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        setLanguage(lang.code);
        setLangName(lang.name);
        setTranslations({ ...EN_FALLBACK, ...parsed });
        setScreen("app");
        return;
      }
    } catch (e) {}

    setLangName(lang.name);
    setScreen("translating");

    try {
      const res = await api.translateUI(lang.code, lang.name, EN_FALLBACK);
      if (res.success && res.data?.translations) {
        setTranslations({ ...EN_FALLBACK, ...res.data.translations });
      } else {
        setTranslations({ ...EN_FALLBACK });
      }
    } catch (e) {
      console.error("Translation error:", e);
      setTranslations({ ...EN_FALLBACK });
    }

    setLanguage(lang.code);
    setScreen("app");
  };

  // ── Language Picker ──
  if (screen === "picker") {
    return (
      <div style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg, #fff7ed 0%, #F8FAFC 40%, #eff6ff 100%)",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "24px 16px",
      }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            width: "88px", height: "88px",
            background: "linear-gradient(135deg, #fff7ed, #fed7aa)",
            borderRadius: "50%", display: "flex",
            alignItems: "center", justifyContent: "center",
            fontSize: "3rem", margin: "0 auto 16px",
            border: "2px solid #fed7aa",
            boxShadow: "0 8px 24px rgba(249,115,22,0.15)",
          }}>💼</div>
          <div style={{ fontSize: "2.4rem", fontWeight: "800", color: ORANGE }}>
            PaySnap
          </div>
          <div style={{ color: MUTED, fontSize: "0.82rem", marginTop: "6px" }}>
            AI Wage Theft Detector · Powered by Gemma 4
          </div>
          <div style={{ color: "#94a3b8", fontSize: "0.75rem", marginTop: "4px" }}>
            Paystub · Recibo · 工资单 · Fiş Salè
          </div>
        </div>

        <div style={{
          fontSize: "0.78rem", fontWeight: "700", color: MUTED,
          textTransform: "uppercase", letterSpacing: "0.08em",
          marginBottom: "6px", textAlign: "center",
        }}>
          Choose your language
        </div>
        <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: "20px" }}>
          Elige tu idioma · 选择语言 · भाषा चुनें
        </div>

        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: "10px", width: "100%", maxWidth: "400px",
        }}>
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              onClick={() => handleSelectLanguage(lang)}
              style={{
                background: SURFACE, border: `1px solid ${BORDER}`,
                borderRadius: "14px", padding: "16px 8px",
                color: TEXT, cursor: "pointer", textAlign: "center",
                transition: "all 0.15s",
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.border = `1px solid ${ORANGE}`;
                e.currentTarget.style.background = "#fff7ed";
                e.currentTarget.style.transform = "scale(1.03)";
                e.currentTarget.style.boxShadow = "0 4px 14px rgba(249,115,22,0.15)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.border = `1px solid ${BORDER}`;
                e.currentTarget.style.background = SURFACE;
                e.currentTarget.style.transform = "scale(1)";
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.04)";
              }}
            >
              <div style={{ fontSize: "2rem", marginBottom: "6px" }}>{lang.flag}</div>
              <div style={{ fontSize: "0.8rem", fontWeight: "600" }}>{lang.name}</div>
            </button>
          ))}
        </div>

        <div style={{ marginTop: "24px", fontSize: "0.72rem", color: "#94a3b8" }}>
          🔒 No account needed · Sin cuenta · 无需账户
        </div>
      </div>
    );
  }

  // ── Translating Spinner ──
  if (screen === "translating") {
    return (
      <div style={{
        minHeight: "100vh", background: BG,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "16px",
      }}>
        <div style={{
          width: "72px", height: "72px",
          background: "linear-gradient(135deg, #fff7ed, #fed7aa)",
          borderRadius: "50%", display: "flex",
          alignItems: "center", justifyContent: "center", fontSize: "2.2rem",
        }}>💼</div>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", color: ORANGE }}>
          PaySnap
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", color: MUTED }}>
          <span style={{
            display: "inline-block", width: "18px", height: "18px",
            border: `2px solid ${ORANGE}`, borderTopColor: "transparent",
            borderRadius: "50%", animation: "spin 0.8s linear infinite",
          }} />
          Translating to {langName}...
        </div>
        <div style={{
          color: "#94a3b8", fontSize: "0.78rem",
          textAlign: "center", maxWidth: "260px", lineHeight: "1.6",
          background: SURFACE, border: `1px solid ${BORDER}`,
          borderRadius: "12px", padding: "12px 16px",
        }}>
          Gemma 4 is translating the UI into {langName}.
          <br />Takes about 60 seconds · Cached after first run.
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Main App ──
  const currentLang = LANGUAGES.find(l => l.code === language);

  return (
    <div style={{ minHeight: "100vh", background: BG, color: TEXT }}>

      {/* Header */}
      <div style={{
        background: SURFACE,
        borderBottom: `1px solid ${ORANGE}`,
        padding: "14px 16px 10px",
        textAlign: "center",
        boxShadow: "0 2px 8px rgba(249,115,22,0.08)",
      }}>
        <div style={{
          display: "flex", alignItems: "center",
          justifyContent: "center", gap: "10px", marginBottom: "4px",
        }}>
          <span style={{ fontSize: "1.5rem", fontWeight: "800", color: ORANGE }}>
            💼 PaySnap
          </span>
          <button
            onClick={() => {
              setScreen("picker");
              setLanguage(null);
              setTranslations(EN_FALLBACK);
            }}
            style={{
              background: LIGHT, border: `1px solid ${BORDER}`,
              borderRadius: "20px", padding: "4px 10px",
              color: MUTED, cursor: "pointer", fontSize: "0.75rem",
              display: "flex", alignItems: "center", gap: "4px",
            }}
          >
            {currentLang?.flag} {currentLang?.name} ↓
          </button>
        </div>
        <div style={{ color: MUTED, fontSize: "0.78rem" }}>
          {translations.tagline}
        </div>
        <div style={{
          marginTop: "8px",
          background: "rgba(251,191,36,0.08)",
          border: "1px solid rgba(251,191,36,0.25)",
          borderRadius: "8px", padding: "6px 12px",
          fontSize: "0.72rem", color: "#92400e",
          maxWidth: "500px", margin: "8px auto 0",
        }}>
          ⚖️ {translations.disclaimer}
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex",
        borderBottom: `1px solid ${BORDER}`,
        backgroundColor: SURFACE,
        position: "sticky", top: 0, zIndex: 10,
        boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
      }}>
        {[
          { id: "analyze", label: translations.tab_analyze },
          { id: "history", label: translations.tab_history },
          { id: "rights",  label: translations.tab_rights  },
        ].map(tb => (
          <button key={tb.id} onClick={() => setTab(tb.id)}
            style={{
              flex: 1, padding: "14px 8px", border: "none",
              background: "transparent", cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: tab === tb.id ? "700" : "400",
              color: tab === tb.id ? ORANGE : MUTED,
              borderBottom: tab === tb.id
                ? `2px solid ${ORANGE}` : "2px solid transparent",
              transition: "all 0.2s",
            }}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: "600px", margin: "0 auto", padding: "20px 16px 60px" }}>
        {tab === "analyze" && (
          <Analyze t={translations} language={language} languageName={langName} />
        )}
        {tab === "history" && <History t={translations} language={language} />}
        {tab === "rights"  && <Rights  t={translations} />}
      </div>

    </div>
  );
}

export default function App() {
  return <ErrorBoundary><AppContent /></ErrorBoundary>;
}
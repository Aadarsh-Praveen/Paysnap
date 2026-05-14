import { useState, Component } from "react";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import Rights from "./pages/Rights";
import { LANGUAGES } from "./data/languages";
import { api } from "./api/client";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: "24px", color: "white",
          background: "#0a0a0f", minHeight: "100vh"
        }}>
          <div style={{ color: "#f97316", fontWeight: "700", marginBottom: "8px" }}>
            ⚠️ Something went wrong
          </div>
          <pre style={{
            color: "#ef4444", fontSize: "0.75rem",
            whiteSpace: "pre-wrap", background: "#111827",
            padding: "12px", borderRadius: "8px"
          }}>
            {this.state.error?.toString()}
          </pre>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              marginTop: "16px", background: "#f97316",
              border: "none", borderRadius: "8px",
              padding: "10px 20px", color: "white", cursor: "pointer"
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
  tagline: "Your paystub. Your rights. On your phone.",
  disclaimer: "PaySnap helps you understand your paystub. Not legal advice. Your data never leaves your device.",
  tab_analyze: "Analyze",
  tab_history: "History",
  tab_rights: "Rights",
  step1: "Step 1",
  step2: "Step 2",
  step3: "Step 3",
  upload_title: "Upload your paystub",
  upload_sub: "Accepts photo, PDF, Word or Excel",
  upload_tap: "Tap here to upload your paystub",
  upload_formats: "Photo · PDF · Word · Excel",
  upload_change: "Tap to change",
  read_btn: "Read paystub automatically",
  reading: "Reading with Gemma 4...",
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
  violation_found: "potentially owed",
  no_violation: "No issues detected in this paystub",
  explanation_title: "Explanation",
  math_title: "Math breakdown",
  illegal_ded_title: "Illegal deductions detected",
  legal_aid_title: "Free legal help",
  letter_title: "Demand letter",
  letter_btn: "Generate formal letter to employer",
  letter_loading: "Generating letter...",
  history_title: "Your paystub history",
  history_sub: "Saved locally on your device, encrypted",
  refresh_btn: "Refresh",
  export_btn: "Export for attorney",
  no_history: "No paystubs analyzed yet.\nUpload your first paystub to begin.",
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

// screen: "picker" | "translating" | "app"
function AppContent() {
  const [screen, setScreen] = useState("picker");
  const [language, setLanguage] = useState(null);
  const [langName, setLangName] = useState("");
  const [translations, setTranslations] = useState(EN_FALLBACK);
  const [tab, setTab] = useState("analyze");

  const handleSelectLanguage = async (lang) => {
    if (lang.code === "en") {
      setLanguage(lang.code);
      setLangName(lang.name);
      setTranslations({ ...EN_FALLBACK });
      setScreen("app");
      return;
    }

    setLangName(lang.name);
    setScreen("translating");

    try {
      const res = await api.translateUI(lang.code, lang.name);

      if (res.success && res.data && res.data.translations) {
        const merged = { ...EN_FALLBACK, ...res.data.translations };
        setTranslations(merged);
        setLanguage(lang.code);
        setScreen("app");
      } else {
        setTranslations({ ...EN_FALLBACK });
        setLanguage(lang.code);
        setScreen("app");
      }
    } catch (e) {
      console.error("Translation error:", e);
      setTranslations({ ...EN_FALLBACK });
      setLanguage(lang.code);
      setScreen("app");
    }
  };

  // ── Language Picker ──
  if (screen === "picker") {
    return (
      <div style={{
        minHeight: "100vh", backgroundColor: "#0a0a0f",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "24px 16px"
      }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{ fontSize: "3.5rem", marginBottom: "8px" }}>💼</div>
          <div style={{ fontSize: "2.2rem", fontWeight: "800", color: "#fff" }}>
            PaySnap
          </div>
          <div style={{ color: "#6b7280", fontSize: "0.82rem", marginTop: "6px" }}>
            Paystub · Recibo · 工资单 · Fiş Salè
          </div>
        </div>

        <div style={{
          fontSize: "1.1rem", fontWeight: "700",
          color: "#f1f1f1", marginBottom: "6px", textAlign: "center"
        }}>
          Choose your language
        </div>
        <div style={{
          fontSize: "0.8rem", color: "#6b7280",
          marginBottom: "24px", textAlign: "center"
        }}>
          Elige tu idioma · 选择语言 · भाषा चुनें
        </div>

        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: "12px", width: "100%", maxWidth: "420px"
        }}>
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              onClick={() => handleSelectLanguage(lang)}
              style={{
                background: "#111827", border: "1px solid #1f2937",
                borderRadius: "12px", padding: "18px 8px",
                color: "#f1f1f1", cursor: "pointer",
                textAlign: "center", transition: "all 0.15s"
              }}
              onMouseEnter={e => {
                e.currentTarget.style.border = "1px solid #f97316";
                e.currentTarget.style.background = "rgba(249,115,22,0.1)";
                e.currentTarget.style.transform = "scale(1.03)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.border = "1px solid #1f2937";
                e.currentTarget.style.background = "#111827";
                e.currentTarget.style.transform = "scale(1)";
              }}
            >
              <div style={{ fontSize: "2.2rem", marginBottom: "6px" }}>
                {lang.flag}
              </div>
              <div style={{ fontSize: "0.82rem", fontWeight: "600" }}>
                {lang.name}
              </div>
            </button>
          ))}
        </div>

        <div style={{
          marginTop: "28px", fontSize: "0.72rem",
          color: "#374151", textAlign: "center"
        }}>
          🔒 No account needed · Sin cuenta · 无需账户
        </div>
      </div>
    );
  }

  // ── Translating Spinner ──
  if (screen === "translating") {
    return (
      <div style={{
        minHeight: "100vh", backgroundColor: "#0a0a0f",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "16px"
      }}>
        <div style={{ fontSize: "3rem" }}>💼</div>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f1f1f1" }}>
          PaySnap
        </div>
        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          color: "#9ca3af", fontSize: "0.88rem"
        }}>
          <span style={{
            display: "inline-block", width: "18px", height: "18px",
            border: "2px solid #f97316", borderTopColor: "transparent",
            borderRadius: "50%", animation: "spin 0.8s linear infinite"
          }} />
          Translating to {langName}...
        </div>
        <div style={{
          color: "#4b5563", fontSize: "0.75rem",
          textAlign: "center", maxWidth: "260px", lineHeight: "1.6"
        }}>
          Gemma 4 is translating into {langName}.
          This happens once — about 60 seconds.
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Main App ──
  const currentLang = LANGUAGES.find(l => l.code === language);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0a0a0f" }}>

      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        borderBottom: "1px solid #f97316",
        padding: "16px 16px 12px", textAlign: "center"
      }}>
        <div style={{
          display: "flex", alignItems: "center",
          justifyContent: "center", gap: "10px", marginBottom: "4px"
        }}>
          <span style={{ fontSize: "1.6rem", fontWeight: "800" }}>
            💼 PaySnap
          </span>
          <button
            onClick={() => {
              setScreen("picker");
              setLanguage(null);
              setTranslations(EN_FALLBACK);
            }}
            style={{
              background: "#1f2937", border: "1px solid #374151",
              borderRadius: "20px", padding: "4px 10px",
              color: "#9ca3af", cursor: "pointer", fontSize: "0.75rem",
              display: "flex", alignItems: "center", gap: "4px"
            }}
          >
            {currentLang?.flag} {currentLang?.name} ↓
          </button>
        </div>

        <div style={{ color: "#9ca3af", fontSize: "0.78rem" }}>
          {translations.tagline}
        </div>

        <div style={{
          marginTop: "10px", background: "rgba(251,191,36,0.1)",
          border: "1px solid rgba(251,191,36,0.3)", borderRadius: "8px",
          padding: "7px 12px", fontSize: "0.72rem", color: "#fbbf24",
          maxWidth: "500px", margin: "10px auto 0"
        }}>
          ⚖️ {translations.disclaimer}
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", borderBottom: "1px solid #1f2937",
        backgroundColor: "#111827", position: "sticky", top: 0, zIndex: 10
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
              color: tab === tb.id ? "#f97316" : "#6b7280",
              borderBottom: tab === tb.id
                ? "2px solid #f97316" : "2px solid transparent",
              transition: "all 0.2s"
            }}>
            {tb.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: "600px", margin: "0 auto",
                    padding: "20px 16px 40px" }}>
        {tab === "analyze" && <Analyze t={translations} language={language} />}
        {tab === "history" && <History t={translations} language={language} />}
        {tab === "rights"  && <Rights  t={translations} />}
      </div>

    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}
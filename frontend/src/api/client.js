// frontend/src/api/client.js
// AI features → FastAPI backend (Gemma 4 via Ollama, local)
// Violation math → pure browser JS (deterministic, zero AI)
// Voice → Web Speech API (browser built-in)

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Deterministic violation math — zero AI, always correct ──
const MIN_WAGES = { TX:7.25, CA:16.50, NY:16.00, FL:13.00, IL:14.00 };
const STATUTES  = {
  TX: "FLSA 29 USC 207(a)(1)",
  CA: "CA Labor Code §510 and FLSA 29 USC 207(a)(1)",
  NY: "NY Labor Law §193 and FLSA 29 USC 207(a)(1)",
  FL: "FLSA 29 USC 207(a)(1)",
  IL: "820 ILCS 105/4a and FLSA 29 USC 207(a)(1)",
};
const ILLEGAL_DEDS = {
  CA: ["tool","uniform","equipment","business"],
  NY: ["tool","uniform","equipment","business"],
  IL: ["tool","uniform","breakage","damage","shortage"],
  TX: [], FL: [],
};
const LEGAL_AID = {
  TX: { name:"DOL Wage and Hour Division", phone:"1-866-487-9243", state:"Texas Workforce Commission", statePhone:"1-800-832-9243" },
  CA: { name:"DOL Wage and Hour Division", phone:"1-866-487-9243", state:"California Labor Commissioner", statePhone:"1-844-522-6734" },
  NY: { name:"DOL Wage and Hour Division", phone:"1-866-487-9243", state:"NY Department of Labor", statePhone:"1-888-469-7365" },
  FL: { name:"DOL Wage and Hour Division", phone:"1-866-487-9243", state:"Florida DEO", statePhone:"1-800-204-2418" },
  IL: { name:"DOL Wage and Hour Division", phone:"1-866-487-9243", state:"Illinois Department of Labor", statePhone:"1-312-793-2800" },
};

// ── Violation math (pure JS, deterministic) ──
function calcViolations(regularHours, overtimeHours, hourlyRate, state, deductions) {
  const total     = regularHours + overtimeHours;
  const minWage   = MIN_WAGES[state]    || 7.25;
  const statute   = STATUTES[state]     || "FLSA 29 USC 207(a)(1)";
  const illegalKw = ILLEGAL_DEDS[state] || [];
  const aid       = LEGAL_AID[state]    || LEGAL_AID.TX;

  let otOwed = 0, otHours = 0, breakdown = "";

  if (total > 40 && overtimeHours < (total - 40)) {
    otHours = (total - 40) - overtimeHours;
    const otRate = hourlyRate * 0.5; // premium only — straight time already paid
    otOwed = otHours * otRate;
    breakdown =
      `Total hours:       ${total}\n` +
      `Rate:              $${hourlyRate.toFixed(2)}/hr (premium only)\n` +
      `OT threshold:      40 hrs/week\n` +
      `OT hours owed:     ${otHours.toFixed(1)}\n` +
      `OT rate:           $${hourlyRate.toFixed(2)} × 0.5 = $${(hourlyRate*0.5).toFixed(2)}/hr (premium only)\n` +
      `OT pay:            ${otHours.toFixed(1)} × $${(hourlyRate*0.5).toFixed(2)} = $${otOwed.toFixed(2)}\n` +
      `────────────────────────────────\n` +
      `TOTAL OWED:        $${otOwed.toFixed(2)}`;
  }

  const illegalDeds = (deductions || []).filter(d =>
    d.name && illegalKw.some(kw => d.name.toLowerCase().includes(kw))
  );
  const illegalTotal = illegalDeds.reduce((s, d) => s + (d.amount || 0), 0);
  const gross = hourlyRate * total;
  const totalDedAmt = (deductions || []).reduce((s, d) => s + (d.amount || 0), 0);
  const effectiveRate = total > 0 ? (gross - totalDedAmt) / total : hourlyRate;
  const mwViolation = effectiveRate < minWage;
  const totalOwed = otOwed + illegalTotal;
  const hasViolation = totalOwed > 0 || mwViolation;

  return {
    hasViolation, totalOwed, otOwed, otHours,
    illegalDeds, mwViolation, effectiveRate,
    minWage, breakdown, statute, aid,
    total, hourlyRate, state
  };
}

// ── Generic backend POST with FormData ──
async function postForm(endpoint, fields) {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    formData.append(key, value);
  }
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Backend error ${res.status}: ${endpoint}`);
  return res.json();
}

export const api = {

  // ── TRANSLATE UI ──
  // Backend calls Gemma 4 via Ollama (local, fast, no rate limits)
  // Cached in localStorage so runs only once per language
  async translateUI(languageCode, languageName, _strings) {
    // Check cache
    const cacheKey = `paysnap_ui_${languageCode}`;
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        console.log(`✅ Cached translations for ${languageCode}`);
        return { success: true, data: { translations: JSON.parse(cached) } };
      }
    } catch (e) {}

    console.log(`🔄 Translating UI to ${languageName} via Gemma 4...`);

    try {
      const res = await postForm('/translate-ui', {
        language: languageCode,
        language_name: languageName,
      });

      if (res.success && res.data?.translations) {
        // Cache for future use
        try {
          localStorage.setItem(cacheKey, JSON.stringify(res.data.translations));
        } catch (e) {}
        return res;
      }
      return { success: false, error: 'Translation failed' };
    } catch (e) {
      console.error('Translation error:', e.message);
      return { success: false, error: e.message };
    }
  },

  // ── EXTRACT FROM FILE ──
  // Backend: Gemma 4 vision reads paystub image/PDF
  async extract(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${BASE_URL}/extract`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Extract error ${res.status}`);
      return res.json();
    } catch (e) {
      console.error('Extract error:', e.message);
      return { success: false, error: e.message };
    }
  },

  // ── EXTRACT FROM TEXT / VOICE ──
  // Two approaches:
  // 1. Try backend Gemma 4 (best accuracy)
  // 2. Fallback to regex (works offline)
  async extractFromText(text) {
    // Try backend first (Gemma 4 understands any language)
    try {
      const res = await postForm('/extract-text', { text });
      if (res.success && res.data) {
        return res;
      }
    } catch (e) {
      console.warn('Backend text extraction failed, using regex:', e.message);
    }

    // Regex fallback — works without backend
    return api._regexExtract(text);
  },

  // Regex extraction — works for any language with numbers
  _regexExtract(text) {
    // Match hours (works for: "52 hours", "52 horas", "52 घंटे", "52 giờ")
    const hoursMatch = text.match(
      /(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|घंटे|horas?|小时|giờ|ساعة|часов|시간|ชั่วโมง)/i
    );
    // Match rate (works for: "$23", "$23/hr", "23 dollars")
    const rateMatch = text.match(/\$\s*(\d+(?:\.\d+)?)/);

    // Match state
    const stateMap = {
      texas:"TX", california:"CA", "new york":"NY",
      florida:"FL", illinois:"IL",
    };
    const stateMatch = text.match(
      /\b(TX|CA|NY|FL|IL|Texas|California|New\s*York|Florida|Illinois)\b/i
    );
    const stateRaw = stateMatch?.[1]?.toLowerCase().trim();
    const state = stateRaw
      ? (stateMap[stateRaw] || stateMatch[1].toUpperCase().substring(0,2))
      : "TX";

    // Match deductions
    const deds = [];
    const dedMatches = text.matchAll(/\$(\d+(?:\.\d+)?)\s+(?:for\s+)?(\w+)/gi);
    for (const m of dedMatches) {
      const amount = parseFloat(m[1]);
      const name   = m[2].toUpperCase();
      if (rateMatch && Math.abs(amount - parseFloat(rateMatch[1])) > 1) {
        deds.push({ name, amount });
      }
    }

    const hours = hoursMatch ? parseFloat(hoursMatch[1]) : 0;
    const rate  = rateMatch  ? parseFloat(rateMatch[1])  : 0;

    return {
      success: hours > 0 && rate > 0,
      data: {
        employer_name: "",      // Cannot extract from speech reliably
        regular_hours: hours,
        overtime_hours: 0,
        hourly_rate: rate,
        state,
        deductions: deds,
      }
    };
  },

  // ── ANALYZE PAYSTUB ──
  // Math: deterministic JS (no AI, always accurate)
  // Explanation: backend Gemma 4 in worker's language
  async analyze({ employer, regularHours, overtimeHours,
                  hourlyRate, state, deductions, language, languageName }) {

    // Always run deterministic math first
    const calc = calcViolations(
      regularHours, overtimeHours, hourlyRate, state, deductions
    );

    // Build summary for Gemma 4 to explain
    let summary = "";
    if (!calc.hasViolation) {
      summary =
        `No violations. Worker: ${regularHours + overtimeHours} hrs at ` +
        `$${hourlyRate}/hr in ${state}. ` +
        `Under ${calc.statute}, overtime applies after 40hrs. ` +
        `All deductions appear legal.`;
    } else {
      if (calc.otOwed > 0) {
        summary +=
          `OVERTIME VIOLATION: ${regularHours + overtimeHours} total hours. ` +
          `${calc.otHours.toFixed(1)} overtime hours unpaid at ` +
          `$${(hourlyRate*1.5).toFixed(2)}/hr. ` +
          `Owed: $${calc.otOwed.toFixed(2)}. ` +
          `Statute: ${calc.statute}. `;
      }
      calc.illegalDeds.forEach(d => {
        summary += `ILLEGAL DEDUCTION: $${d.amount} for "${d.name}" illegal in ${state}. `;
      });
      summary += `Total owed: $${calc.totalOwed.toFixed(2)}.`;
    }

    // Try backend for Gemma 4 explanation
    try {
      const res = await postForm('/analyze', {
        employer: employer || 'Unknown',
        regular_hours: String(regularHours),
        overtime_hours: String(overtimeHours),
        hourly_rate: String(hourlyRate),
        state,
        deductions: JSON.stringify(deductions || []),
        language: language || 'en',
      });

      if (res.success && res.data) {
        // Merge backend explanation with our deterministic math
        return {
          success: true,
          data: {
            ...res.data,
            // Always use our math (deterministic)
            has_violation: calc.hasViolation,
            total_money_owed: calc.totalOwed,
            breakdown: calc.breakdown || res.data.breakdown,
          }
        };
      }
    } catch (e) {
      console.warn('Backend analyze failed, using fallback:', e.message);
    }

    // Fallback — return deterministic result with English explanation
    return {
      success: true,
      data: {
        has_violation: calc.hasViolation,
        total_money_owed: calc.totalOwed,
        breakdown: calc.breakdown,
        explanation_es: summary + '\n\nDOL: 1-866-487-9243 (free, confidential)',
        statute: calc.statute,
        illegal_deductions: calc.illegalDeds.map(d => ({
          name: d.name, amount: d.amount,
          reason_es: `$${d.amount} for "${d.name}" is illegal in ${state}`,
          statute: calc.statute,
        })),
        legal_aid: [{
          organization_name: calc.aid.name,
          organization_name_es: calc.aid.name,
          phone: calc.aid.phone,
          phone_note_es: 'Free · Bilingual · Regardless of immigration status',
        }, {
          organization_name: calc.aid.state,
          organization_name_es: calc.aid.state,
          phone: calc.aid.statePhone,
          phone_note_es: 'State agency — free assistance',
        }],
      }
    };
  },

  // ── DEMAND LETTER ──
  async demandLetter({ employer, regularHours, overtimeHours,
                       hourlyRate, state, totalOwed, breakdown, statute }) {
    try {
      const res = await postForm('/demand-letter', {
        employer: employer || 'Unknown',
        regular_hours: String(regularHours),
        overtime_hours: String(overtimeHours),
        hourly_rate: String(hourlyRate),
        state,
        total_owed: String(totalOwed),
        breakdown: breakdown || '',
        statute: statute || 'FLSA 29 USC 207(a)(1)',
      });
      return res;
    } catch (e) {
      return { success: false, error: e.message };
    }
  },

  // ── VOICE TRANSCRIPTION ──
  // Uses Web Speech API — browser built-in, works in Chrome/Safari
  // continuous=true: keeps listening until silence detected
  transcribeAudio(onResult, onEnd, onError) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      onError("Speech recognition requires Chrome or Safari.");
      return null;
    }

    const recognition = new SR();
    recognition.continuous     = true;   // Keep listening
    recognition.interimResults = true;   // Show words as spoken
    recognition.maxAlternatives = 1;
    recognition.lang           = "";     // Auto-detect language

    let finalTranscript = "";
    let silenceTimer    = null;

    recognition.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          finalTranscript += t + " ";
        } else {
          interim = t;
        }
      }
      // Show live transcript
      onResult((finalTranscript + interim).trim(), false);

      // Auto-stop after 2.5 seconds of silence
      clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => {
        if (finalTranscript.trim()) {
          recognition.stop();
          onResult(finalTranscript.trim(), true);
        }
      }, 2500);
    };

    recognition.onend = () => {
      clearTimeout(silenceTimer);
      onEnd(finalTranscript.trim());
    };

    recognition.onerror = (e) => {
      clearTimeout(silenceTimer);
      if (e.error !== "no-speech") onError(e.error);
    };

    recognition.start();

    return {
      recognition,
      getTranscript: () => finalTranscript.trim(),
      stop: () => {
        clearTimeout(silenceTimer);
        recognition.stop();
      }
    };
  },

  // ── HISTORY ──
  async getHistory(language = "en") {
    try {
      const res = await fetch(`${BASE_URL}/history?language=${language}`);
      return res.json();
    } catch (e) {
      return { success: true, data: { records: [], summary: {} } };
    }
  },

  // ── EXPORT ──
  exportEvidence() {
    window.open(`${BASE_URL}/export`, '_blank');
  }
};
// frontend/src/api/client.js
// All API calls to FastAPI backend
// Backend runs at localhost:8000

const BASE_URL = 'http://localhost:8000';

export const api = {

  // ─────────────────────────────────────────────
  // TRANSLATE UI
  // Called once when user picks a language.
  // Gemma 4 translates all UI strings.
  // Adding a new language = zero changes here.
  // ─────────────────────────────────────────────
  async translateUI(languageCode, languageName) {
    const formData = new FormData();
    formData.append('language', languageCode);
    formData.append('language_name', languageName);
    const res = await fetch(`${BASE_URL}/translate-ui`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // ─────────────────────────────────────────────
  // EXTRACT
  // Upload paystub file — Gemma 4 reads it
  // Returns pre-filled fields for worker to verify
  // ─────────────────────────────────────────────
  async extract(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/extract`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // ─────────────────────────────────────────────
  // ANALYZE
  // Run violation analysis on confirmed paystub data
  // Returns Spanish/multilingual explanation + math
  // ─────────────────────────────────────────────
  async analyze(data) {
    const formData = new FormData();
    formData.append('employer', data.employer || '');
    formData.append('regular_hours', data.regularHours || 0);
    formData.append('overtime_hours', data.overtimeHours || 0);
    formData.append('hourly_rate', data.hourlyRate || 0);
    formData.append('state', data.state || 'TX');
    formData.append('deductions', JSON.stringify(data.deductions || []));
    formData.append('language', data.language || 'es');
    const res = await fetch(`${BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // ─────────────────────────────────────────────
  // DEMAND LETTER
  // Generate formal English demand letter
  // Based on violation findings
  // ─────────────────────────────────────────────
  async demandLetter(data) {
    const formData = new FormData();
    formData.append('employer', data.employer || '');
    formData.append('regular_hours', data.regularHours || 0);
    formData.append('overtime_hours', data.overtimeHours || 0);
    formData.append('hourly_rate', data.hourlyRate || 0);
    formData.append('state', data.state || 'TX');
    formData.append('total_owed', data.totalOwed || 0);
    formData.append('breakdown', data.breakdown || '');
    formData.append('statute', data.statute || 'FLSA 29 USC 207(a)(1)');
    const res = await fetch(`${BASE_URL}/demand-letter`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // ─────────────────────────────────────────────
  // HISTORY
  // Get encrypted local paystub history
  // ─────────────────────────────────────────────
  async getHistory(language = "es") {
    const res = await fetch(`${BASE_URL}/history?language=${language}`);
    return res.json();
  },

  // ─────────────────────────────────────────────
  // EXPORT EVIDENCE
  // Download evidence vault as text file
  // Opens in new tab for download
  // ─────────────────────────────────────────────
  exportEvidence() {
    window.open(`${BASE_URL}/export`, '_blank');
  }

};
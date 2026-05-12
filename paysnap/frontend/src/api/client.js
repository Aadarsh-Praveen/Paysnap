// API client — all calls to FastAPI backend

const BASE_URL = 'http://localhost:8000';

export const api = {

  // Extract fields from uploaded file
  async extract(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/extract`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // Analyze paystub for violations
  async analyze(data) {
    const formData = new FormData();
    formData.append('employer', data.employer || '');
    formData.append('regular_hours', data.regularHours || 0);
    formData.append('overtime_hours', data.overtimeHours || 0);
    formData.append('hourly_rate', data.hourlyRate || 0);
    formData.append('state', data.state || 'TX');
    formData.append('deductions', JSON.stringify(data.deductions || []));
    const res = await fetch(`${BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // Generate demand letter
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

  // Get history
  async getHistory() {
    const res = await fetch(`${BASE_URL}/history`);
    return res.json();
  },

  // Export evidence
  exportEvidence() {
    window.open(`${BASE_URL}/export`, '_blank');
  }
};
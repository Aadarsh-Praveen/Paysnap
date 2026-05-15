import 'package:flutter/material.dart';
import '../services/violation_service.dart';
import '../models/paystub_model.dart';
import 'results_screen.dart';
import 'agent_screen.dart';

class AnalyzeScreen extends StatefulWidget {
  final String language;
  final String languageName;
  final String languageFlag;
  final Map<String, String> translations;
  final VoidCallback onSwitchLanguage;

  const AnalyzeScreen({
    super.key,
    required this.language,
    required this.languageName,
    required this.languageFlag,
    required this.translations,
    required this.onSwitchLanguage,
  });

  @override
  State<AnalyzeScreen> createState() => _AnalyzeScreenState();
}

class _AnalyzeScreenState extends State<AnalyzeScreen> {
  int _currentTab = 0;
  bool _analyzing = false;

  final _employerCtrl = TextEditingController();
  final _regHoursCtrl = TextEditingController();
  final _otHoursCtrl  = TextEditingController(text: '0');
  final _rateCtrl     = TextEditingController();
  String _state = 'TX';

  final List<Map<String, dynamic>> _deductions = [];
  final _states = ['TX', 'CA', 'NY', 'FL', 'IL'];

  String t(String key, String fallback) =>
    widget.translations[key] ?? fallback;

  final _testCases = [
    {
      'icon': '🚨',
      'title': 'Texas Construction Worker',
      'desc': '52 hrs · \$23/hr · Overtime violation · TX',
      'data': {
        'employer': 'ABC Construction LLC',
        'reg': '52', 'ot': '0',
        'rate': '23', 'state': 'TX',
        'deds': <Map<String, dynamic>>[]
      }
    },
    {
      'icon': '⚠️',
      'title': 'California Uniform Deduction',
      'desc': '40 hrs · \$20/hr · Illegal deduction · CA',
      'data': {
        'employer': 'Golden State Services',
        'reg': '40', 'ot': '0',
        'rate': '20', 'state': 'CA',
        'deds': [{'name': 'UNIFORM', 'amount': '100'}]
      }
    },
    {
      'icon': '✅',
      'title': 'Clean Paystub',
      'desc': '38 hrs · \$18/hr · No violation · FL',
      'data': {
        'employer': 'Sunshine Retail FL',
        'reg': '38', 'ot': '0',
        'rate': '18', 'state': 'FL',
        'deds': [{'name': 'FEDERAL TAX', 'amount': '95'}]
      }
    },
  ];

  void _loadTestCase(Map<String, dynamic> data) {
    setState(() {
      _employerCtrl.text = data['employer'];
      _regHoursCtrl.text = data['reg'];
      _otHoursCtrl.text  = data['ot'];
      _rateCtrl.text     = data['rate'];
      _state = data['state'];
      _deductions.clear();
      for (final d in data['deds'] as List) {
        _deductions.add(Map<String, dynamic>.from(d));
      }
    });
  }

  Future<void> _analyze() async {
    final reg  = double.tryParse(_regHoursCtrl.text) ?? 0;
    final ot   = double.tryParse(_otHoursCtrl.text)  ?? 0;
    final rate = double.tryParse(_rateCtrl.text)      ?? 0;

    if (rate == 0 || reg == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(
          t('enter_hours', 'Please enter hours worked and hourly rate')
        )),
      );
      return;
    }

    setState(() => _analyzing = true);

    try {
      final paystub = PaystubModel(
        employer: _employerCtrl.text.isEmpty ? 'Unknown' : _employerCtrl.text,
        regularHours: reg,
        otHours: ot,
        hourlyRate: rate,
        state: _state,
        deductions: _deductions.map((d) => DeductionModel(
          name: d['name'] ?? '',
          amount: double.tryParse(d['amount'] ?? '0') ?? 0,
        )).toList(),
        language: widget.language,
      );

      final result = await ViolationService.analyze(paystub);

      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ResultsScreen(
              result: result,
              language: widget.language,
              translations: widget.translations,
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: Column(
        children: [
          _buildHeader(),
          _buildTabs(),
          Expanded(
            child: _currentTab == 0
              ? _buildAnalyzeTab()
              : _buildRightsTab(),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: EdgeInsets.only(
        top: MediaQuery.of(context).padding.top + 8,
        left: 20, right: 20, bottom: 12,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(color: Color(0xFFF97316), width: 1),
        ),
        boxShadow: [BoxShadow(
          color: Color(0x10F97316), blurRadius: 8, offset: Offset(0, 2),
        )],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('💼 PAYSNAP',
                style: TextStyle(
                  fontFamily: 'SpaceMono', fontSize: 18,
                  fontWeight: FontWeight.bold, color: Color(0xFFF97316),
                ),
              ),
              const SizedBox(width: 12),
              GestureDetector(
                onTap: widget.onSwitchLanguage,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${widget.languageFlag} ${widget.languageName} ↓',
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            t('tagline', 'Your paystub. Your rights. On your phone.'),
            style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFFFFBEB),
              border: Border.all(color: const Color(0xFFFDE68A)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '⚖️ ${t("disclaimer", "Not legal advice. Your data never leaves your device.")}',
              style: const TextStyle(fontSize: 11, color: Color(0xFF92400E)),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabs() {
    return Container(
      color: Colors.white,
      child: Row(
        children: [
          _buildTab(0, t('tab_analyze', 'ANALYZE')),
          _buildTab(1, t('tab_rights', 'RIGHTS')),
        ],
      ),
    );
  }

  Widget _buildTab(int index, String label) {
    final active = _currentTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _currentTab = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: active ? const Color(0xFFF97316) : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: 'SpaceMono', fontSize: 13,
              fontWeight: FontWeight.bold,
              color: active ? const Color(0xFFF97316) : const Color(0xFF94A3B8),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAnalyzeTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [

          // ── AGENT BUTTON (The wow factor) ──
          GestureDetector(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => AgentScreen(
                  language: widget.language,
                  languageName: widget.languageName,
                  languageFlag: widget.languageFlag,
                  translations: widget.translations,
                ),
              ),
            ),
            child: Container(
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFF97316), Color(0xFFEA580C)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0x40F97316),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: Row(
                children: [
                  Container(
                    width: 52, height: 52,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Center(
                      child: Text('🤖', style: TextStyle(fontSize: 28)),
                    ),
                  ),
                  const SizedBox(width: 14),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'ASK GEMMA 4 DIRECTLY',
                          style: TextStyle(
                            fontFamily: 'SpaceMono',
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Describe your situation in your language.\n'
                          'Gemma 4 calls the right tools automatically.',
                          style: TextStyle(
                            fontSize: 11,
                            color: Color(0xFFFFEDD5),
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(
                    Icons.arrow_forward_ios,
                    color: Colors.white,
                    size: 16,
                  ),
                ],
              ),
            ),
          ),

          // ── QUICK TEST CASES ──
          _buildSectionLabel('⚡ ${t("quick_tests", "QUICK TEST CASES")}'),
          const SizedBox(height: 8),
          ..._testCases.map((tc) => _buildTestCaseButton(tc)),
          const SizedBox(height: 20),

          // ── FORM ──
          _buildCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildStepLabel(t('step2', 'STEP 2')),
                Text(
                  t('form_title', 'Enter Your Paystub Data'),
                  style: const TextStyle(
                    fontFamily: 'SpaceMono', fontSize: 16,
                    fontWeight: FontWeight.bold, color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  t('form_sub', 'Fill in your information below'),
                  style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                ),
                const SizedBox(height: 16),

                _buildField(
                  t('employer', 'EMPLOYER NAME'),
                  _employerCtrl,
                  hint: 'ABC Construction LLC',
                ),
                const SizedBox(height: 12),

                Row(children: [
                  Expanded(child: _buildField(
                    t('reg_hours', 'REGULAR HOURS'), _regHoursCtrl,
                    hint: '40', keyboardType: TextInputType.number,
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: _buildField(
                    t('ot_hours', 'OT HOURS ON STUB'), _otHoursCtrl,
                    hint: '0', keyboardType: TextInputType.number,
                  )),
                ]),
                const SizedBox(height: 12),

                Row(children: [
                  Expanded(child: _buildField(
                    t('rate', 'HOURLY RATE (\$)'), _rateCtrl,
                    hint: '15.00', keyboardType: TextInputType.number,
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: _buildStateDropdown()),
                ]),
                const SizedBox(height: 12),

                _buildDeductionsSection(),
                const SizedBox(height: 16),

                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _analyzing ? null : _analyze,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFF97316),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                      elevation: 4,
                      shadowColor: const Color(0x40F97316),
                    ),
                    child: _analyzing
                      ? Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const SizedBox(
                              width: 18, height: 18,
                              child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Text(
                              t('analyzing', 'ANALYZING...'),
                              style: const TextStyle(
                                fontFamily: 'SpaceMono',
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        )
                      : Text(
                          '🔍  ${t("analyze_btn", "RUN GEMMA 4 ANALYSIS")}',
                          style: const TextStyle(
                            fontFamily: 'SpaceMono',
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTestCaseButton(Map<String, dynamic> tc) {
    return GestureDetector(
      onTap: () => _loadTestCase(tc['data'] as Map<String, dynamic>),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: const Color(0xFFE2E8F0)),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFFFFF7ED),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(tc['icon']!, style: const TextStyle(fontSize: 20)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(tc['title']!,
                    style: const TextStyle(
                      fontFamily: 'SpaceMono', fontWeight: FontWeight.bold,
                      fontSize: 12, color: Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(tc['desc']!,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                  ),
                ],
              ),
            ),
            const Text('→',
              style: TextStyle(color: Color(0xFFF97316), fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeductionsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildFieldLabel(t('deductions', 'DEDUCTIONS')),
        ..._deductions.asMap().entries.map((e) {
          final i = e.key;
          final d = e.value;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    initialValue: d['name'],
                    decoration: _inputDecoration('e.g. TOOLS'),
                    onChanged: (v) => _deductions[i]['name'] = v,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextFormField(
                    initialValue: d['amount'],
                    decoration: _inputDecoration('75.00'),
                    keyboardType: TextInputType.number,
                    onChanged: (v) => _deductions[i]['amount'] = v,
                  ),
                ),
                IconButton(
                  onPressed: () => setState(() => _deductions.removeAt(i)),
                  icon: const Icon(Icons.close, color: Color(0xFFCBD5E1), size: 18),
                ),
              ],
            ),
          );
        }),
        GestureDetector(
          onTap: () => setState(() => _deductions.add({'name': '', 'amount': ''})),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFFCBD5E1)),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              t('add_ded', '+ Add deduction'),
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontFamily: 'SpaceMono', fontSize: 11, color: Color(0xFF94A3B8),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStateDropdown() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildFieldLabel(t('state', 'STATE')),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            borderRadius: BorderRadius.circular(10),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _state,
              isExpanded: true,
              items: _states.map((s) => DropdownMenuItem(
                value: s,
                child: Text(s, style: const TextStyle(
                  fontFamily: 'SpaceMono', fontWeight: FontWeight.bold,
                )),
              )).toList(),
              onChanged: (v) => setState(() => _state = v!),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRightsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          _buildCard(
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: const BoxDecoration(
                    color: Color(0xFFF97316),
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(10),
                      topRight: Radius.circular(10),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        t('rights_title', 'YOUR RIGHTS AS A WORKER'),
                        style: const TextStyle(
                          fontFamily: 'SpaceMono', color: Colors.white,
                          fontWeight: FontWeight.bold, fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        t('rights_sub', 'Regardless of immigration status'),
                        style: const TextStyle(color: Color(0xFFFFEDD5), fontSize: 11),
                      ),
                    ],
                  ),
                ),
                _buildRightItem('💰', 'Minimum Wage',
                  'Your employer MUST pay at least state minimum wage.'),
                _buildRightItem('⏰', 'Overtime Pay',
                  'Over 40 hours/week = 1.5x your regular rate.'),
                _buildRightItem('🛡️', 'No Retaliation',
                  'Illegal to fire you for reporting wage violations.'),
                _buildRightItem('📋', 'FLSA Protection',
                  'Protects ALL workers regardless of immigration status.'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _buildCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  t('wages_title', 'MINIMUM WAGES 2025'),
                  style: const TextStyle(
                    fontFamily: 'SpaceMono', fontWeight: FontWeight.bold,
                    fontSize: 13, color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 12),
                _buildWageRow('🏖️ California', '\$16.50/hr'),
                _buildWageRow('🗽 New York',   '\$16.00/hr'),
                _buildWageRow('🌾 Illinois',   '\$14.00/hr'),
                _buildWageRow('☀️ Florida',    '\$13.00/hr'),
                _buildWageRow('⭐ Texas',      '\$7.25/hr'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              border: Border.all(color: const Color(0xFFBFDBFE)),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              children: [
                Text(
                  '📞 ${t("report", "REPORT A VIOLATION")}',
                  style: const TextStyle(
                    fontFamily: 'SpaceMono', color: Color(0xFF2563EB),
                    fontSize: 11, letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                const Text('1-866-487-9243',
                  style: TextStyle(
                    fontFamily: 'SpaceMono', fontSize: 28,
                    fontWeight: FontWeight.bold, color: Color(0xFFF97316),
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Free · Bilingual · Regardless of immigration status',
                  style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRightItem(String icon, String title, String desc) {
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(child: Text(icon)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                  style: const TextStyle(
                    fontFamily: 'SpaceMono', fontWeight: FontWeight.bold,
                    fontSize: 12, color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 3),
                Text(desc,
                  style: const TextStyle(
                    fontSize: 12, color: Color(0xFF64748B), height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWageRow(String state, String wage) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(state,
            style: const TextStyle(
              fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF334155),
            ),
          ),
          Text(wage,
            style: const TextStyle(
              fontFamily: 'SpaceMono', fontWeight: FontWeight.bold,
              color: Color(0xFFF97316), fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCard({required Widget child}) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE2E8F0)),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(
          color: Colors.black.withOpacity(0.04),
          blurRadius: 8, offset: const Offset(0, 2),
        )],
      ),
      child: Padding(padding: const EdgeInsets.all(16), child: child),
    );
  }

  Widget _buildField(
    String label,
    TextEditingController ctrl, {
    String hint = '',
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildFieldLabel(label),
        TextFormField(
          controller: ctrl,
          keyboardType: keyboardType,
          decoration: _inputDecoration(hint),
          style: const TextStyle(
            fontFamily: 'SpaceMono', fontWeight: FontWeight.bold, fontSize: 15,
          ),
        ),
      ],
    );
  }

  Widget _buildFieldLabel(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(label,
        style: const TextStyle(
          fontFamily: 'SpaceMono', fontSize: 10,
          color: Color(0xFF94A3B8), letterSpacing: 1,
        ),
      ),
    );
  }

  Widget _buildSectionLabel(String label) {
    return Text(label,
      style: const TextStyle(
        fontFamily: 'SpaceMono', fontSize: 10,
        color: Color(0xFF94A3B8), letterSpacing: 1.5,
      ),
    );
  }

  Widget _buildStepLabel(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(label,
        style: const TextStyle(
          fontFamily: 'SpaceMono', fontSize: 10,
          color: Color(0xFFF97316), letterSpacing: 1.5,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13),
      filled: true,
      fillColor: const Color(0xFFF8FAFC),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Color(0xFFF97316), width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    );
  }
}
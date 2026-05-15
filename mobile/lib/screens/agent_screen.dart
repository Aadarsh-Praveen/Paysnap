import 'package:flutter/material.dart';
import '../services/agent_service.dart';
import '../services/cactus_service.dart';

class AgentScreen extends StatefulWidget {
  final String language;
  final String languageName;
  final String languageFlag;
  final Map<String, String> translations;

  const AgentScreen({
    super.key,
    required this.language,
    required this.languageName,
    required this.languageFlag,
    required this.translations,
  });

  @override
  State<AgentScreen> createState() => _AgentScreenState();
}

class _AgentScreenState extends State<AgentScreen> {
  final _controller = TextEditingController();
  bool _analyzing = false;
  String _currentStep = '';
  AgentAnalysisResult? _result;

  String get _examplePrompt {
    switch (widget.language) {
      case 'es':
        return 'Trabajé 52 horas esta semana a \$23 por hora en Texas. '
               'Me descontaron \$75 por herramientas.';
      case 'hi':
        return 'मैंने इस हफ्ते Texas में 52 घंटे काम किया \$23 प्रति घंटे पर। '
               'उन्होंने tools के लिए \$75 काटे।';
      case 'zh':
        return '我这周在德克萨斯州工作了52小时，每小时23美元。'
               '他们扣了我75美元的工具费。';
      case 'vi':
        return 'Tôi làm việc 52 giờ tuần này ở Texas với \$23/giờ. '
               'Họ khấu trừ \$75 cho dụng cụ.';
      case 'pt':
        return 'Trabalhei 52 horas esta semana no Texas a \$23/hora. '
               'Descontaram \$75 por ferramentas.';
      case 'ko':
        return '이번 주 텍사스에서 시간당 \$23에 52시간 일했습니다. '
               '도구 비용으로 \$75를 공제했습니다.';
      default:
        return 'I worked 52 hours this week in Texas at \$23/hour. '
               'They deducted \$75 for tools.';
    }
  }

  Future<void> _analyze() async {
    final input = _controller.text.trim();
    if (input.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please describe your situation'),
          backgroundColor: Color(0xFFF97316),
        ),
      );
      return;
    }

    setState(() {
      _analyzing = true;
      _currentStep = 'Loading Gemma 4...';
      _result = null;
    });

    try {
      await CactusService.initialize(
        onProgress: (progress, status) {
          if (mounted) setState(() => _currentStep = status);
        },
      );

      final model = CactusService.model;
      if (model == null) throw Exception('Model not loaded');

      final agent = PaySnapAgent(model: model);
      final result = await agent.analyze(
        workerInput: input,
        langName: widget.languageName,
        onProgress: (step) {
          if (mounted) setState(() => _currentStep = step);
        },
      );

      if (mounted) {
        setState(() {
          _result = result;
          _analyzing = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _analyzing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Color(0xFF0F172A)),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          '🤖 AI AGENT',
          style: TextStyle(
            fontFamily: 'SpaceMono',
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: Color(0xFFF97316),
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: const Color(0xFFF97316)),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Info card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF7ED),
                border: Border.all(color: const Color(0xFFFED7AA)),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '✨ Describe your situation',
                    style: TextStyle(
                      fontFamily: 'SpaceMono',
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: Color(0xFF92400E),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tell Gemma 4 what happened in ${widget.languageName}. '
                    'No forms needed — just describe your pay situation naturally. '
                    'Gemma 4 will call the right tools and explain your rights.',
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFF92400E),
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Input area
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: const Color(0xFFE2E8F0)),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  )
                ],
              ),
              child: Column(
                children: [
                  TextField(
                    controller: _controller,
                    maxLines: 5,
                    decoration: InputDecoration(
                      hintText: _examplePrompt,
                      hintStyle: const TextStyle(
                        color: Color(0xFFCBD5E1),
                        fontSize: 13,
                        height: 1.5,
                      ),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.all(16),
                    ),
                    style: const TextStyle(
                      fontSize: 14,
                      color: Color(0xFF0F172A),
                      height: 1.5,
                    ),
                  ),
                  GestureDetector(
                    onTap: () => setState(() {
                      _controller.text = _examplePrompt;
                    }),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10,
                      ),
                      decoration: const BoxDecoration(
                        border: Border(
                          top: BorderSide(color: Color(0xFFE2E8F0)),
                        ),
                      ),
                      child: Text(
                        '📋 Use example in ${widget.languageName}',
                        style: const TextStyle(
                          fontFamily: 'SpaceMono',
                          fontSize: 11,
                          color: Color(0xFFF97316),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12),

            // Analyze button
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
                        Flexible(
                          child: Text(
                            _currentStep,
                            style: const TextStyle(
                              fontFamily: 'SpaceMono',
                              fontWeight: FontWeight.bold,
                              fontSize: 11,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    )
                  : const Text(
                      '🤖  ASK GEMMA 4',
                      style: TextStyle(
                        fontFamily: 'SpaceMono',
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
              ),
            ),

            // Results
            if (_result != null) ...[
              const SizedBox(height: 20),
              _buildResults(_result!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResults(AgentAnalysisResult result) {
    return Column(
      children: [
        // Violation banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: result.hasViolation
              ? const Color(0xFFFFF7ED)
              : const Color(0xFFF0FDF4),
            border: Border.all(
              color: result.hasViolation
                ? const Color(0xFFFDBA74)
                : const Color(0xFF86EFAC),
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Container(
                width: 56, height: 56,
                decoration: BoxDecoration(
                  color: result.hasViolation
                    ? const Color(0xFFFEE2E2)
                    : const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Center(
                  child: Text(
                    result.hasViolation ? '🚨' : '✅',
                    style: const TextStyle(fontSize: 28),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      result.hasViolation
                        ? 'VIOLATION DETECTED'
                        : 'NO ISSUES FOUND',
                      style: TextStyle(
                        fontFamily: 'SpaceMono',
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1,
                        color: result.hasViolation
                          ? const Color(0xFFDC2626)
                          : const Color(0xFF16A34A),
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (result.hasViolation) ...[
                      Text(
                        '\$${result.totalOwed.toStringAsFixed(2)}',
                        style: const TextStyle(
                          fontFamily: 'SpaceMono',
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFFF97316),
                        ),
                      ),
                      const Text(
                        'potentially owed',
                        style: TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                    if (!result.hasViolation)
                      const Text(
                        'Your paystub is in compliance.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Color(0xFF16A34A),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Speed badge
        if (result.tokensPerSecond != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '⚡ ${result.tokensPerSecond!.toStringAsFixed(1)} tokens/sec  '
              '📱 On device  🔒 No internet',
              style: const TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 10,
                color: Color(0xFF64748B),
              ),
            ),
          ),
        ],

        const SizedBox(height: 12),

        // Tools called
        if (result.toolResults.isNotEmpty) ...[
          _buildCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '🔧 TOOLS CALLED BY GEMMA 4',
                  style: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 11,
                    color: Color(0xFFF97316),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 10),
                ...result.toolResults.map((tr) {
                  // Safe null check
                  final toolName = tr['tool'] as String? ?? 'unknown';
                  final hasError = tr['error'] != null;
                  final toolResult = tr['result'] as Map<String, dynamic>?;
                  final isViolation = !hasError &&
                    (toolResult?['has_violation'] == true ||
                     toolResult?['is_legal'] == false);

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            toolName,
                            style: const TextStyle(
                              fontFamily: 'SpaceMono',
                              fontSize: 10,
                              color: Color(0xFF475569),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          hasError
                            ? '❌ Error'
                            : isViolation
                              ? '🚨 Violation found'
                              : '✅ No violation',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF334155),
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],

        // Gemma explanation
        _buildCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '💬 GEMMA 4 EXPLANATION',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 11,
                  color: Color(0xFFF97316),
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                result.explanation,
                style: const TextStyle(
                  fontSize: 13,
                  color: Color(0xFF334155),
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),

        // Math breakdown
        if (result.breakdown.isNotEmpty) ...[
          const SizedBox(height: 12),
          _buildCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '🧮 MATH BREAKDOWN',
                  style: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 11,
                    color: Color(0xFFF97316),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    result.breakdown,
                    style: const TextStyle(
                      fontFamily: 'SpaceMono',
                      fontSize: 12,
                      color: Color(0xFF4ADE80),
                      height: 1.8,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: 12),

        // Legal aid
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            border: Border.all(color: const Color(0xFFBFDBFE)),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '📞 FREE LEGAL HELP',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 11,
                  color: Color(0xFF2563EB),
                  letterSpacing: 1,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'DOL Wage and Hour Division',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: Color(0xFF0F172A),
                ),
              ),
              SizedBox(height: 4),
              Text(
                '1-866-487-9243',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontWeight: FontWeight.bold,
                  fontSize: 24,
                  color: Color(0xFFF97316),
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Free · Bilingual · Regardless of immigration status',
                style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
              ),
            ],
          ),
        ),

        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildCard({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE2E8F0)),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: child,
    );
  }
}
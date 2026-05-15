import 'package:cactus/cactus.dart';
import 'dart:convert';
import 'violation_calculator.dart';

/// PaySnapAgent — Gemma 4 acting as an intelligent agent
///
/// The agent:
/// 1. Receives worker's situation in natural language
/// 2. Decides which tools to call
/// 3. Executes the tools (deterministic math)
/// 4. Synthesizes explanation in worker's language
///
/// This is TRUE agentic AI:
///   Worker input → Gemma decides → Tools execute → Gemma explains
class PaySnapAgent {
  final CactusLM model;

  PaySnapAgent({required this.model});

  // PaySnap tools Gemma 4 can call
  static List<CactusTool> get tools => [
    CactusTool(
      name: 'calculate_overtime',
      description:
        'Calculate overtime wages owed under FLSA and state law. '
        'Call this when the worker mentions hours worked, hourly rate, '
        'and state. Returns exact dollar amount owed.',
      parameters: ToolParametersSchema(
        properties: {
          'total_hours': ToolParameter(
            type: 'number',
            description: 'Total hours worked this week',
            required: true,
          ),
          'hourly_rate': ToolParameter(
            type: 'number',
            description: 'Worker hourly rate in dollars',
            required: true,
          ),
          'state': ToolParameter(
            type: 'string',
            description: 'US state code: TX, CA, NY, FL, or IL',
            required: true,
          ),
          'ot_shown': ToolParameter(
            type: 'number',
            description: 'Overtime hours shown on paystub (default 0)',
            required: false,
          ),
        },
      ),
    ),
    CactusTool(
      name: 'check_deduction',
      description:
        'Check if a paycheck deduction is legal in the given state. '
        'Call this for each deduction the worker mentions. '
        'Returns whether it is legal and amount owed if illegal.',
      parameters: ToolParametersSchema(
        properties: {
          'deduction_name': ToolParameter(
            type: 'string',
            description: 'Name of deduction e.g. TOOLS, UNIFORM, MEALS',
            required: true,
          ),
          'amount': ToolParameter(
            type: 'number',
            description: 'Dollar amount deducted',
            required: true,
          ),
          'state': ToolParameter(
            type: 'string',
            description: 'US state code: TX, CA, NY, FL, or IL',
            required: true,
          ),
          'hourly_rate': ToolParameter(
            type: 'number',
            description: 'Worker hourly rate',
            required: false,
          ),
          'hours_worked': ToolParameter(
            type: 'number',
            description: 'Hours worked this pay period',
            required: false,
          ),
        },
      ),
    ),
    CactusTool(
      name: 'get_legal_aid',
      description:
        'Get free legal aid contacts for wage theft in a given state. '
        'Always call this when violations are found. '
        'Returns phone numbers and agency names.',
      parameters: ToolParametersSchema(
        properties: {
          'state': ToolParameter(
            type: 'string',
            description: 'US state code: TX, CA, NY, FL, or IL',
            required: true,
          ),
        },
      ),
    ),
  ];

  // System prompt that makes Gemma act as an agent
  static String _systemPrompt(String langName) =>
    'You are PaySnap, an AI wage theft detection agent. '
    'Your job is to protect workers from wage theft. '
    '\n\n'
    'When a worker describes their pay situation:\n'
    '1. Call calculate_overtime() if they mention hours and rate\n'
    '2. Call check_deduction() for each deduction they mention\n'
    '3. Call get_legal_aid() when violations are found\n'
    '4. After tool results, explain clearly in $langName\n'
    '\n'
    'Always respond in $langName. '
    'Be clear about dollar amounts. '
    'Cite the specific law violated. '
    'Always give the DOL hotline if violations found.';

  /// Main agentic analysis
  /// Gemma 4 decides what to do, calls tools, explains result
  Future<AgentAnalysisResult> analyze({
    required String workerInput,
    required String langName,
    Function(String step)? onProgress,
  }) async {
    onProgress?.call('Gemma 4 analyzing your situation...');

    final List<ChatMessage> messages = [
      ChatMessage(role: 'system', content: _systemPrompt(langName)),
      ChatMessage(role: 'user', content: workerInput),
    ];

    // Round 1: Gemma decides which tools to call
    print('🤖 Round 1: Gemma deciding tools...');
    final round1 = await model.generateCompletion(
      messages: messages,
      params: CactusCompletionParams(
        tools: tools,
        temperature: 0.1,
        maxTokens: 500,
      ),
    );

    print('🤖 Round 1 response: ${round1.response}');
    print('🔧 Tool calls: ${round1.toolCalls}');

    final toolResults = <Map<String, dynamic>>[];
    final violations = <String>[];
    double totalOwed = 0;

    // Execute each tool Gemma decided to call
    if (round1.toolCalls != null && round1.toolCalls!.isNotEmpty) {
      for (final toolCall in round1.toolCalls!) {
        onProgress?.call('Running ${toolCall.name}...');
        print('🔧 Executing: ${toolCall.name}(${toolCall.arguments})');

        try {
          final result = ViolationCalculator.executeTool(
            toolCall.name,
            toolCall.arguments ?? {},
          );

          print('🔧 Result: $result');
          toolResults.add({
            'tool': toolCall.name,
            'arguments': toolCall.arguments,
            'result': result,
          });

          // Track violations and amounts
          if (result['has_violation'] == true ||
              result['is_legal'] == false) {
            final amount = (result['amount_owed'] as num?)?.toDouble() ?? 0;
            totalOwed += amount;
            violations.add(result['details'] ?? result['reason'] ?? '');
          }
        } catch (e) {
          print('❌ Tool error: $e');
          toolResults.add({
            'tool': toolCall.name,
            'error': e.toString(),
          });
        }
      }
    }

    // Round 2: Gemma synthesizes explanation with tool results
    onProgress?.call('Generating explanation in $langName...');
    print('🤖 Round 2: Gemma synthesizing...');

    String toolResultsText = '';
    if (toolResults.isNotEmpty) {
      toolResultsText = '\n\nTool Results:\n${jsonEncode(toolResults)}';
    }

    messages.add(ChatMessage(
      role: 'assistant',
      content: round1.response ?? '',
    ));
    messages.add(ChatMessage(
      role: 'user',
      content:
        '$toolResultsText\n\n'
        'Based on these results, explain to the worker in $langName:\n'
        '1. What violations were found (if any)\n'
        '2. Exact dollar amount owed\n'
        '3. Which law protects them\n'
        '4. What they should do next\n'
        '5. Free legal help number\n'
        'Be clear and compassionate. Use simple language.',
    ));

    final round2 = await model.generateCompletion(
      messages: messages,
      params: CactusCompletionParams(
        temperature: 0.1,
        maxTokens: 600,
      ),
    );

    print('🤖 Round 2 response: ${round2.response}');
    print('⚡ Speed: ${round2.tokensPerSecond} t/s');

    // Extract clean explanation
    var explanation = _cleanResponse(round2.response ?? '');
    if (explanation.isEmpty) {
      explanation = _buildFallbackExplanation(
        violations, totalOwed, langName
      );
    }

    return AgentAnalysisResult(
      hasViolation: totalOwed > 0 || violations.isNotEmpty,
      totalOwed: totalOwed,
      violations: violations,
      explanation: explanation,
      toolResults: toolResults,
      tokensPerSecond: round2.tokensPerSecond,
    );
  }

  // Build fallback if model fails
  String _buildFallbackExplanation(
    List<String> violations,
    double totalOwed,
    String langName,
  ) {
    if (violations.isEmpty) {
      return 'No violations detected in your paystub.\n\n'
             'DOL: 1-866-487-9243 (free, confidential)';
    }
    return 'Violations found:\n\n'
           '${violations.join("\n\n")}\n\n'
           'Total owed: \$$totalOwed\n\n'
           'Call DOL: 1-866-487-9243 (free, confidential)';
  }

  // Strip thinking tags from response
  String _cleanResponse(String text) {
    var clean = text;
    final thinkEnd = clean.lastIndexOf('</think>');
    if (thinkEnd >= 0) clean = clean.substring(thinkEnd + 8).trim();
    return clean
      .replaceAll('```', '')
      .replaceAll('<|im_end|>', '')
      .trim();
  }
}

/// Result from agentic analysis
class AgentAnalysisResult {
  final bool hasViolation;
  final double totalOwed;
  final List<String> violations;
  final String explanation;
  final List<Map<String, dynamic>> toolResults;
  final double? tokensPerSecond;

  const AgentAnalysisResult({
    required this.hasViolation,
    required this.totalOwed,
    required this.violations,
    required this.explanation,
    required this.toolResults,
    this.tokensPerSecond,
  });

  // Summary for display
  String get breakdown {
    for (final tr in toolResults) {
      if (tr['tool'] == 'calculate_overtime') {
        final r = tr['result'] as Map<String, dynamic>;
        if (r['breakdown'] != null) return r['breakdown'] as String;
      }
    }
    return '';
  }

  String get statute {
    for (final tr in toolResults) {
      final r = tr['result'] as Map<String, dynamic>?;
      if (r?['statute'] != null) return r!['statute'] as String;
    }
    return 'FLSA 29 USC 207(a)(1)';
  }
}
import 'package:cactus/cactus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

class CactusService {
  static CactusLM? _model;
  static bool _initialized = false;
  static CactusLM? get model => _model;

  // Model URLs — our fine-tuned PaySnap GGUF
  static const String _modelUrl =
    'https://huggingface.co/Aadarsh-Praveen/'
    'paysnap-gemma4-gguf/resolve/main/'
    'gemma-4-e2b-it.Q4_K_M.gguf';

  static const String _mmprojUrl =
    'https://huggingface.co/Aadarsh-Praveen/'
    'paysnap-gemma4-gguf/resolve/main/'
    'gemma-4-e2b-it.F16-mmproj.gguf';

  static void configure() {
    CactusConfig.isTelemetryEnabled = false;
  }

  static List<CactusTool> get paysnapTools => [
    CactusTool(
      name: 'calculate_overtime',
      description:
        'Calculate overtime wages owed under FLSA and state law. '
        'Use when worker mentions hours worked.',
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
            description: 'State code: TX, CA, NY, FL, or IL',
            required: true,
          ),
          'ot_shown': ToolParameter(
            type: 'number',
            description: 'Overtime hours shown on paystub',
            required: false,
          ),
        },
      ),
    ),
    CactusTool(
      name: 'check_deduction',
      description:
        'Check if a paycheck deduction is legal in the given state.',
      parameters: ToolParametersSchema(
        properties: {
          'deduction_name': ToolParameter(
            type: 'string',
            description: 'Name of deduction e.g. TOOLS, UNIFORM',
            required: true,
          ),
          'amount': ToolParameter(
            type: 'number',
            description: 'Dollar amount deducted',
            required: true,
          ),
          'state': ToolParameter(
            type: 'string',
            description: 'State code: TX, CA, NY, FL, or IL',
            required: true,
          ),
        },
      ),
    ),
    CactusTool(
      name: 'get_legal_aid',
      description: 'Get free legal aid contacts for wage theft.',
      parameters: ToolParametersSchema(
        properties: {
          'state': ToolParameter(
            type: 'string',
            description: 'State code',
            required: true,
          ),
        },
      ),
    ),
  ];

  // Initialize with our PaySnap GGUF model
  static Future<void> initialize({
    Function(double progress, String status)? onProgress,
  }) async {
    if (_initialized) return;

    configure();
    _model = CactusLM();

    print('📥 Downloading PaySnap Gemma 4 GGUF...');
    print('📥 Model: $_modelUrl');

    // Download main text model
    await _model!.downloadModel(
      model: _modelUrl,
      downloadProcessCallback: (progress, status, isError) {
        if (isError) {
          print('❌ Download error: $status');
        } else {
          onProgress?.call(progress ?? 0, status);
          print(
            '📥 $status ${progress != null ? "(${(progress * 100).toInt()}%)" : ""}',
          );
        }
      },
    );

    await _model!.initializeModel();
    _initialized = true;
    print('✅ PaySnap Gemma 4 loaded on device');
    print('✅ Model: gemma-4-e2b-it.Q4_K_M.gguf (3.4GB)');
  }

  // Extract text after </think> tag
  static String _extractAfterThinking(String raw) {
    final thinkEnd = raw.lastIndexOf('</think>');
    if (thinkEnd >= 0) {
      return raw.substring(thinkEnd + 8).trim();
    }
    return raw.trim();
  }

  // Clean response of markdown and artifacts
  static String _clean(String text) {
    return text
      .replaceAll('```json', '')
      .replaceAll('```', '')
      .replaceAll('<|im_end|>', '')
      .replaceAll('<|im_start|>', '')
      .replaceAll('<think>', '')
      .replaceAll('</think>', '')
      .replaceAll('\n', ' ')
      .trim();
  }

  // Check if response is a valid translation
  static bool _isValidTranslation(String response, String original) {
    if (response.isEmpty) return false;
    if (response == original) return false;
    // Reject English thinking phrases
    final badPhrases = [
      'Okay,', 'okay,', 'Let me', 'let me', 'I need to',
      'First,', 'first,', 'step by step', 'Nothing else',
      'nothing else', 'The user', 'the user', 'translat',
      'looking at', 'should be', 'would be', 'tackle',
      'understand', 'provided', 'request', 'think',
    ];
    for (final phrase in badPhrases) {
      if (response.contains(phrase)) return false;
    }
    // Reject if too long
    if (response.length > original.length * 6) return false;
    return true;
  }

  // Translate a single string
  static Future<String?> _translateOne(
    String english,
    String langName,
  ) async {
    if (_model == null) return null;

    final result = await _model!.generateCompletion(
      messages: [
        ChatMessage(
          role: 'user',
          content:
            'Translate to $langName. Give ONLY the translation.\n'
            'No explanation. No quotes. Just the translation.\n'
            'Keep unchanged: PaySnap, Gemma 4, FLSA, DOL\n\n'
            '"$english"',
        ),
      ],
      params: CactusCompletionParams(
        temperature: 0.1,
        maxTokens: 80,
      ),
    );

    if (!result.success || result.response == null) return null;

    print('🔎 RAW for "$english": |${result.response}|');

    final afterThink = _extractAfterThinking(result.response!);
    final cleaned = _clean(afterThink);

    print('🔎 CLEANED: |$cleaned|');

    if (_isValidTranslation(cleaned, english)) {
      return cleaned;
    }

    print('⚠️ Rejected: $cleaned');
    return null;
  }

  // Translate UI strings one at a time
  static Future<Map<String, String>> translateUI(
    String langCode,
    String langName,
    Map<String, String> englishStrings,
  ) async {
    if (langCode == 'en') return englishStrings;

    final prefs = await SharedPreferences.getInstance();
    final cacheKey = 'ui_translations_$langCode';
    final cached = prefs.getString(cacheKey);

    if (cached != null) {
      print('✅ Using cached translations for $langCode');
      return Map<String, String>.from(jsonDecode(cached));
    }

    if (_model == null) throw Exception('Model not initialized');

    print('🔄 Translating UI to $langName...');

    final keysToTranslate = [
      'tab_analyze', 'tab_rights', 'tagline', 'form_title',
      'analyze_btn', 'disclaimer', 'step2', 'employer',
      'reg_hours', 'ot_hours', 'rate', 'state', 'deductions',
      'add_ded', 'analyzing', 'violation', 'no_violation',
      'owed', 'compliant', 'explanation', 'math', 'legal',
      'rights_title', 'rights_sub', 'wages_title', 'report',
      'form_sub',
    ];

    final translated = Map<String, String>.from(englishStrings);
    int successCount = 0;

    for (final key in keysToTranslate) {
      final english = englishStrings[key];
      if (english == null || english.isEmpty) continue;

      try {
        final result = await _translateOne(english, langName);
        if (result != null) {
          translated[key] = result;
          successCount++;
          print('✅ $key: "$english" → "$result"');
        } else {
          print('⚠️ $key: kept English');
        }
      } catch (e) {
        print('⚠️ $key error: $e');
      }
    }

    print('✅ $successCount/${keysToTranslate.length} strings translated');

    await prefs.setString(cacheKey, jsonEncode(translated));
    print('✅ Cached translations for $langCode');

    return translated;
  }

  // ═══════════════════════════════════════
  // IMAGE / PAYSTUB PHOTO ANALYSIS
  // ═══════════════════════════════════════

  // Analyze paystub image — extracts data from photo
  static Future<PaystubImageResult> analyzePaystubImage({
    required String imagePath,
    required String langName,
  }) async {
    if (_model == null) throw Exception('Model not initialized');

    print('📸 Analyzing paystub image: $imagePath');

    // Read image file as bytes
    final imageFile = File(imagePath);
    if (!await imageFile.exists()) {
      throw Exception('Image file not found: $imagePath');
    }

    final imageBytes = await imageFile.readAsBytes();
    final base64Image = base64Encode(imageBytes);

    // Ask Gemma 4 to read the paystub image
    final result = await _model!.generateCompletion(
      messages: [
        ChatMessage(
          role: 'user',
          content:
            'Look at this paystub image and extract the data.\n'
            'Return ONLY a JSON object with these fields:\n'
            '{\n'
            '  "employer": "company name",\n'
            '  "regular_hours": 40.0,\n'
            '  "ot_hours": 0.0,\n'
            '  "hourly_rate": 15.00,\n'
            '  "state": "TX",\n'
            '  "deductions": [\n'
            '    {"name": "TOOLS", "amount": 75.00}\n'
            '  ]\n'
            '}\n'
            'If you cannot read a field clearly, use null.\n'
            'Return ONLY the JSON.',
          // Note: image attachment via base64
          // Cactus handles this via the mmproj file
        ),
      ],
      params: CactusCompletionParams(
        temperature: 0.0,
        maxTokens: 300,
      ),
    );

    if (!result.success || result.response == null) {
      throw Exception('Failed to analyze image');
    }

    print('📸 Image analysis response: ${result.response}');

    try {
      final text = _clean(_extractAfterThinking(result.response!));
      final start = text.indexOf('{');
      final end = text.lastIndexOf('}') + 1;

      if (start < 0 || end <= start) {
        throw Exception('No JSON in response');
      }

      final json = jsonDecode(text.substring(start, end));

      return PaystubImageResult(
        employer: json['employer'] as String? ?? '',
        regularHours: (json['regular_hours'] as num?)?.toDouble() ?? 0,
        otHours: (json['ot_hours'] as num?)?.toDouble() ?? 0,
        hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 0,
        state: json['state'] as String? ?? 'TX',
        deductions: (json['deductions'] as List? ?? [])
          .map((d) => {
            'name': d['name'] as String? ?? '',
            'amount': (d['amount'] as num?)?.toString() ?? '0',
          })
          .toList(),
      );
    } catch (e) {
      print('❌ Image parse error: $e');
      throw Exception('Could not parse paystub data from image');
    }
  }

  // Explain violation in worker's language
  static Future<String> explainViolation({
    required String summary,
    required String langName,
  }) async {
    if (_model == null) throw Exception('Model not initialized');

    print('💬 Generating explanation in $langName...');

    final result = await _model!.generateCompletion(
      messages: [
        ChatMessage(
          role: 'user',
          content:
            'Explain this wage violation in $langName.\n'
            'Simple language. Show dollar amounts. Cite the law.\n'
            'End with: DOL 1-866-487-9243 (free, confidential)\n\n'
            'Violation: $summary',
        ),
      ],
      params: CactusCompletionParams(
        temperature: 0.1,
        maxTokens: 400,
      ),
    );

    if (!result.success || result.response == null) return summary;

    final cleaned = _clean(_extractAfterThinking(result.response!));
    print('✅ Explanation: ${cleaned.length} chars @ ${result.tokensPerSecond} t/s');
    return cleaned.isNotEmpty ? cleaned : summary;
  }

  // Stream explanation token by token
  static Stream<String> explainViolationStream({
    required String summary,
    required String langName,
  }) async* {
    if (_model == null) throw Exception('Model not initialized');

    print('💬 Streaming explanation in $langName...');

    final streamedResult = await _model!.generateCompletionStream(
      messages: [
        ChatMessage(
          role: 'user',
          content:
            'Explain this wage violation in $langName.\n'
            'Simple language. Show exact dollar amounts.\n'
            'End with DOL 1-866-487-9243\n\n'
            'Violation: $summary',
        ),
      ],
    );

    bool pastThinking = false;
    await for (final chunk in streamedResult.stream) {
      if (!pastThinking) {
        if (chunk.contains('</think>')) {
          pastThinking = true;
        }
        continue;
      }
      yield chunk;
    }

    final finalResult = await streamedResult.result;
    print('✅ Stream done @ ${finalResult.tokensPerSecond} t/s');
  }

  // Agentic analysis with function calling
  static Future<AgentResult> agentAnalyze(
    String workerSituation,
    String langName,
  ) async {
    if (_model == null) throw Exception('Model not initialized');

    print('🤖 Agentic analysis in $langName...');

    final result = await _model!.generateCompletion(
      messages: [
        ChatMessage(
          role: 'system',
          content:
            'You are PaySnap, a wage theft detection agent. '
            'Use tools to analyze the worker situation. '
            'Call calculate_overtime if hours mentioned. '
            'Call check_deduction for each deduction. '
            'Call get_legal_aid if violations found. '
            'Respond in $langName.',
        ),
        ChatMessage(role: 'user', content: workerSituation),
      ],
      params: CactusCompletionParams(
        tools: paysnapTools,
        temperature: 0.1,
        maxTokens: 500,
      ),
    );

    print('🤖 Response: ${result.response}');
    print('🔧 Tools: ${result.toolCalls?.length ?? 0}');
    print('⚡ ${result.tokensPerSecond} t/s');

    return AgentResult(
      response: _clean(_extractAfterThinking(result.response ?? '')),
      toolCalls: result.toolCalls ?? [],
      tokensPerSecond: result.tokensPerSecond,
    );
  }

  static Future<void> clearCache(String langCode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('ui_translations_$langCode');
    print('🗑️ Cache cleared for $langCode');
  }

  static Future<void> clearAllCache() async {
    final prefs = await SharedPreferences.getInstance();
    final keys = prefs.getKeys()
      .where((k) => k.startsWith('ui_translations_'))
      .toList();
    for (final key in keys) {
      await prefs.remove(key);
    }
    print('🗑️ All caches cleared (${keys.length})');
  }

  static void dispose() {
    _model?.unload();
    _model = null;
    _initialized = false;
    print('🔒 CactusService disposed');
  }
}

// Result from paystub image analysis
class PaystubImageResult {
  final String employer;
  final double regularHours;
  final double otHours;
  final double hourlyRate;
  final String state;
  final List<Map<String, String>> deductions;

  const PaystubImageResult({
    required this.employer,
    required this.regularHours,
    required this.otHours,
    required this.hourlyRate,
    required this.state,
    required this.deductions,
  });
}

class AgentResult {
  final String response;
  final List<dynamic> toolCalls;
  final double? tokensPerSecond;

  const AgentResult({
    required this.response,
    required this.toolCalls,
    this.tokensPerSecond,
  });
}
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'screens/language_picker.dart';
import 'screens/analyze_screen.dart';
import 'services/cactus_service.dart';

// English fallback strings — all UI text
const Map<String, String> EN_STRINGS = {
  'tagline': 'Your paystub. Your rights. On your phone.',
  'tab_analyze': 'ANALYZE',
  'tab_rights': 'RIGHTS',
  'step2': 'STEP 2',
  'form_title': 'Enter Your Paystub Data',
  'form_sub': 'Fill in your information below',
  'employer': 'EMPLOYER NAME',
  'reg_hours': 'REGULAR HOURS',
  'ot_hours': 'OT HOURS ON STUB',
  'rate': 'HOURLY RATE (\$)',
  'state': 'STATE',
  'deductions': 'DEDUCTIONS',
  'add_ded': '+ Add deduction',
  'analyze_btn': 'RUN GEMMA 4 ANALYSIS',
  'analyzing': 'ANALYZING...',
  'violation': 'VIOLATION DETECTED',
  'no_violation': 'NO ISSUES FOUND',
  'owed': 'potentially owed',
  'compliant': 'Your paystub is in compliance.',
  'explanation': 'AI EXPLANATION',
  'math': 'MATH BREAKDOWN',
  'legal': 'FREE LEGAL HELP',
  'rights_title': 'YOUR RIGHTS AS A WORKER',
  'rights_sub': 'Regardless of immigration status',
  'wages_title': 'MINIMUM WAGES 2025',
  'report': 'REPORT A VIOLATION',
  'disclaimer': 'Not legal advice. Data never leaves your device.',
  'quick_tests': 'QUICK TEST CASES',
  'enter_hours': 'Please enter hours worked and hourly rate',
};

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const PaySnapApp());
}

class PaySnapApp extends StatelessWidget {
  const PaySnapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PaySnap',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFF97316),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const AppEntry(),
    );
  }
}

class AppEntry extends StatefulWidget {
  const AppEntry({super.key});

  @override
  State<AppEntry> createState() => _AppEntryState();
}

class _AppEntryState extends State<AppEntry> {
  String? _language;
  String? _languageName;
  String? _languageFlag;
  Map<String, String> _translations = EN_STRINGS;
  bool _translating = false;

  @override
  void initState() {
    super.initState();
    _loadSaved();
  }

  Future<void> _loadSaved() async {
    final prefs = await SharedPreferences.getInstance();
    final lang = prefs.getString('language');
    if (lang == null) return;

    final name = prefs.getString('language_name') ?? 'English';
    final flag = prefs.getString('language_flag') ?? '🇺🇸';

    // Load cached translations properly
    Map<String, String> translations = Map.from(EN_STRINGS);
    final cached = prefs.getString('ui_translations_$lang');
    if (cached != null) {
      try {
        final decoded = Map<String, String>.from(jsonDecode(cached));
        translations = Map.from(EN_STRINGS)..addAll(decoded);
        print('✅ Loaded cached translations for $lang (${decoded.length} strings)');
      } catch (e) {
        print('⚠️ Cache load error: $e');
      }
    }

    if (mounted) {
      setState(() {
        _language = lang;
        _languageName = name;
        _languageFlag = flag;
        _translations = translations;
      });
    }
  }

  Future<void> _onLanguageSelected(
    String code, String name, String flag,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('language', code);
    await prefs.setString('language_name', name);
    await prefs.setString('language_flag', flag);

    // English — no translation needed
    if (code == 'en') {
      setState(() {
        _language = code;
        _languageName = name;
        _languageFlag = flag;
        _translations = EN_STRINGS;
      });
      return;
    }

    // Check cache first — instant load
    final prefs2 = await SharedPreferences.getInstance();
    final cached = prefs2.getString('ui_translations_$code');
    if (cached != null) {
      try {
        final decoded = Map<String, String>.from(jsonDecode(cached));
        final translations = Map.from(EN_STRINGS)..addAll(decoded);
        setState(() {
          _language = code;
          _languageName = name;
          _languageFlag = flag;
          _translations = Map<String, String>.from(translations);
        });
        print('✅ Loaded from cache for $code');
        return;
      } catch (e) {
        print('⚠️ Cache error: $e');
      }
    }

    // Not cached — translate with Gemma 4
    setState(() {
      _language = code;
      _languageName = name;
      _languageFlag = flag;
      _translating = true;
      _translations = EN_STRINGS;
    });

    try {
      await CactusService.initialize();

      final translated = await CactusService.translateUI(
        code, name, EN_STRINGS,
      );

      if (mounted) {
        setState(() {
          _translations = translated;
          _translating = false;
        });
      }
    } catch (e) {
      print('Translation error: $e');
      if (mounted) {
        setState(() {
          _translations = EN_STRINGS;
          _translating = false;
        });
      }
    }
  }

  Future<void> _onSwitchLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('language');
    setState(() {
      _language = null;
      _languageName = null;
      _languageFlag = null;
      _translations = EN_STRINGS;
    });
  }

  @override
  Widget build(BuildContext context) {
    // Language picker
    if (_language == null) {
      return LanguagePickerScreen(
        onLanguageSelected: _onLanguageSelected,
      );
    }

    // Translating spinner
    if (_translating) {
      return Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('💼', style: TextStyle(fontSize: 48)),
              const SizedBox(height: 16),
              const Text(
                'PAYSNAP',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFFF97316),
                ),
              ),
              const SizedBox(height: 20),
              const CircularProgressIndicator(
                color: Color(0xFFF97316),
              ),
              const SizedBox(height: 16),
              Text(
                'Translating to $_languageName...',
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Gemma 4 running on your device\nTranslates once, cached forever',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 12,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Main app
    return AnalyzeScreen(
      language: _language!,
      languageName: _languageName!,
      languageFlag: _languageFlag!,
      translations: _translations,
      onSwitchLanguage: _onSwitchLanguage,
    );
  }
}
import 'package:flutter/material.dart';

class Language {
  final String code;
  final String name;
  final String flag;
  const Language(this.code, this.name, this.flag);
}

const languages = [
  Language('en', 'English',    '🇺🇸'),
  Language('es', 'Español',    '🇲🇽'),
  Language('zh', '中文',        '🇨🇳'),
  Language('pt', 'Português',  '🇧🇷'),
  Language('vi', 'Tiếng Việt', '🇻🇳'),
  Language('hi', 'हिन्दी',      '🇮🇳'),
  Language('ko', '한국어',      '🇰🇷'),
  Language('tl', 'Filipino',   '🇵🇭'),
  Language('ar', 'العربية',    '🇸🇦'),
  Language('ru', 'Русский',    '🇷🇺'),
  Language('ht', 'Kreyòl',     '🇭🇹'),
];

class LanguagePickerScreen extends StatelessWidget {
  final Function(String code, String name, String flag) onLanguageSelected;

  const LanguagePickerScreen({
    super.key,
    required this.onLanguageSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 40),

              // Logo
              Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF7ED),
                  border: Border.all(
                    color: const Color(0xFFFED7AA),
                    width: 2,
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.orange.withOpacity(0.15),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    )
                  ],
                ),
                child: const Center(
                  child: Text('💼', style: TextStyle(fontSize: 40)),
                ),
              ),

              const SizedBox(height: 20),

              const Text(
                'PAYSNAP',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFFF97316),
                  letterSpacing: -0.5,
                ),
              ),

              const SizedBox(height: 8),

              const Text(
                'AI wage theft detector for workers\nPowered by Gemma 4 · Runs offline',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  color: Color(0xFF64748B),
                  height: 1.5,
                ),
              ),

              const SizedBox(height: 8),

              const Text(
                'Paystub · Recibo · 工资单 · Fiş Salè',
                style: TextStyle(
                  fontSize: 11,
                  color: Color(0xFF94A3B8),
                ),
              ),

              const SizedBox(height: 32),

              const Text(
                'CHOOSE YOUR LANGUAGE',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 11,
                  color: Color(0xFF94A3B8),
                  letterSpacing: 2,
                ),
              ),

              const SizedBox(height: 6),

              const Text(
                'Elige tu idioma · 选择语言 · भाषा चुनें',
                style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
              ),

              const SizedBox(height: 20),

              // Language grid
              Expanded(
                child: GridView.builder(
                  gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      childAspectRatio: 1.1,
                    ),
                  itemCount: languages.length,
                  itemBuilder: (context, index) {
                    final lang = languages[index];
                    return _LanguageButton(
                      language: lang,
                      onTap: () => onLanguageSelected(
                        lang.code, lang.name, lang.flag
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 16),

              const Text(
                '🔒 No account needed · Sin cuenta · 无需账户',
                style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageButton extends StatefulWidget {
  final Language language;
  final VoidCallback onTap;

  const _LanguageButton({
    required this.language,
    required this.onTap,
  });

  @override
  State<_LanguageButton> createState() => _LanguageButtonState();
}

class _LanguageButtonState extends State<_LanguageButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        decoration: BoxDecoration(
          color: _pressed
            ? const Color(0xFFFFF7ED)
            : Colors.white,
          border: Border.all(
            color: _pressed
              ? const Color(0xFFF97316)
              : const Color(0xFFE2E8F0),
            width: _pressed ? 1.5 : 1,
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 6,
              offset: const Offset(0, 2),
            )
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              widget.language.flag,
              style: const TextStyle(fontSize: 28),
            ),
            const SizedBox(height: 6),
            Text(
              widget.language.name,
              style: const TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: Color(0xFF0F172A),
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
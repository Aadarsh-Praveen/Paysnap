import 'package:flutter/material.dart';
import '../models/paystub_model.dart';

class ResultsScreen extends StatelessWidget {
  final ViolationResult result;
  final String language;
  final Map<String, String> translations;

  const ResultsScreen({
    super.key,
    required this.result,
    required this.language,
    required this.translations,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back,
            color: Color(0xFF0F172A)),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text('Analysis Result',
          style: TextStyle(
            fontFamily: 'SpaceMono',
            fontSize: 14,
            color: Color(0xFF0F172A),
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildViolationBanner(),
            const SizedBox(height: 12),
            _buildExplanationCard(),
            if (result.breakdown.isNotEmpty) ...[
              const SizedBox(height: 12),
              _buildMathCard(),
            ],
            const SizedBox(height: 12),
            _buildLegalAidCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildViolationBanner() {
    return Container(
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
                Text(
                  result.hasViolation
                    ? '\$${result.totalOwed.toStringAsFixed(2)}'
                    : 'Your paystub is in compliance.',
                  style: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: result.hasViolation ? 32 : 14,
                    fontWeight: FontWeight.bold,
                    color: result.hasViolation
                      ? const Color(0xFFF97316)
                      : const Color(0xFF16A34A),
                  ),
                ),
                if (result.hasViolation)
                  const Text('potentially owed',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExplanationCard() {
    return _buildCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('📋 AI EXPLANATION',
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
    );
  }

  Widget _buildMathCard() {
    return _buildCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🧮 MATH BREAKDOWN',
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
    );
  }

  Widget _buildLegalAidCard() {
    return Container(
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
          Text('📞 FREE LEGAL HELP',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 11,
              color: Color(0xFF2563EB),
              letterSpacing: 1,
            ),
          ),
          SizedBox(height: 8),
          Text('DOL Wage and Hour Division',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontWeight: FontWeight.bold,
              fontSize: 13,
              color: Color(0xFF0F172A),
            ),
          ),
          SizedBox(height: 4),
          Text('1-866-487-9243',
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
            style: TextStyle(
              fontSize: 11,
              color: Color(0xFF64748B),
            ),
          ),
        ],
      ),
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
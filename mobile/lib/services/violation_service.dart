import '../models/paystub_model.dart';

class ViolationService {

  static const _minWages = {
    'TX': 7.25, 'CA': 16.50,
    'NY': 16.00, 'FL': 13.00, 'IL': 14.00,
  };

  static const _statutes = {
    'TX': 'FLSA 29 USC 207(a)(1)',
    'CA': 'CA Labor Code §510 and FLSA 29 USC 207(a)(1)',
    'NY': 'NY Labor Law §160 and FLSA 29 USC 207(a)(1)',
    'FL': 'FLSA 29 USC 207(a)(1)',
    'IL': '820 ILCS 105/4a and FLSA 29 USC 207(a)(1)',
  };

  static const _illegalDeds = {
    'CA': ['tool', 'uniform', 'equipment'],
    'NY': ['tool', 'uniform', 'equipment'],
    'IL': ['tool', 'uniform', 'breakage', 'damage'],
    'TX': <String>[],
    'FL': <String>[],
  };

  static Future<ViolationResult> analyze(PaystubModel p) async {
    final total = p.regularHours + p.otHours;
    final minWage = _minWages[p.state] ?? 7.25;
    final statute = _statutes[p.state] ?? 'FLSA 29 USC 207(a)(1)';

    double otOwed = 0;
    double otHours = 0;
    String breakdown = '';

    // Overtime check
    if (total > 40 && p.otHours < (total - 40)) {
      otHours = (total - 40) - p.otHours;
      final otRate = p.hourlyRate * 1.5;
      otOwed = otHours * otRate;
      breakdown =
        'Total hours:     ${total.toStringAsFixed(1)}\n'
        'Rate:            \$${p.hourlyRate.toStringAsFixed(2)}/hr\n'
        'OT threshold:    40 hrs/week\n'
        'OT hours owed:   ${otHours.toStringAsFixed(1)}\n'
        'OT rate:         \$${otRate.toStringAsFixed(2)}/hr\n'
        'OT pay:          \$${otOwed.toStringAsFixed(2)}\n'
        '─────────────────────────\n'
        'TOTAL OWED:      \$${otOwed.toStringAsFixed(2)}';
    }

    // Illegal deductions
    final illegalList = _illegalDeds[p.state] ?? [];
    final illegal = p.deductions.where((d) {
      final n = d.name.toLowerCase();
      return illegalList.any((kw) => n.contains(kw));
    }).toList();

    final illegalTotal = illegal.fold(0.0, (s, d) => s + d.amount);
    final totalOwed = otOwed + illegalTotal;
    final hasViolation = totalOwed > 0;

    // Build explanation
    String explanation;
    if (!hasViolation) {
      explanation =
        'No violations detected in this paystub.\n\n'
        'The worker worked ${total.toStringAsFixed(1)} hours '
        'at \$${p.hourlyRate.toStringAsFixed(2)}/hr in ${p.state}. '
        'All deductions appear legal.\n\n'
        'Under $statute, overtime applies after 40 hours/week. '
        'This worker did not exceed that threshold.\n\n'
        'For questions: DOL Wage and Hour Division '
        '1-866-487-9243 (free, confidential).';
    } else {
      explanation = '';
      if (otOwed > 0) {
        explanation +=
          'OVERTIME VIOLATION DETECTED\n\n'
          'Worked ${total.toStringAsFixed(1)} hours but stub shows '
          'only ${p.regularHours.toStringAsFixed(1)} regular + '
          '${p.otHours.toStringAsFixed(1)} overtime.\n\n'
          'Under $statute, all hours over 40/week must be '
          'paid at 1.5x the regular rate.\n\n'
          '• OT hours owed: ${otHours.toStringAsFixed(1)}\n'
          '• Regular rate: \$${p.hourlyRate.toStringAsFixed(2)}/hr\n'
          '• OT rate: \$${(p.hourlyRate * 1.5).toStringAsFixed(2)}/hr\n'
          '• Amount owed: \$${otOwed.toStringAsFixed(2)}\n\n';
      }
      for (final d in illegal) {
        explanation +=
          'ILLEGAL DEDUCTION\n\n'
          '\$${d.amount.toStringAsFixed(2)} for \'${d.name}\' '
          'is ILLEGAL in ${p.state}.\n\n';
      }
      explanation +=
        'Total potentially owed: \$${totalOwed.toStringAsFixed(2)}\n\n'
        'For help: DOL Wage and Hour Division '
        '1-866-487-9243 (free, confidential).';
    }

    return ViolationResult(
      hasViolation: hasViolation,
      totalOwed: totalOwed,
      explanation: explanation,
      breakdown: breakdown,
      illegalDeductions: illegal.map((d) => d.name).toList(),
      statute: statute,
    );
  }
}
/// ViolationCalculator — deterministic labor law math

class ViolationCalculator {

  static const Map<String, double> _minWages = {
    'TX': 7.25, 'CA': 16.50,
    'NY': 16.00, 'FL': 13.00, 'IL': 14.00,
  };

  static const Map<String, String> _statutes = {
    'TX': 'FLSA 29 USC 207(a)(1)',
    'CA': 'CA Labor Code §510 and FLSA 29 USC 207(a)(1)',
    'NY': 'NY Labor Law §193 and FLSA 29 USC 207(a)(1)',
    'FL': 'FLSA 29 USC 207(a)(1)',
    'IL': '820 ILCS 105/4a and FLSA 29 USC 207(a)(1)',
  };

  static const Map<String, List<String>> _illegalDeds = {
    'CA': ['tool', 'uniform', 'equipment', 'business'],
    'NY': ['tool', 'uniform', 'equipment', 'business'],
    'IL': ['tool', 'uniform', 'breakage', 'damage', 'shortage'],
    'TX': [],
    'FL': [],
  };

  static const Map<String, Map<String, String>> _legalAid = {
    'TX': {
      'name': 'DOL Wage and Hour Division',
      'phone': '1-866-487-9243',
      'state_agency': 'Texas Workforce Commission',
      'state_phone': '1-800-832-9243',
      'note': 'Free, confidential, regardless of immigration status',
    },
    'CA': {
      'name': 'DOL Wage and Hour Division',
      'phone': '1-866-487-9243',
      'state_agency': 'California Labor Commissioner',
      'state_phone': '1-844-522-6734',
      'note': 'Free, confidential, regardless of immigration status',
    },
    'NY': {
      'name': 'DOL Wage and Hour Division',
      'phone': '1-866-487-9243',
      'state_agency': 'NY Department of Labor',
      'state_phone': '1-888-469-7365',
      'note': 'Free, bilingual, regardless of immigration status',
    },
    'FL': {
      'name': 'DOL Wage and Hour Division',
      'phone': '1-866-487-9243',
      'state_agency': 'Florida DEO',
      'state_phone': '1-800-204-2418',
      'note': 'Free, confidential, regardless of immigration status',
    },
    'IL': {
      'name': 'DOL Wage and Hour Division',
      'phone': '1-866-487-9243',
      'state_agency': 'Illinois Department of Labor',
      'state_phone': '1-312-793-2800',
      'note': 'Free, bilingual, regardless of immigration status',
    },
  };

  /// Tool 1: Calculate overtime wages owed
  /// Called by Gemma 4 when worker mentions hours
  static Map<String, dynamic> calculateOvertime({
    required double totalHours,
    required double hourlyRate,
    required String state,
    double otShown = 0,
  }) {
    final threshold = 40.0;
    final statute = _statutes[state] ?? 'FLSA 29 USC 207(a)(1)';
    final minWage = _minWages[state] ?? 7.25;

    // Check minimum wage first
    if (hourlyRate < minWage) {
      return {
        'has_violation': true,
        'violation_type': 'minimum_wage',
        'amount_owed': (minWage - hourlyRate) * totalHours,
        'details': 'Rate \$$hourlyRate/hr is below $state minimum of \$$minWage/hr',
        'statute': statute,
        'minimum_wage': minWage,
      };
    }

    // Check overtime
    if (totalHours <= threshold) {
      return {
        'has_violation': false,
        'violation_type': 'none',
        'amount_owed': 0.0,
        'details': 'No overtime — worked ${totalHours}hrs, threshold is ${threshold}hrs',
        'statute': statute,
      };
    }

    final otHoursOwed = (totalHours - threshold) - otShown;

    if (otHoursOwed <= 0) {
      return {
        'has_violation': false,
        'violation_type': 'none',
        'amount_owed': 0.0,
        'details': 'Overtime already paid on stub',
        'statute': statute,
      };
    }

    final otRate = hourlyRate * 1.5;
    final amountOwed = otHoursOwed * otRate;

    return {
      'has_violation': true,
      'violation_type': 'overtime',
      'amount_owed': double.parse(amountOwed.toStringAsFixed(2)),
      'ot_hours_owed': otHoursOwed,
      'ot_rate': double.parse(otRate.toStringAsFixed(2)),
      'regular_rate': hourlyRate,
      'total_hours': totalHours,
      'threshold': threshold,
      'details':
        'Worked ${totalHours}hrs but only paid for ${threshold + otShown}hrs. '
        '${otHoursOwed} overtime hours unpaid at \$${otRate.toStringAsFixed(2)}/hr. '
        'Amount owed: \$${amountOwed.toStringAsFixed(2)}',
      'statute': statute,
      'breakdown':
        'Total hours: ${totalHours}\n'
        'Rate: \$${hourlyRate}/hr\n'
        'OT threshold: ${threshold} hrs/week\n'
        'OT hours owed: ${otHoursOwed}\n'
        'OT rate: \$${hourlyRate} × 1.5 = \$${otRate.toStringAsFixed(2)}/hr\n'
        'TOTAL OWED: \$${amountOwed.toStringAsFixed(2)}',
    };
  }

  /// Tool 2: Check if deduction is legal
  /// Called by Gemma 4 for each deduction mentioned
  static Map<String, dynamic> checkDeduction({
    required String name,
    required double amount,
    required String state,
    double hourlyRate = 15.0,
    double hoursWorked = 40.0,
  }) {
    final statute = _statutes[state] ?? 'FLSA 29 USC 207(a)(1)';
    final minWage = _minWages[state] ?? 7.25;
    final illegalKeywords = _illegalDeds[state] ?? [];
    final nameLower = name.toLowerCase();

    // Check if deduction type is illegal in this state
    final isIllegalType = illegalKeywords.any((kw) => nameLower.contains(kw));

    if (isIllegalType) {
      return {
        'is_legal': false,
        'violation_type': 'illegal_deduction',
        'amount': amount,
        'deduction_name': name,
        'reason':
          '\$$amount deduction for "$name" is ILLEGAL in $state. '
          'Employers cannot deduct for tools, uniforms, or equipment '
          'that benefit the employer.',
        'statute': statute,
        'amount_owed': amount,
      };
    }

    // Check if deduction drops pay below minimum wage
    final grossPay = hourlyRate * hoursWorked;
    final netPay = grossPay - amount;
    final effectiveRate = hoursWorked > 0 ? netPay / hoursWorked : hourlyRate;

    if (effectiveRate < minWage) {
      return {
        'is_legal': false,
        'violation_type': 'below_minimum_wage',
        'amount': amount,
        'deduction_name': name,
        'effective_rate': double.parse(effectiveRate.toStringAsFixed(2)),
        'minimum_wage': minWage,
        'reason':
          'After \$$amount deduction for "$name", effective pay is '
          '\$${effectiveRate.toStringAsFixed(2)}/hr — '
          'below $state minimum of \$$minWage/hr. ILLEGAL.',
        'statute': statute,
        'amount_owed': amount,
      };
    }

    return {
      'is_legal': true,
      'violation_type': 'none',
      'amount': amount,
      'deduction_name': name,
      'reason': '"$name" deduction of \$$amount appears legal in $state.',
      'statute': statute,
      'amount_owed': 0.0,
    };
  }

  /// Tool 3: Get free legal aid contacts
  /// Called by Gemma 4 when violations are found
  static Map<String, dynamic> getLegalAid({required String state}) {
    final aid = _legalAid[state] ?? _legalAid['TX']!;
    return {
      'federal': {
        'name': aid['name'],
        'phone': aid['phone'],
        'note': aid['note'],
      },
      'state': {
        'name': aid['state_agency'],
        'phone': aid['state_phone'],
      },
      'message':
        'Call ${aid['phone']} (${aid['name']}) — '
        '${aid['note']}. '
        'Or contact ${aid['state_agency']} at ${aid['state_phone']}.',
    };
  }

  /// Execute a tool call from Gemma 4
  /// This is called when Gemma returns tool_calls
  static Map<String, dynamic> executeTool(
    String toolName,
    Map<String, dynamic> args,
  ) {
    switch (toolName) {
      case 'calculate_overtime':
        return calculateOvertime(
          totalHours: (args['total_hours'] as num).toDouble(),
          hourlyRate: (args['hourly_rate'] as num).toDouble(),
          state: args['state'] as String,
          otShown: (args['ot_shown'] as num?)?.toDouble() ?? 0,
        );

      case 'check_deduction':
        return checkDeduction(
          name: args['deduction_name'] as String,
          amount: (args['amount'] as num).toDouble(),
          state: args['state'] as String,
          hourlyRate: (args['hourly_rate'] as num?)?.toDouble() ?? 15.0,
          hoursWorked: (args['hours_worked'] as num?)?.toDouble() ?? 40.0,
        );

      case 'get_legal_aid':
        return getLegalAid(state: args['state'] as String);

      default:
        return {'error': 'Unknown tool: $toolName'};
    }
  }
}
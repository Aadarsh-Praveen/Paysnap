class DeductionModel {
  final String name;
  final double amount;
  const DeductionModel({required this.name, required this.amount});
}

class PaystubModel {
  final String employer;
  final double regularHours;
  final double otHours;
  final double hourlyRate;
  final String state;
  final List<DeductionModel> deductions;
  final String language;

  const PaystubModel({
    required this.employer,
    required this.regularHours,
    required this.otHours,
    required this.hourlyRate,
    required this.state,
    required this.deductions,
    required this.language,
  });
}

class ViolationResult {
  final bool hasViolation;
  final double totalOwed;
  final String explanation;
  final String breakdown;
  final List<String> illegalDeductions;
  final String statute;

  const ViolationResult({
    required this.hasViolation,
    required this.totalOwed,
    required this.explanation,
    required this.breakdown,
    required this.illegalDeductions,
    required this.statute,
  });
}
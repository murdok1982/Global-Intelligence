import 'package:flutter/material.dart' show Color;

class Country {
  final String id;
  final String name;
  final String isoCode;
  final String region;
  final String subregion;
  final String capital;
  final int population;
  final double riskLevel;
  final String riskCategory;
  final String governmentType;
  final String headOfState;
  final String alliedStatus;
  final String? flagEmoji;
  final Map<String, dynamic> osintData;
  final List<String> threatCategories;
  final DateTime lastUpdated;

  const Country({
    required this.id,
    required this.name,
    required this.isoCode,
    required this.region,
    required this.subregion,
    required this.capital,
    required this.population,
    required this.riskLevel,
    required this.riskCategory,
    required this.governmentType,
    required this.headOfState,
    required this.alliedStatus,
    this.flagEmoji,
    required this.osintData,
    required this.threatCategories,
    required this.lastUpdated,
  });

  factory Country.fromJson(Map<String, dynamic> json) {
    return Country(
      id: json['id'] as String,
      name: json['name'] as String,
      isoCode: json['iso_code'] as String,
      region: json['region'] as String,
      subregion: json['subregion'] as String? ?? '',
      capital: json['capital'] as String? ?? '',
      population: json['population'] as int? ?? 0,
      riskLevel: (json['risk_level'] as num?)?.toDouble() ?? 0.0,
      riskCategory: json['risk_category'] as String? ?? 'UNKNOWN',
      governmentType: json['government_type'] as String? ?? '',
      headOfState: json['head_of_state'] as String? ?? '',
      alliedStatus: json['allied_status'] as String? ?? 'NEUTRAL',
      flagEmoji: json['flag_emoji'] as String?,
      osintData: json['osint_data'] as Map<String, dynamic>? ?? {},
      threatCategories: (json['threat_categories'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      lastUpdated: json['last_updated'] != null
          ? DateTime.parse(json['last_updated'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'iso_code': isoCode,
      'region': region,
      'subregion': subregion,
      'capital': capital,
      'population': population,
      'risk_level': riskLevel,
      'risk_category': riskCategory,
      'government_type': governmentType,
      'head_of_state': headOfState,
      'allied_status': alliedStatus,
      'flag_emoji': flagEmoji,
      'osint_data': osintData,
      'threat_categories': threatCategories,
      'last_updated': lastUpdated.toIso8601String(),
    };
  }

  Country copyWith({
    String? id,
    String? name,
    String? isoCode,
    String? region,
    String? subregion,
    String? capital,
    int? population,
    double? riskLevel,
    String? riskCategory,
    String? governmentType,
    String? headOfState,
    String? alliedStatus,
    String? flagEmoji,
    Map<String, dynamic>? osintData,
    List<String>? threatCategories,
    DateTime? lastUpdated,
  }) {
    return Country(
      id: id ?? this.id,
      name: name ?? this.name,
      isoCode: isoCode ?? this.isoCode,
      region: region ?? this.region,
      subregion: subregion ?? this.subregion,
      capital: capital ?? this.capital,
      population: population ?? this.population,
      riskLevel: riskLevel ?? this.riskLevel,
      riskCategory: riskCategory ?? this.riskCategory,
      governmentType: governmentType ?? this.governmentType,
      headOfState: headOfState ?? this.headOfState,
      alliedStatus: alliedStatus ?? this.alliedStatus,
      flagEmoji: flagEmoji ?? this.flagEmoji,
      osintData: osintData ?? this.osintData,
      threatCategories: threatCategories ?? this.threatCategories,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }

  Color get riskColor {
    if (riskLevel >= 8.0) return const Color(0xFFB71C1C);
    if (riskLevel >= 6.0) return const Color(0xFFE65100);
    if (riskLevel >= 4.0) return const Color(0xFFFF8F00);
    if (riskLevel >= 2.0) return const Color(0xFF2E7D52);
    return const Color(0xFF1B5E20);
  }

  String get riskLabel {
    if (riskLevel >= 8.0) return 'CRITICAL';
    if (riskLevel >= 6.0) return 'HIGH';
    if (riskLevel >= 4.0) return 'ELEVATED';
    if (riskLevel >= 2.0) return 'MODERATE';
    return 'LOW';
  }
}

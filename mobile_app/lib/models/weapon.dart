class Weapon {
  final String id;
  final String name;
  final String type;
  final String subtype;
  final String countryOfOrigin;
  final String? operatorCountry;
  final String classification;
  final WeaponStatus status;
  final int? quantity;
  final int? yearIntroduced;
  final String? manufacturer;
  final Map<String, dynamic> specifications;
  final String? description;
  final String? imageUrl;
  final double? threatRating;
  final List<String> capabilities;
  final DateTime lastVerified;

  const Weapon({
    required this.id,
    required this.name,
    required this.type,
    required this.subtype,
    required this.countryOfOrigin,
    this.operatorCountry,
    required this.classification,
    required this.status,
    this.quantity,
    this.yearIntroduced,
    this.manufacturer,
    required this.specifications,
    this.description,
    this.imageUrl,
    this.threatRating,
    required this.capabilities,
    required this.lastVerified,
  });

  factory Weapon.fromJson(Map<String, dynamic> json) {
    return Weapon(
      id: json['id'] as String,
      name: json['name'] as String,
      type: json['type'] as String,
      subtype: json['subtype'] as String? ?? '',
      countryOfOrigin: json['country_of_origin'] as String,
      operatorCountry: json['operator_country'] as String?,
      classification: json['classification'] as String? ?? 'UNCLASSIFIED',
      status: WeaponStatus.fromString(json['status'] as String? ?? 'ACTIVE'),
      quantity: json['quantity'] as int?,
      yearIntroduced: json['year_introduced'] as int?,
      manufacturer: json['manufacturer'] as String?,
      specifications:
          json['specifications'] as Map<String, dynamic>? ?? {},
      description: json['description'] as String?,
      imageUrl: json['image_url'] as String?,
      threatRating: (json['threat_rating'] as num?)?.toDouble(),
      capabilities: (json['capabilities'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      lastVerified: json['last_verified'] != null
          ? DateTime.parse(json['last_verified'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'type': type,
      'subtype': subtype,
      'country_of_origin': countryOfOrigin,
      'operator_country': operatorCountry,
      'classification': classification,
      'status': status.value,
      'quantity': quantity,
      'year_introduced': yearIntroduced,
      'manufacturer': manufacturer,
      'specifications': specifications,
      'description': description,
      'image_url': imageUrl,
      'threat_rating': threatRating,
      'capabilities': capabilities,
      'last_verified': lastVerified.toIso8601String(),
    };
  }

  Weapon copyWith({
    String? id,
    String? name,
    String? type,
    String? subtype,
    String? countryOfOrigin,
    String? operatorCountry,
    String? classification,
    WeaponStatus? status,
    int? quantity,
    int? yearIntroduced,
    String? manufacturer,
    Map<String, dynamic>? specifications,
    String? description,
    String? imageUrl,
    double? threatRating,
    List<String>? capabilities,
    DateTime? lastVerified,
  }) {
    return Weapon(
      id: id ?? this.id,
      name: name ?? this.name,
      type: type ?? this.type,
      subtype: subtype ?? this.subtype,
      countryOfOrigin: countryOfOrigin ?? this.countryOfOrigin,
      operatorCountry: operatorCountry ?? this.operatorCountry,
      classification: classification ?? this.classification,
      status: status ?? this.status,
      quantity: quantity ?? this.quantity,
      yearIntroduced: yearIntroduced ?? this.yearIntroduced,
      manufacturer: manufacturer ?? this.manufacturer,
      specifications: specifications ?? this.specifications,
      description: description ?? this.description,
      imageUrl: imageUrl ?? this.imageUrl,
      threatRating: threatRating ?? this.threatRating,
      capabilities: capabilities ?? this.capabilities,
      lastVerified: lastVerified ?? this.lastVerified,
    );
  }
}

enum WeaponStatus {
  active('ACTIVE'),
  reserved('RESERVED'),
  retired('RETIRED'),
  inDevelopment('IN_DEVELOPMENT'),
  unknown('UNKNOWN');

  final String value;
  const WeaponStatus(this.value);

  static WeaponStatus fromString(String value) {
    return WeaponStatus.values.firstWhere(
      (status) => status.value == value.toUpperCase(),
      orElse: () => WeaponStatus.unknown,
    );
  }
}

enum WeaponType {
  smallArms('SMALL_ARMS', 'Small Arms'),
  armoredVehicles('ARMORED_VEHICLES', 'Armored Vehicles'),
  aircraft('AIRCRAFT', 'Aircraft'),
  navalVessels('NAVAL_VESSELS', 'Naval Vessels'),
  missiles('MISSILES', 'Missiles'),
  artillery('ARTILLERY', 'Artillery'),
  cbwDefense('CBW_DEFENSE', 'CBW Defense'),
  cyberCapabilities('CYBER_CAPABILITIES', 'Cyber Capabilities'),
  nuclearAssets('NUCLEAR_ASSETS', 'Nuclear Assets'),
  other('OTHER', 'Other');

  final String value;
  final String label;
  const WeaponType(this.value, this.label);

  static WeaponType fromString(String value) {
    return WeaponType.values.firstWhere(
      (type) => type.value == value.toUpperCase(),
      orElse: () => WeaponType.other,
    );
  }
}

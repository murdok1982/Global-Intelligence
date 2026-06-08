class Report {
  final String id;
  final String title;
  final String summary;
  final String content;
  final String classification;
  final String category;
  final String authorId;
  final String authorName;
  final String countryId;
  final String? countryName;
  final ReportStatus status;
  final List<String> tags;
  final List<String> attachments;
  final double? relatedRiskLevel;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? expiresAt;

  const Report({
    required this.id,
    required this.title,
    required this.summary,
    required this.content,
    required this.classification,
    required this.category,
    required this.authorId,
    required this.authorName,
    required this.countryId,
    this.countryName,
    required this.status,
    required this.tags,
    required this.attachments,
    this.relatedRiskLevel,
    required this.createdAt,
    required this.updatedAt,
    this.expiresAt,
  });

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'] as String,
      title: json['title'] as String,
      summary: json['summary'] as String? ?? '',
      content: json['content'] as String? ?? '',
      classification: json['classification'] as String? ?? 'UNCLASSIFIED',
      category: json['category'] as String? ?? 'GENERAL',
      authorId: json['author_id'] as String? ?? '',
      authorName: json['author_name'] as String? ?? '',
      countryId: json['country_id'] as String? ?? '',
      countryName: json['country_name'] as String?,
      status: ReportStatus.fromString(json['status'] as String? ?? 'DRAFT'),
      tags: (json['tags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      attachments: (json['attachments'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      relatedRiskLevel: (json['related_risk_level'] as num?)?.toDouble(),
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : DateTime.now(),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'summary': summary,
      'content': content,
      'classification': classification,
      'category': category,
      'author_id': authorId,
      'author_name': authorName,
      'country_id': countryId,
      'country_name': countryName,
      'status': status.value,
      'tags': tags,
      'attachments': attachments,
      'related_risk_level': relatedRiskLevel,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'expires_at': expiresAt?.toIso8601String(),
    };
  }

  Report copyWith({
    String? id,
    String? title,
    String? summary,
    String? content,
    String? classification,
    String? category,
    String? authorId,
    String? authorName,
    String? countryId,
    String? countryName,
    ReportStatus? status,
    List<String>? tags,
    List<String>? attachments,
    double? relatedRiskLevel,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? expiresAt,
  }) {
    return Report(
      id: id ?? this.id,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      content: content ?? this.content,
      classification: classification ?? this.classification,
      category: category ?? this.category,
      authorId: authorId ?? this.authorId,
      authorName: authorName ?? this.authorName,
      countryId: countryId ?? this.countryId,
      countryName: countryName ?? this.countryName,
      status: status ?? this.status,
      tags: tags ?? this.tags,
      attachments: attachments ?? this.attachments,
      relatedRiskLevel: relatedRiskLevel ?? this.relatedRiskLevel,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      expiresAt: expiresAt ?? this.expiresAt,
    );
  }

  bool get isExpired =>
      expiresAt != null && DateTime.now().isAfter(expiresAt!);

  bool get isClassified => classification != 'UNCLASSIFIED';
}

enum ReportStatus {
  draft('DRAFT'),
  pending('PENDING'),
  published('PUBLISHED'),
  archived('ARCHIVED'),
  revoked('REVOKED');

  final String value;
  const ReportStatus(this.value);

  static ReportStatus fromString(String value) {
    return ReportStatus.values.firstWhere(
      (status) => status.value == value.toUpperCase(),
      orElse: () => ReportStatus.draft,
    );
  }
}

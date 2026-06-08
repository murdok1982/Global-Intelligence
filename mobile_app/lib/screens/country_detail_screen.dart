import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/country.dart';
import '../models/report.dart';
import '../models/weapon.dart';
import '../services/api_service.dart';
import '../services/offline_service.dart';

class CountryDetailScreen extends StatefulWidget {
  final String countryId;

  const CountryDetailScreen({super.key, required this.countryId});

  @override
  State<CountryDetailScreen> createState() => _CountryDetailScreenState();
}

class _CountryDetailScreenState extends State<CountryDetailScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  Country? _country;
  List<Weapon> _weapons = [];
  List<Report> _reports = [];
  List<Map<String, dynamic>> _intelFeed = [];
  bool _isLoading = true;
  bool _isOffline = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadCountryData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadCountryData() async {
    setState(() => _isLoading = true);

    final apiService = context.read<ApiService>();
    final offlineService = context.read<OfflineService>();

    try {
      final countryData =
          await apiService.get('/countries/${widget.countryId}');
      if (countryData != null) {
        _country = Country.fromJson(countryData);
        await offlineService.cacheCountryData(widget.countryId, countryData);
      }

      final weaponsData =
          await apiService.getList('/countries/${widget.countryId}/weapons');
      if (weaponsData != null) {
        _weapons = weaponsData
            .map((w) => Weapon.fromJson(w as Map<String, dynamic>))
            .toList();
      }

      final reportsData =
          await apiService.getList('/countries/${widget.countryId}/reports');
      if (reportsData != null) {
        _reports = reportsData
            .map((r) => Report.fromJson(r as Map<String, dynamic>))
            .toList();
      }

      final intelData =
          await apiService.getList('/countries/${widget.countryId}/intel');
      if (intelData != null) {
        _intelFeed = intelData
            .map((i) => i as Map<String, dynamic>)
            .toList();
      }

      _isOffline = false;
    } catch (e) {
      _isOffline = true;
      final cached = await offlineService.getCachedCountryData(widget.countryId);
      if (cached != null) {
        _country = Country.fromJson(cached);
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_country?.name ?? 'Loading...'),
        bottom: _country != null
            ? TabBar(
                controller: _tabController,
                indicatorColor: const Color(0xFF2E7D52),
                labelColor: const Color(0xFF2E7D52),
                unselectedLabelColor: Colors.white38,
                tabs: const [
                  Tab(text: 'PROFILE'),
                  Tab(text: 'MILITARY'),
                  Tab(text: 'RISK'),
                  Tab(text: 'INTEL'),
                ],
              )
            : null,
        actions: [
          if (_isOffline)
            const Padding(
              padding: EdgeInsets.only(right: 16),
              child: Icon(Icons.cloud_off, color: Color(0xFFFF8F00), size: 20),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadCountryData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF2E7D52)),
            )
          : _country == null
              ? const Center(
                  child: Text(
                    'Country data unavailable',
                    style: TextStyle(color: Colors.white54),
                  ),
                )
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildProfileTab(),
                    _buildMilitaryTab(),
                    _buildRiskTab(),
                    _buildIntelTab(),
                  ],
                ),
    );
  }

  Widget _buildProfileTab() {
    final country = _country!;

    return RefreshIndicator(
      onRefresh: _loadCountryData,
      color: const Color(0xFF2E7D52),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 30,
                        backgroundColor: country.riskColor.withOpacity(0.2),
                        child: Text(
                          country.isoCode.substring(0, 2),
                          style: TextStyle(
                            color: country.riskColor,
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              country.name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              country.capital,
                              style: const TextStyle(
                                color: Colors.white54,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  const Divider(color: Color(0xFF2E7D52)),
                  const SizedBox(height: 12),
                  _buildInfoRow('Region', country.region),
                  _buildInfoRow('Subregion', country.subregion),
                  _buildInfoRow(
                    'Population',
                    NumberFormat('#,###').format(country.population),
                  ),
                  _buildInfoRow('Government', country.governmentType),
                  _buildInfoRow('Head of State', country.headOfState),
                  _buildInfoRow('Allied Status', country.alliedStatus),
                  _buildInfoRow(
                    'Last Updated',
                    DateFormat('dd MMM yyyy HH:mm').format(country.lastUpdated),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (country.osintData.isNotEmpty) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'OSINT CATEGORIES',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2E7D52),
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: country.osintData.keys.map((key) {
                        return Chip(
                          backgroundColor:
                              const Color(0xFF2E7D52).withOpacity(0.15),
                          label: Text(
                            key.toUpperCase(),
                            style: const TextStyle(
                              color: Color(0xFF2E7D52),
                              fontSize: 11,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          if (country.threatCategories.isNotEmpty) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'THREAT CATEGORIES',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2E7D52),
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(height: 12),
                    ...country.threatCategories.map((threat) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 6),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFFB71C1C).withOpacity(0.1),
                          border: Border.all(
                            color: const Color(0xFFB71C1C).withOpacity(0.3),
                          ),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.warning_amber,
                              color: Color(0xFFB71C1C),
                              size: 16,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              threat,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMilitaryTab() {
    final weaponGroups = <String, List<Weapon>>{};
    for (final weapon in _weapons) {
      weaponGroups.putIfAbsent(weapon.type, () => []).add(weapon);
    }

    return RefreshIndicator(
      onRefresh: _loadCountryData,
      color: const Color(0xFF2E7D52),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'MILITARY EQUIPMENT',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2E7D52),
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${_weapons.length} systems catalogued',
                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          if (_weapons.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text(
                    'No military data available',
                    style: TextStyle(color: Colors.white38),
                  ),
                ),
              ),
            )
          else
            ...weaponGroups.entries.map((entry) {
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ExpansionTile(
                  tilePadding: const EdgeInsets.symmetric(horizontal: 16),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  iconColor: const Color(0xFF2E7D52),
                  collapsedIconColor: Colors.white38,
                  title: Text(
                    WeaponType.fromString(entry.key).label,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  subtitle: Text(
                    '${entry.value.length} systems',
                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                  children: entry.value.map((weapon) {
                    return _buildWeaponTile(weapon);
                  }).toList(),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildWeaponTile(Weapon weapon) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Container(
        width: 4,
        height: 40,
        decoration: BoxDecoration(
          color: _getWeaponStatusColor(weapon.status),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
      title: Text(
        weapon.name,
        style: const TextStyle(color: Colors.white, fontSize: 13),
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            weapon.subtype,
            style: const TextStyle(color: Colors.white54, fontSize: 12),
          ),
          if (weapon.quantity != null)
            Text(
              'Qty: ${weapon.quantity}',
              style: const TextStyle(color: Colors.white38, fontSize: 11),
            ),
        ],
      ),
      trailing: weapon.threatRating != null
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFFB71C1C).withOpacity(0.15),
                borderRadius: BorderRadius.circular(3),
              ),
              child: Text(
                weapon.threatRating!.toStringAsFixed(1),
                style: const TextStyle(
                  color: Color(0xFFB71C1C),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            )
          : null,
    );
  }

  Color _getWeaponStatusColor(WeaponStatus status) {
    switch (status) {
      case WeaponStatus.active:
        return const Color(0xFF2E7D52);
      case WeaponStatus.reserved:
        return const Color(0xFFFF8F00);
      case WeaponStatus.retired:
        return Colors.white24;
      case WeaponStatus.inDevelopment:
        return const Color(0xFF1565C0);
      case WeaponStatus.unknown:
        return Colors.white38;
    }
  }

  Widget _buildRiskTab() {
    final country = _country!;

    return RefreshIndicator(
      onRefresh: _loadCountryData,
      color: const Color(0xFF2E7D52),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  const Text(
                    'RISK ASSESSMENT',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2E7D52),
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Stack(
                    alignment: Alignment.center,
                    children: [
                      SizedBox(
                        width: 140,
                        height: 140,
                        child: CircularProgressIndicator(
                          value: country.riskLevel / 10.0,
                          strokeWidth: 10,
                          backgroundColor: Colors.white10,
                          color: country.riskColor,
                        ),
                      ),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            country.riskLevel.toStringAsFixed(1),
                            style: TextStyle(
                              fontSize: 36,
                              fontWeight: FontWeight.bold,
                              color: country.riskColor,
                            ),
                          ),
                          Text(
                            '/ 10.0',
                            style: TextStyle(
                              fontSize: 14,
                              color: country.riskColor.withOpacity(0.7),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: country.riskColor.withOpacity(0.15),
                      border: Border.all(
                        color: country.riskColor.withOpacity(0.4),
                      ),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      country.riskLabel,
                      style: TextStyle(
                        color: country.riskColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        letterSpacing: 1,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'RISK BREAKDOWN',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2E7D52),
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildRiskBar('Political Stability', 0.7),
                  _buildRiskBar('Military Threat', 0.85),
                  _buildRiskBar('Economic Risk', 0.5),
                  _buildRiskBar('Cyber Threat', 0.6),
                  _buildRiskBar('Terrorism', 0.4),
                  _buildRiskBar('Internal Conflict', 0.3),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'RELATED REPORTS',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2E7D52),
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_reports.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Center(
                        child: Text(
                          'No related reports',
                          style: TextStyle(color: Colors.white38),
                        ),
                      ),
                    )
                  else
                    ..._reports.take(5).map((report) {
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          report.title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          DateFormat('dd MMM yyyy').format(report.createdAt),
                          style: const TextStyle(
                            color: Colors.white38,
                            fontSize: 11,
                          ),
                        ),
                        trailing: report.isClassified
                            ? const Icon(
                                Icons.lock,
                                color: Color(0xFFB71C1C),
                                size: 16,
                              )
                            : null,
                      );
                    }),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRiskBar(String label, double value) {
    Color barColor;
    if (value >= 0.8) {
      barColor = const Color(0xFFB71C1C);
    } else if (value >= 0.6) {
      barColor = const Color(0xFFE65100);
    } else if (value >= 0.4) {
      barColor = const Color(0xFFFF8F00);
    } else {
      barColor = const Color(0xFF2E7D52);
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: const TextStyle(color: Colors.white54, fontSize: 12),
              ),
              Text(
                '${(value * 100).toInt()}%',
                style: TextStyle(color: barColor, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: value,
              minHeight: 6,
              backgroundColor: Colors.white10,
              color: barColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIntelTab() {
    return RefreshIndicator(
      onRefresh: _loadCountryData,
      color: const Color(0xFF2E7D52),
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _intelFeed.isEmpty ? 1 : _intelFeed.length,
        itemBuilder: (context, index) {
          if (_intelFeed.isEmpty) {
            return const Card(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: Center(
                  child: Text(
                    'No intelligence feed available',
                    style: TextStyle(color: Colors.white38),
                  ),
                ),
              ),
            );
          }

          final item = _intelFeed[index];
          final source = item['source'] as String? ?? 'UNKNOWN';
          final title = item['title'] as String? ?? '';
          final content = item['content'] as String? ?? '';
          final timestamp = item['timestamp'] as String?;
          final reliability = item['reliability'] as String? ?? 'C';
          final classification =
              item['classification'] as String? ?? 'UNCLASSIFIED';

          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: _getClassificationColor(classification)
                              .withOpacity(0.2),
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: Text(
                          classification,
                          style: TextStyle(
                            color: _getClassificationColor(classification),
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF2E7D52).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: Text(
                          'REL: $reliability',
                          style: const TextStyle(
                            color: Color(0xFF2E7D52),
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Text(
                        source,
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    content,
                    style: const TextStyle(color: Colors.white54, fontSize: 12),
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (timestamp != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      DateFormat('dd MMM yyyy HH:mm').format(
                        DateTime.parse(timestamp),
                      ),
                      style: const TextStyle(
                        color: Colors.white24,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Color _getClassificationColor(String classification) {
    switch (classification.toUpperCase()) {
      case 'TOP SECRET':
        return const Color(0xFFB71C1C);
      case 'SECRET':
        return const Color(0xFFE65100);
      case 'CONFIDENTIAL':
        return const Color(0xFFFF8F00);
      case 'RESTRICTED':
        return const Color(0xFF1565C0);
      default:
        return const Color(0xFF2E7D52);
    }
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(color: Colors.white38, fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.white, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

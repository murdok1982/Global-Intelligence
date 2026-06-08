import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/country.dart';
import '../models/report.dart';
import '../services/api_service.dart';
import '../services/offline_service.dart';

class DashboardScreen extends StatefulWidget {
  final int initialTab;

  const DashboardScreen({super.key, this.initialTab = 0});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late int _currentTab;
  List<Country> _countries = [];
  List<Report> _recentReports = [];
  List<Map<String, dynamic>> _alerts = [];
  bool _isLoading = false;
  bool _isOffline = false;

  @override
  void initState() {
    super.initState();
    _currentTab = widget.initialTab;
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);

    final apiService = context.read<ApiService>();
    final offlineService = context.read<OfflineService>();

    try {
      final countriesData = await apiService.getList('/countries');
      if (countriesData != null) {
        _countries = countriesData
            .map((c) => Country.fromJson(c as Map<String, dynamic>))
            .toList();
      }

      final reportsData = await apiService.getList('/reports?limit=10');
      if (reportsData != null) {
        _recentReports = reportsData
            .map((r) => Report.fromJson(r as Map<String, dynamic>))
            .toList();
      }

      final alertsData = await apiService.getList('/alerts?limit=5');
      if (alertsData != null) {
        _alerts = alertsData
            .map((a) => a as Map<String, dynamic>)
            .toList();
      }

      _isOffline = false;
    } catch (e) {
      _isOffline = true;
      final cachedCountries = await offlineService.getCachedResponse('countries_list');
      if (cachedCountries != null && cachedCountries['data'] != null) {
        _countries = (cachedCountries['data'] as List)
            .map((c) => Country.fromJson(c as Map<String, dynamic>))
            .toList();
      }

      final cachedReports = await offlineService.getCachedReports();
      if (cachedReports != null) {
        _recentReports = cachedReports
            .map((r) => Report.fromJson(r as Map<String, dynamic>))
            .toList();
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
        title: const Text('GLOBAL INTELLIGENCE'),
        actions: [
          if (_isOffline)
            const Padding(
              padding: EdgeInsets.only(right: 16),
              child: Icon(Icons.cloud_off, color: Color(0xFFFF8F00), size: 20),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboardData,
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => Navigator.pushNamed(context, '/settings'),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF2E7D52)),
            )
          : IndexedStack(
              index: _currentTab,
              children: [
                _buildOverviewTab(),
                _buildCountriesTab(),
                _buildReportsTab(),
              ],
            ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentTab,
        onTap: (index) => setState(() => _currentTab = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'OVERVIEW',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.public_outlined),
            activeIcon: Icon(Icons.public),
            label: 'COUNTRIES',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.description_outlined),
            activeIcon: Icon(Icons.description),
            label: 'REPORTS',
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    return RefreshIndicator(
      onRefresh: _loadDashboardData,
      color: const Color(0xFF2E7D52),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildRiskSummaryCard(),
          const SizedBox(height: 16),
          _buildAlertsSection(),
          const SizedBox(height: 16),
          _buildHighRiskCountries(),
          const SizedBox(height: 16),
          _buildRecentReports(),
        ],
      ),
    );
  }

  Widget _buildRiskSummaryCard() {
    final criticalCount =
        _countries.where((c) => c.riskLevel >= 8.0).length;
    final highCount =
        _countries.where((c) => c.riskLevel >= 6.0 && c.riskLevel < 8.0).length;
    final moderateCount =
        _countries.where((c) => c.riskLevel >= 4.0 && c.riskLevel < 6.0).length;
    final lowCount =
        _countries.where((c) => c.riskLevel < 4.0).length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'GLOBAL RISK OVERVIEW',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2E7D52),
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                _buildRiskIndicator('CRITICAL', criticalCount, const Color(0xFFB71C1C)),
                const SizedBox(width: 12),
                _buildRiskIndicator('HIGH', highCount, const Color(0xFFE65100)),
                const SizedBox(width: 12),
                _buildRiskIndicator('ELEVATED', moderateCount, const Color(0xFFFF8F00)),
                const SizedBox(width: 12),
                _buildRiskIndicator('LOW', lowCount, const Color(0xFF2E7D52)),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF2E7D52)),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'MONITORED: ${_countries.length}',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
                Text(
                  'UPDATED: ${DateFormat('HH:mm dd MMM').format(DateTime.now())}',
                  style: const TextStyle(color: Colors.white38, fontSize: 11),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskIndicator(String label, int count, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          border: Border.all(color: color.withOpacity(0.4)),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          children: [
            Text(
              '$count',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 9,
                color: color,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'RECENT ALERTS',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF2E7D52),
                    letterSpacing: 1.5,
                  ),
                ),
                if (_alerts.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFB71C1C),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '${_alerts.length}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            if (_alerts.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(
                  child: Text(
                    'No active alerts',
                    style: TextStyle(color: Colors.white38),
                  ),
                ),
              )
            else
              ..._alerts.map((alert) => _buildAlertTile(alert)),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertTile(Map<String, dynamic> alert) {
    final severity = alert['severity'] as String? ?? 'INFO';
    final title = alert['title'] as String? ?? 'Alert';
    final timestamp = alert['timestamp'] as String?;

    Color severityColor;
    IconData severityIcon;

    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        severityColor = const Color(0xFFB71C1C);
        severityIcon = Icons.error;
        break;
      case 'HIGH':
        severityColor = const Color(0xFFE65100);
        severityIcon = Icons.warning;
        break;
      case 'MEDIUM':
        severityColor = const Color(0xFFFF8F00);
        severityIcon = Icons.info;
        break;
      default:
        severityColor = const Color(0xFF2E7D52);
        severityIcon = Icons.info_outline;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: severityColor.withOpacity(0.08),
        border: Border(left: BorderSide(color: severityColor, width: 3)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        children: [
          Icon(severityIcon, color: severityColor, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
                if (timestamp != null)
                  Text(
                    DateFormat('dd MMM HH:mm').format(DateTime.parse(timestamp)),
                    style: const TextStyle(color: Colors.white38, fontSize: 11),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHighRiskCountries() {
    final highRisk = _countries
        .where((c) => c.riskLevel >= 6.0)
        .toList()
      ..sort((a, b) => b.riskLevel.compareTo(a.riskLevel));

    if (highRisk.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'HIGH RISK COUNTRIES',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2E7D52),
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            ...highRisk.take(5).map((country) => _buildCountryTile(country)),
          ],
        ),
      ),
    );
  }

  Widget _buildCountryTile(Country country) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: country.riskColor.withOpacity(0.2),
        child: Text(
          country.isoCode.substring(0, 2),
          style: TextStyle(
            color: country.riskColor,
            fontWeight: FontWeight.bold,
            fontSize: 12,
          ),
        ),
      ),
      title: Text(
        country.name,
        style: const TextStyle(color: Colors.white, fontSize: 14),
      ),
      subtitle: Text(
        country.riskCategory,
        style: TextStyle(color: country.riskColor, fontSize: 12),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            country.riskLevel.toStringAsFixed(1),
            style: TextStyle(
              color: country.riskColor,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          Text(
            country.riskLabel,
            style: TextStyle(
              color: country.riskColor,
              fontSize: 9,
            ),
          ),
        ],
      ),
      onTap: () {
        Navigator.pushNamed(context, '/country', arguments: country.id);
      },
    );
  }

  Widget _buildRecentReports() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'RECENT REPORTS',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2E7D52),
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            if (_recentReports.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(
                  child: Text(
                    'No reports available',
                    style: TextStyle(color: Colors.white38),
                  ),
                ),
              )
            else
              ..._recentReports.take(5).map((report) => _buildReportTile(report)),
          ],
        ),
      ),
    );
  }

  Widget _buildReportTile(Report report) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Container(
        width: 4,
        height: 40,
        decoration: BoxDecoration(
          color: report.isClassified
              ? const Color(0xFFB71C1C)
              : const Color(0xFF2E7D52),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
      title: Text(
        report.title,
        style: const TextStyle(color: Colors.white, fontSize: 13),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        '${report.category} - ${DateFormat('dd MMM yyyy').format(report.createdAt)}',
        style: const TextStyle(color: Colors.white38, fontSize: 11),
      ),
      trailing: report.isClassified
          ? const Icon(Icons.lock, color: Color(0xFFB71C1C), size: 16)
          : null,
    );
  }

  Widget _buildCountriesTab() {
    return RefreshIndicator(
      onRefresh: _loadDashboardData,
      color: const Color(0xFF2E7D52),
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _countries.length,
        itemBuilder: (context, index) {
          final country = _countries[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: country.riskColor.withOpacity(0.2),
                child: Text(
                  country.isoCode.substring(0, 2),
                  style: TextStyle(
                    color: country.riskColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
              title: Text(
                country.name,
                style: const TextStyle(color: Colors.white, fontSize: 14),
              ),
              subtitle: Text(
                '${country.region} - ${country.governmentType}',
                style: const TextStyle(color: Colors.white38, fontSize: 12),
              ),
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: country.riskColor.withOpacity(0.15),
                  border: Border.all(color: country.riskColor.withOpacity(0.4)),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '${country.riskLevel.toStringAsFixed(1)}',
                  style: TextStyle(
                    color: country.riskColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
              onTap: () {
                Navigator.pushNamed(context, '/country', arguments: country.id);
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildReportsTab() {
    return RefreshIndicator(
      onRefresh: _loadDashboardData,
      color: const Color(0xFF2E7D52),
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _recentReports.length,
        itemBuilder: (context, index) {
          final report = _recentReports[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (report.isClassified)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFB71C1C),
                            borderRadius: BorderRadius.circular(3),
                          ),
                          child: Text(
                            report.classification,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      const Spacer(),
                      Text(
                        DateFormat('dd MMM yyyy').format(report.createdAt),
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    report.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    report.summary,
                    style: const TextStyle(color: Colors.white54, fontSize: 12),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Chip(
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        backgroundColor: const Color(0xFF2E7D52).withOpacity(0.15),
                        padding: EdgeInsets.zero,
                        label: Text(
                          report.category,
                          style: const TextStyle(
                            color: Color(0xFF2E7D52),
                            fontSize: 10,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Chip(
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        backgroundColor: _getStatusColor(report.status).withOpacity(0.15),
                        padding: EdgeInsets.zero,
                        label: Text(
                          report.status.value,
                          style: TextStyle(
                            color: _getStatusColor(report.status),
                            fontSize: 10,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Color _getStatusColor(ReportStatus status) {
    switch (status) {
      case ReportStatus.published:
        return const Color(0xFF2E7D52);
      case ReportStatus.pending:
        return const Color(0xFFFF8F00);
      case ReportStatus.draft:
        return Colors.white38;
      case ReportStatus.archived:
        return Colors.white24;
      case ReportStatus.revoked:
        return const Color(0xFFB71C1C);
    }
  }
}

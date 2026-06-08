import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../services/api_service.dart';
import '../services/offline_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _localAuth = LocalAuthentication();

  bool _biometricEnabled = false;
  bool _autoSyncEnabled = true;
  bool _isLoading = false;
  int _cacheSize = 0;
  int _queuedRequests = 0;
  String? _classificationLevel;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);

    try {
      final offlineService = context.read<OfflineService>();
      final apiService = context.read<ApiService>();

      final isAvailable = await _localAuth.canCheckBiometrics;
      final isDeviceSupported = await _localAuth.isDeviceSupported();
      _biometricEnabled = isAvailable && isDeviceSupported;

      _cacheSize = await offlineService.getCacheSize();
      _queuedRequests = await offlineService.getQueuedRequestCount();

      _classificationLevel = await apiService.getClassificationLevel();
    } catch (_) {}

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF121A16),
        title: const Text(
          'LOGOUT',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        content: const Text(
          'Are you sure you want to logout? Cached data will be cleared.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('LOGOUT', style: TextStyle(color: Color(0xFFFF8F00))),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await context.read<ApiService>().logout();
      if (mounted) {
        context.read<AuthState>().setAuthenticated(false);
        Navigator.of(context).pushNamedAndRemoveUntil('/login', (_) => false);
      }
    }
  }

  Future<void> _handleRemoteWipe() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF121A16),
        title: const Text(
          'REMOTE WIPE',
          style: TextStyle(
            color: Color(0xFFB71C1C),
            fontWeight: FontWeight.bold,
          ),
        ),
        content: const Text(
          'This will permanently erase ALL data from this device including '
          'cached intelligence, credentials, and offline queues. '
          'This action is IRREVERSIBLE.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text(
              'WIPE DEVICE',
              style: TextStyle(color: Color(0xFFB71C1C)),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      setState(() => _isLoading = true);

      final apiService = context.read<ApiService>();
      await apiService.triggerRemoteWipe();

      if (mounted) {
        context.read<AuthState>().setAuthenticated(false);
        Navigator.of(context).pushNamedAndRemoveUntil('/login', (_) => false);
      }
    }
  }

  Future<void> _handleClearCache() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF121A16),
        title: const Text(
          'CLEAR CACHE',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        content: Text(
          'This will clear ${_formatBytes(_cacheSize)} of cached data. '
          'You will need to re-fetch data when going online.',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('CLEAR', style: TextStyle(color: Color(0xFFFF8F00))),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final offlineService = context.read<OfflineService>();
      await offlineService.clearExpiredCache();
      await _loadSettings();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cache cleared')),
        );
      }
    }
  }

  Future<void> _handleBiometricToggle(bool value) async {
    if (value) {
      try {
        final authenticated = await _localAuth.authenticate(
          localizedReason: 'Enable biometric authentication',
          options: const AuthenticationOptions(
            stickyAuth: true,
            biometricOnly: true,
          ),
        );

        if (mounted) {
          setState(() => _biometricEnabled = authenticated);
        }
      } catch (_) {
        if (mounted) {
          setState(() => _biometricEnabled = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Biometric enrollment failed')),
          );
        }
      }
    } else {
      setState(() => _biometricEnabled = false);
    }
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SETTINGS'),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF2E7D52)),
            )
          : ListView(
              children: [
                _buildClassificationBanner(),
                const SizedBox(height: 8),
                _buildSectionHeader('SECURITY'),
                _buildSecuritySection(),
                const SizedBox(height: 8),
                _buildSectionHeader('DATA MANAGEMENT'),
                _buildDataSection(),
                const SizedBox(height: 8),
                _buildSectionHeader('ACCOUNT'),
                _buildAccountSection(),
                const SizedBox(height: 32),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: ElevatedButton(
                    onPressed: _handleRemoteWipe,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFB71C1C),
                      side: const BorderSide(color: Color(0xFFB71C1C)),
                    ),
                    child: const Text(
                      'REMOTE WIPE DEVICE',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: OutlinedButton(
                    onPressed: _handleLogout,
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Color(0xFFFF8F00)),
                      minimumSize: const Size(double.infinity, 48),
                    ),
                    child: const Text(
                      'LOGOUT',
                      style: TextStyle(color: Color(0xFFFF8F00)),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
    );
  }

  Widget _buildClassificationBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      color: _getClassificationBannerColor().withOpacity(0.2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.shield,
            color: _getClassificationBannerColor(),
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            'CLASSIFICATION: ${_classificationLevel ?? 'UNCLASSIFIED'}',
            style: TextStyle(
              color: _getClassificationBannerColor(),
              fontWeight: FontWeight.bold,
              fontSize: 12,
              letterSpacing: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Color _getClassificationBannerColor() {
    switch (_classificationLevel?.toUpperCase()) {
      case 'TOP SECRET':
        return const Color(0xFFB71C1C);
      case 'SECRET':
        return const Color(0xFFE65100);
      case 'CONFIDENTIAL':
        return const Color(0xFFFF8F00);
      default:
        return const Color(0xFF2E7D52);
    }
  }

  Widget _buildSectionHeader(String title) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: const TextStyle(
          color: Color(0xFF2E7D52),
          fontSize: 12,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  Widget _buildSecuritySection() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          SwitchListTile(
            title: const Text(
              'Biometric Authentication',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: const Text(
              'Use fingerprint or face recognition',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
            value: _biometricEnabled,
            activeColor: const Color(0xFF2E7D52),
            onChanged: _handleBiometricToggle,
            secondary: const Icon(
              Icons.fingerprint,
              color: Color(0xFF2E7D52),
            ),
          ),
          const Divider(height: 1, color: Color(0xFF2E7D52)),
          SwitchListTile(
            title: const Text(
              'Auto-Sync',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: const Text(
              'Sync data when connection is available',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
            value: _autoSyncEnabled,
            activeColor: const Color(0xFF2E7D52),
            onChanged: (value) {
              setState(() => _autoSyncEnabled = value);
            },
            secondary: const Icon(
              Icons.sync,
              color: Color(0xFF2E7D52),
            ),
          ),
          const Divider(height: 1, color: Color(0xFF2E7D52)),
          ListTile(
            leading: const Icon(Icons.lock_outline, color: Color(0xFF2E7D52)),
            title: const Text(
              'Session Timeout',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: const Text(
              '15 minutes',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
            trailing: const Icon(
              Icons.chevron_right,
              color: Colors.white38,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDataSection() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.storage_outlined, color: Color(0xFF2E7D52)),
            title: const Text(
              'Cache Size',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: Text(
              _formatBytes(_cacheSize),
              style: const TextStyle(color: Colors.white38, fontSize: 12),
            ),
            trailing: TextButton(
              onPressed: _handleClearCache,
              child: const Text(
                'CLEAR',
                style: TextStyle(color: Color(0xFFFF8F00), fontSize: 12),
              ),
            ),
          ),
          const Divider(height: 1, color: Color(0xFF2E7D52)),
          ListTile(
            leading: const Icon(Icons.cloud_upload_outlined, color: Color(0xFF2E7D52)),
            title: const Text(
              'Pending Requests',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: Text(
              '$_queuedRequests queued offline',
              style: const TextStyle(color: Colors.white38, fontSize: 12),
            ),
            trailing: _queuedRequests > 0
                ? TextButton(
                    onPressed: () async {
                      final apiService = context.read<ApiService>();
                      await apiService.syncOfflineQueue();
                      await _loadSettings();
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Sync complete')),
                        );
                      }
                    },
                    child: const Text(
                      'SYNC',
                      style: TextStyle(color: Color(0xFF2E7D52), fontSize: 12),
                    ),
                  )
                : null,
          ),
          const Divider(height: 1, color: Color(0xFF2E7D52)),
          ListTile(
            leading: const Icon(Icons.history_outlined, color: Color(0xFF2E7D52)),
            title: const Text(
              'Sync History',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            trailing: const Icon(
              Icons.chevron_right,
              color: Colors.white38,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAccountSection() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.person_outline, color: Color(0xFF2E7D52)),
            title: const Text(
              'User Profile',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            trailing: const Icon(
              Icons.chevron_right,
              color: Colors.white38,
            ),
          ),
          const Divider(height: 1, color: Color(0xFF2E7D52)),
          ListTile(
            leading: const Icon(Icons.info_outline, color: Color(0xFF2E7D52)),
            title: const Text(
              'App Version',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            subtitle: const Text(
              '1.0.0 (Build 1)',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

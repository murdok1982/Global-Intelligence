import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'offline_service.dart';

class ApiService {
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.global-intelligence.gov/v1',
  );

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _tokenExpiryKey = 'token_expiry';

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final OfflineService _offlineService;
  final http.Client _httpClient;

  String? _accessToken;
  String? _refreshToken;
  DateTime? _tokenExpiry;
  bool _isRefreshing = false;
  final List<PendingRequest> _offlineQueue = [];

  ApiService({
    required OfflineService offlineService,
    http.Client? httpClient,
  })  : _offlineService = offlineService,
        _httpClient = httpClient ?? http.Client();

  Future<void> initialize() async {
    _accessToken = await _secureStorage.read(key: _accessTokenKey);
    _refreshToken = await _secureStorage.read(key: _refreshTokenKey);

    final expiryStr = await _secureStorage.read(key: _tokenExpiryKey);
    if (expiryStr != null) {
      _tokenExpiry = DateTime.tryParse(expiryStr);
    }

    await _loadOfflineQueue();
  }

  bool get hasValidToken =>
      _accessToken != null &&
      _tokenExpiry != null &&
      DateTime.now().isBefore(_tokenExpiry!);

  Future<bool> login(String email, String password) async {
    try {
      final response = await _httpClient.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _storeTokens(data);
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Login error: $e');
      return false;
    }
  }

  Future<bool> submitMfaCode(String code) async {
    try {
      final response = await _httpClient.post(
        Uri.parse('$_baseUrl/auth/mfa/verify'),
        headers: {
          'Content-Type': 'application/json',
          if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        },
        body: jsonEncode({'code': code}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _storeTokens(data);
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('MFA verification error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    try {
      if (_accessToken != null) {
        await _httpClient.post(
          Uri.parse('$_baseUrl/auth/logout'),
          headers: {'Authorization': 'Bearer $_accessToken'},
        );
      }
    } catch (_) {}

    _accessToken = null;
    _refreshToken = null;
    _tokenExpiry = null;
    _offlineQueue.clear();

    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _secureStorage.delete(key: _tokenExpiryKey);
    await _offlineService.clearAll();
  }

  Future<String?> getClassificationLevel() async {
    final response = await get('/auth/profile');
    if (response != null) {
      return response['classification_level'] as String?;
    }
    return null;
  }

  Future<Map<String, dynamic>?> get(String path) async {
    final request = PendingRequest(
      method: 'GET',
      path: path,
      timestamp: DateTime.now(),
    );

    if (!await _ensureAuthenticated()) {
      await _enqueueRequest(request);
      return null;
    }

    try {
      final response = await _httpClient.get(
        Uri.parse('$_baseUrl$path'),
        headers: await _buildHeaders(),
      );

      if (response.statusCode == 401) {
        final refreshed = await _refreshAccessToken();
        if (refreshed) {
          return get(path);
        }
        return null;
      }

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _offlineService.cacheResponse(path, data);
        return data;
      }

      return null;
    } catch (e) {
      debugPrint('GET error: $e');
      final cached = await _offlineService.getCachedResponse(path);
      return cached;
    }
  }

  Future<List<dynamic>?> getList(String path) async {
    if (!await _ensureAuthenticated()) {
      return null;
    }

    try {
      final response = await _httpClient.get(
        Uri.parse('$_baseUrl$path'),
        headers: await _buildHeaders(),
      );

      if (response.statusCode == 401) {
        final refreshed = await _refreshAccessToken();
        if (refreshed) {
          return getList(path);
        }
        return null;
      }

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List<dynamic>;
        await _offlineService.cacheResponse(path, {'data': data});
        return data;
      }

      return null;
    } catch (e) {
      debugPrint('GET list error: $e');
      final cached = await _offlineService.getCachedResponse(path);
      return cached?['data'] as List<dynamic>?;
    }
  }

  Future<Map<String, dynamic>?> post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final request = PendingRequest(
      method: 'POST',
      path: path,
      body: body,
      timestamp: DateTime.now(),
    );

    if (!await _ensureAuthenticated()) {
      await _enqueueRequest(request);
      return null;
    }

    try {
      final response = await _httpClient.post(
        Uri.parse('$_baseUrl$path'),
        headers: await _buildHeaders(),
        body: jsonEncode(body),
      );

      if (response.statusCode == 401) {
        final refreshed = await _refreshAccessToken();
        if (refreshed) {
          return post(path, body);
        }
        return null;
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }

      return null;
    } catch (e) {
      debugPrint('POST error: $e');
      await _enqueueRequest(request);
      return null;
    }
  }

  Future<void> triggerRemoteWipe() async {
    try {
      await _httpClient.post(
        Uri.parse('$_baseUrl/auth/remote-wipe'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      );
    } catch (_) {}

    await logout();
  }

  Future<void> syncOfflineQueue() async {
    if (_offlineQueue.isEmpty) return;

    final pending = List<PendingRequest>.from(_offlineQueue);
    _offlineQueue.clear();

    for (final request in pending) {
      try {
        if (request.method == 'POST') {
          await _httpClient.post(
            Uri.parse('$_baseUrl${request.path}'),
            headers: await _buildHeaders(),
            body: jsonEncode(request.body),
          );
        } else if (request.method == 'PUT') {
          await _httpClient.put(
            Uri.parse('$_baseUrl${request.path}'),
            headers: await _buildHeaders(),
            body: jsonEncode(request.body),
          );
        } else if (request.method == 'DELETE') {
          await _httpClient.delete(
            Uri.parse('$_baseUrl${request.path}'),
            headers: await _buildHeaders(),
          );
        }
      } catch (e) {
        debugPrint('Sync failed for ${request.method} ${request.path}: $e');
        _offlineQueue.add(request);
      }
    }

    await _saveOfflineQueue();
  }

  Future<void> remoteWipeDevice() async {
    await _secureStorage.deleteAll();
    await _offlineService.clearAll();
    _accessToken = null;
    _refreshToken = null;
    _tokenExpiry = null;
    _offlineQueue.clear();
  }

  Future<void> _storeTokens(Map<String, dynamic> data) async {
    _accessToken = data['access_token'] as String?;
    _refreshToken = data['refresh_token'] as String?;

    final expiresIn = data['expires_in'] as int? ?? 900;
    _tokenExpiry = DateTime.now().add(Duration(seconds: expiresIn));

    if (_accessToken != null) {
      await _secureStorage.write(
        key: _accessTokenKey,
        value: _accessToken!,
      );
    }
    if (_refreshToken != null) {
      await _secureStorage.write(
        key: _refreshTokenKey,
        value: _refreshToken!,
      );
    }
    if (_tokenExpiry != null) {
      await _secureStorage.write(
        key: _tokenExpiryKey,
        value: _tokenExpiry!.toIso8601String(),
      );
    }
  }

  Future<bool> _ensureAuthenticated() async {
    if (hasValidToken) return true;
    return _refreshAccessToken();
  }

  Future<bool> _refreshAccessToken() async {
    if (_isRefreshing) return false;
    if (_refreshToken == null) return false;

    _isRefreshing = true;

    try {
      final response = await _httpClient.post(
        Uri.parse('$_baseUrl/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': _refreshToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _storeTokens(data);
        return true;
      }

      await logout();
      return false;
    } catch (e) {
      debugPrint('Token refresh error: $e');
      return false;
    } finally {
      _isRefreshing = false;
    }
  }

  Future<Map<String, String>> _buildHeaders() async {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
    };
  }

  Future<void> _enqueueRequest(PendingRequest request) async {
    _offlineQueue.add(request);
    await _offlineService.queueRequest(request);
  }

  Future<void> _loadOfflineQueue() async {
    final queued = await _offlineService.getQueuedRequests();
    _offlineQueue.addAll(queued);
  }

  Future<void> _saveOfflineQueue() async {
    await _offlineService.clearQueuedRequests();
    for (final request in _offlineQueue) {
      await _offlineService.queueRequest(request);
    }
  }
}

class PendingRequest {
  final String method;
  final String path;
  final Map<String, dynamic>? body;
  final DateTime timestamp;

  const PendingRequest({
    required this.method,
    required this.path,
    this.body,
    required this.timestamp,
  });

  Map<String, dynamic> toJson() {
    return {
      'method': method,
      'path': path,
      'body': body != null ? jsonEncode(body) : null,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  factory PendingRequest.fromJson(Map<String, dynamic> json) {
    return PendingRequest(
      method: json['method'] as String,
      path: json['path'] as String,
      body: json['body'] != null
          ? jsonDecode(json['body'] as String) as Map<String, dynamic>
          : null,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }
}

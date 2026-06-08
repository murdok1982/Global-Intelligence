import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;

import 'api_service.dart';

class OfflineService {
  static const String _dbName = 'global_intelligence.db';
  static const int _dbVersion = 1;

  static const String _cacheTable = 'response_cache';
  static const String _queueTable = 'request_queue';
  static const String _syncLogTable = 'sync_log';

  Database? _database;

  Future<void> initialize() async {
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, _dbName);

    _database = await openDatabase(
      path,
      version: _dbVersion,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE $_cacheTable (
        id TEXT PRIMARY KEY,
        response_data TEXT NOT NULL,
        cached_at INTEGER NOT NULL,
        expires_at INTEGER
      )
    ''');

    await db.execute('''
      CREATE TABLE $_queueTable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        body TEXT,
        timestamp INTEGER NOT NULL,
        retry_count INTEGER DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE $_syncLogTable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        synced_at INTEGER NOT NULL,
        status TEXT NOT NULL,
        record_count INTEGER DEFAULT 0
      )
    ''');

    await db.execute(
      'CREATE INDEX idx_cache_expires ON $_cacheTable(expires_at)',
    );
    await db.execute(
      'CREATE INDEX idx_queue_timestamp ON $_queueTable(timestamp)',
    );
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {}
  }

  Future<void> cacheResponse(
    String endpoint,
    Map<String, dynamic> data, {
    Duration ttl = const Duration(hours: 24),
  }) async {
    final db = _database;
    if (db == null) return;

    final now = DateTime.now().millisecondsSinceEpoch;
    final expiresAt = now + ttl.inMilliseconds;

    await db.insert(
      _cacheTable,
      {
        'id': endpoint,
        'response_data': jsonEncode(data),
        'cached_at': now,
        'expires_at': expiresAt,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<Map<String, dynamic>?> getCachedResponse(String endpoint) async {
    final db = _database;
    if (db == null) return null;

    final results = await db.query(
      _cacheTable,
      where: 'id = ?',
      whereArgs: [endpoint],
      limit: 1,
    );

    if (results.isEmpty) return null;

    final row = results.first;
    final expiresAt = row['expires_at'] as int?;

    if (expiresAt != null &&
        DateTime.now().millisecondsSinceEpoch > expiresAt) {
      await db.delete(_cacheTable, where: 'id = ?', whereArgs: [endpoint]);
      return null;
    }

    final data = row['response_data'] as String;
    return jsonDecode(data) as Map<String, dynamic>;
  }

  Future<void> cacheCountryData(String countryId, Map<String, dynamic> data) async {
    await cacheResponse('country_$countryId', data);
  }

  Future<Map<String, dynamic>?> getCachedCountryData(String countryId) async {
    return getCachedResponse('country_$countryId');
  }

  Future<void> cacheReports(List<dynamic> reports) async {
    await cacheResponse('reports_list', {'data': reports});
  }

  Future<List<dynamic>?> getCachedReports() async {
    final cached = await getCachedResponse('reports_list');
    return cached?['data'] as List<dynamic>?;
  }

  Future<void> queueRequest(PendingRequest request) async {
    final db = _database;
    if (db == null) return;

    await db.insert(
      _queueTable,
      {
        'method': request.method,
        'path': request.path,
        'body': request.body != null ? jsonEncode(request.body) : null,
        'timestamp': request.timestamp.millisecondsSinceEpoch,
        'retry_count': 0,
      },
    );
  }

  Future<List<PendingRequest>> getQueuedRequests() async {
    final db = _database;
    if (db == null) return [];

    final results = await db.query(
      _queueTable,
      orderBy: 'timestamp ASC',
    );

    return results.map((row) {
      return PendingRequest(
        method: row['method'] as String,
        path: row['path'] as String,
        body: row['body'] != null
            ? jsonDecode(row['body'] as String) as Map<String, dynamic>
            : null,
        timestamp:
            DateTime.fromMillisecondsSinceEpoch(row['timestamp'] as int),
      );
    }).toList();
  }

  Future<void> clearQueuedRequests() async {
    final db = _database;
    if (db == null) return;
    await db.delete(_queueTable);
  }

  Future<void> removeQueuedRequest(int id) async {
    final db = _database;
    if (db == null) return;
    await db.delete(_queueTable, where: 'id = ?', whereArgs: [id]);
  }

  Future<void> logSync(
    String endpoint, {
    required String status,
    int recordCount = 0,
  }) async {
    final db = _database;
    if (db == null) return;

    await db.insert(_syncLogTable, {
      'endpoint': endpoint,
      'synced_at': DateTime.now().millisecondsSinceEpoch,
      'status': status,
      'record_count': recordCount,
    });
  }

  Future<List<Map<String, dynamic>>> getSyncHistory({int limit = 50}) async {
    final db = _database;
    if (db == null) return [];

    return db.query(
      _syncLogTable,
      orderBy: 'synced_at DESC',
      limit: limit,
    );
  }

  Future<void> resolveConflict({
    required String endpoint,
    required Map<String, dynamic> serverData,
  }) async {
    await cacheResponse(endpoint, serverData);
    await logSync(endpoint, status: 'CONFLICT_RESOLVED_SERVER_WINS');
  }

  Future<int> getCacheSize() async {
    final db = _database;
    if (db == null) return 0;

    final result = await db.rawQuery(
      'SELECT SUM(LENGTH(response_data)) as total_size FROM $_cacheTable',
    );

    if (result.isEmpty || result.first['total_size'] == null) return 0;
    return result.first['total_size'] as int;
  }

  Future<int> getQueuedRequestCount() async {
    final db = _database;
    if (db == null) return 0;

    final result = await db.rawQuery(
      'SELECT COUNT(*) as count FROM $_queueTable',
    );

    if (result.isEmpty) return 0;
    return result.first['count'] as int;
  }

  Future<void> clearExpiredCache() async {
    final db = _database;
    if (db == null) return;

    final now = DateTime.now().millisecondsSinceEpoch;
    await db.delete(
      _cacheTable,
      where: 'expires_at IS NOT NULL AND expires_at < ?',
      whereArgs: [now],
    );
  }

  Future<void> clearAll() async {
    final db = _database;
    if (db == null) return;

    await db.delete(_cacheTable);
    await db.delete(_queueTable);
    await db.delete(_syncLogTable);
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/api_service.dart';
import 'services/offline_service.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/country_detail_screen.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final offlineService = OfflineService();
  await offlineService.initialize();

  final apiService = ApiService(offlineService: offlineService);
  await apiService.initialize();

  runApp(
    GlobalIntelligenceApp(
      apiService: apiService,
      offlineService: offlineService,
    ),
  );
}

class GlobalIntelligenceApp extends StatelessWidget {
  final ApiService apiService;
  final OfflineService offlineService;

  const GlobalIntelligenceApp({
    super.key,
    required this.apiService,
    required this.offlineService,
  });

  static const Color _primaryGreen = Color(0xFF1B3A2D);
  static const Color _accentGreen = Color(0xFF2E7D52);
  static const Color _darkBackground = Color(0xFF0A0F0D);
  static const Color _surfaceDark = Color(0xFF121A16);
  static const Color _alertRed = Color(0xFFB71C1C);
  static const Color _warningAmber = Color(0xFFFF8F00);

  static final ThemeData _darkMilitaryTheme = ThemeData(
    brightness: Brightness.dark,
    primaryColor: _primaryGreen,
    scaffoldBackgroundColor: _darkBackground,
    colorScheme: const ColorScheme.dark(
      primary: _accentGreen,
      secondary: _accentGreen,
      surface: _surfaceDark,
      error: _alertRed,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: Colors.white70,
      onError: Colors.white,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: _primaryGreen,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
    cardTheme: CardThemeData(
      color: _surfaceDark,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: _accentGreen, width: 0.5),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: _accentGreen,
        foregroundColor: Colors.white,
        minimumSize: const Size(double.infinity, 48),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: _surfaceDark,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: _accentGreen),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: _accentGreen, width: 2),
      ),
      labelStyle: const TextStyle(color: Colors.white54),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: _surfaceDark,
      selectedItemColor: _accentGreen,
      unselectedItemColor: Colors.white38,
    ),
    dividerColor: _accentGreen.withOpacity(0.2),
  );

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiService>.value(value: apiService),
        Provider<OfflineService>.value(value: offlineService),
        ChangeNotifierProvider(create: (_) => AuthState(apiService)),
      ],
      child: MaterialApp(
        title: 'Global Intelligence',
        debugShowCheckedModeBanner: false,
        theme: _darkMilitaryTheme,
        initialRoute: '/login',
        routes: {
          '/login': (_) => const LoginScreen(),
          '/dashboard': (_) => const DashboardScreen(),
          '/countries': (_) => const DashboardScreen(initialTab: 1),
          '/reports': (_) => const DashboardScreen(initialTab: 2),
          '/settings': (_) => const SettingsScreen(),
        },
        onGenerateRoute: (settings) {
          if (settings.name == '/country') {
            final countryId = settings.arguments as String;
            return MaterialPageRoute(
              builder: (_) => CountryDetailScreen(countryId: countryId),
            );
          }
          return null;
        },
      ),
    );
  }
}

class AuthState extends ChangeNotifier {
  final ApiService _apiService;
  bool _isAuthenticated = false;
  String? _classificationLevel;

  AuthState(this._apiService);

  bool get isAuthenticated => _isAuthenticated;
  String? get classificationLevel => _classificationLevel;

  Future<bool> login(String email, String password) async {
    final success = await _apiService.login(email, password);
    if (success) {
      _isAuthenticated = true;
      _classificationLevel = await _apiService.getClassificationLevel();
      notifyListeners();
    }
    return success;
  }

  Future<void> logout() async {
    await _apiService.logout();
    _isAuthenticated = false;
    _classificationLevel = null;
    notifyListeners();
  }

  void setAuthenticated(bool value, {String? classification}) {
    _isAuthenticated = value;
    _classificationLevel = classification;
    notifyListeners();
  }
}

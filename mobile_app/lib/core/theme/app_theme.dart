import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  AppTheme._();

  // ANEP color palette
  static const Color primary = Color(0xFF1565C0);   // ANEP blue
  static const Color secondary = Color(0xFF2E7D32); // EBI green
  static const Color surface = Color(0xFFF5F7FA);
  static const Color onPrimary = Colors.white;

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        secondary: secondary,
        surface: surface,
      ),
      textTheme: GoogleFonts.interTextTheme(),
      appBarTheme: AppBarTheme(
        backgroundColor: primary,
        foregroundColor: onPrimary,
        elevation: 0,
        titleTextStyle: GoogleFonts.inter(
          color: onPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        indicatorColor: primary.withAlpha(30),
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => GoogleFonts.inter(fontSize: 12),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      ),
    );
  }
}

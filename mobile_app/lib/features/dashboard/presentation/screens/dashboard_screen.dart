import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../chat/presentation/screens/chat_screen.dart';
import '../../../curriculum/presentation/screens/curriculum_explorer_screen.dart';
import '../../../planificaciones/presentation/screens/planificaciones_list_screen.dart';
import '../../../alumnos/presentation/screens/alumnos_list_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  int _selectedIndex = 0;

  static const _destinations = [
    NavigationDestination(
      icon: Icon(Icons.chat_bubble_outline),
      selectedIcon: Icon(Icons.chat_bubble),
      label: 'Agente',
    ),
    NavigationDestination(
      icon: Icon(Icons.school_outlined),
      selectedIcon: Icon(Icons.school),
      label: 'Programa',
    ),
    NavigationDestination(
      icon: Icon(Icons.description_outlined),
      selectedIcon: Icon(Icons.description),
      label: 'Planificaciones',
    ),
    NavigationDestination(
      icon: Icon(Icons.group_outlined),
      selectedIcon: Icon(Icons.group),
      label: 'Alumnos',
    ),
  ];

  static const _screens = [
    ChatScreen(),
    CurriculumExplorerScreen(),
    PlanificacionesListScreen(),
    AlumnosListScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (i) => setState(() => _selectedIndex = i),
        destinations: _destinations,
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_fonts/google_fonts.dart';

import 'screens/login/login_screen.dart';
import 'screens/tasks/tasks_screen.dart';
import 'screens/task_detail/task_detail_screen.dart';
import 'screens/active_task/active_task_screen.dart';
import 'screens/impact/impact_screen.dart';
import 'screens/badges/badges_screen.dart';

void main() async {
  // Ensure Flutter binding is initialized
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase Core
  await Firebase.initializeApp();

  runApp(const SynapseApp());
}

class SynapseApp extends StatelessWidget {
  const SynapseApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Definining our Navy theme color
    const Color navyColor = Color(0xFF0D2B4E);

    return MaterialApp(
      title: 'SYNAPSE Volunteer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        // Apply DM Sans font across the app
        textTheme: GoogleFonts.dmSansTextTheme(
          Theme.of(context).textTheme,
        ),
        colorScheme: ColorScheme.fromSeed(
          seedColor: navyColor,
          primary: navyColor,
        ),
        scaffoldBackgroundColor: Colors.white,
        appBarTheme: const AppBarTheme(
          backgroundColor: navyColor,
          foregroundColor: Colors.white,
          centerTitle: true,
          elevation: 0,
        ),
        useMaterial3: true,
      ),
      // Check auth to determine initial screen
      home: const AuthChecker(),
      // Named routes for all screens
      routes: {
        '/login': (context) => const LoginScreen(),
        '/tasks': (context) => const TasksScreen(),
        '/task_detail': (context) => const TaskDetailScreen(),
        '/active_task': (context) => const ActiveTaskScreen(),
        '/impact': (context) => const ImpactScreen(),
        '/badges': (context) => const BadgesScreen(),
      },
    );
  }
}

class AuthChecker extends StatelessWidget {
  const AuthChecker({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        // While checking auth status
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(
              child: CircularProgressIndicator(
                color: Color(0xFF0D2B4E),
              ),
            ),
          );
        }
        
        // Logged in -> show TasksScreen
        if (snapshot.hasData && snapshot.data != null) {
          return const TasksScreen();
        }
        
        // Not logged in -> show LoginScreen
        return const LoginScreen();
      },
    );
  }
}

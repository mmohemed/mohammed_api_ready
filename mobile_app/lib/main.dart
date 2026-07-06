// =========================================
// Smart Factory ERP — تطبيق المشرفين (Flutter)
// تسجيل دخول + مؤشرات المصنع + الرؤى الذكية + خطر الآلات
// عدّل serverUrl ليشير إلى خادم النظام على شبكة المصنع
// =========================================
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// ⚠️ غيّر هذا إلى عنوان الخادم عندك (مثال: http://192.168.1.50:8000)
const String serverUrl = 'http://192.168.1.50:8000';

void main() => runApp(const SupervisorApp());

class SupervisorApp extends StatelessWidget {
  const SupervisorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Factory ERP',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2A78D6)),
        fontFamily: 'Segoe UI',
        useMaterial3: true,
      ),
      locale: const Locale('ar'),
      builder: (context, child) =>
          Directionality(textDirection: TextDirection.rtl, child: child!),
      home: const LoginScreen(),
    );
  }
}

// ---------- عميل الـ API ----------
class Api {
  static String? token;

  static Future<Map<String, dynamic>> post(String path, Map body) async {
    final response = await http.post(
      Uri.parse('$serverUrl$path'),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
      body: jsonEncode(body),
    );
    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 400) {
      throw Exception(data['detail'] ?? 'خطأ غير متوقع');
    }
    return data;
  }

  static Future<dynamic> get(String path) async {
    final response = await http.get(
      Uri.parse('$serverUrl$path'),
      headers: {if (token != null) 'Authorization': 'Bearer $token'},
    );
    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 400) {
      throw Exception(data['detail'] ?? 'خطأ غير متوقع');
    }
    return data;
  }
}

// ---------- شاشة الدخول ----------
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  String? _error;
  bool _loading = false;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await Api.post('/auth/login', {
        'username': _username.text.trim(),
        'password': _password.text,
      });
      Api.token = data['access_token'];
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', data['username']);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const DashboardScreen()),
      );
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('🏭', style: TextStyle(fontSize: 56)),
              const SizedBox(height: 8),
              Text('Smart Factory ERP',
                  style: Theme.of(context).textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800)),
              const Text('تطبيق المشرفين'),
              const SizedBox(height: 28),
              TextField(
                controller: _username,
                decoration: const InputDecoration(
                    labelText: 'اسم المستخدم', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(
                    labelText: 'كلمة المرور', border: OutlineInputBorder()),
                onSubmitted: (_) => _login(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _loading ? null : _login,
                  child: Text(_loading ? '...' : 'تسجيل الدخول'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------- لوحة المشرف ----------
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? kpis;
  Map<String, dynamic>? insights;
  List<dynamic> machines = [];

  Future<void> _load() async {
    final results = await Future.wait([
      Api.get('/dashboard'),
      Api.get('/ai/insights'),
      Api.get('/machines/risk-overview'),
    ]);
    setState(() {
      kpis = results[0];
      insights = results[1];
      machines = results[2]['machines'];
    });
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Widget _tile(String label, String value, {Color? color}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            const SizedBox(height: 6),
            Text(value,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: color)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🏭 لوحة المشرف')),
      body: kpis == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(14),
                children: [
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    childAspectRatio: 1.9,
                    children: [
                      _tile('قيمة المخزون', '${kpis!['inventory']['inventory_value']}'),
                      _tile('إيرادات المبيعات', '${kpis!['sales']['total_revenue']}'),
                      _tile('جاهزية الآلات',
                          '${((kpis!['machines']['availability_rate'] ?? 0) * 100).round()}٪'),
                      _tile('نسبة العيوب',
                          '${((kpis!['production']['defect_rate'] ?? 0) * 100).toStringAsFixed(1)}٪'),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('⚠️ خطر عطل الآلات',
                      style: Theme.of(context).textTheme.titleMedium),
                  ...machines.map((m) {
                    final p = m['failure_probability'];
                    final percent = p == null ? null : (p * 100).round();
                    return ListTile(
                      title: Text(m['name']),
                      subtitle: Text(m['risk_level'] ?? ''),
                      trailing: Text(percent == null ? '—' : '$percent٪',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                            color: percent == null
                                ? Colors.grey
                                : percent >= 70
                                    ? Colors.red
                                    : percent >= 40
                                        ? Colors.orange
                                        : Colors.green,
                          )),
                    );
                  }),
                  const SizedBox(height: 10),
                  Text('🤖 الرؤى والتوصيات',
                      style: Theme.of(context).textTheme.titleMedium),
                  if (insights != null)
                    ...List<Widget>.from((insights!['insights'] as List).map(
                      (i) => Card(
                        child: ListTile(
                          title: Text('${i['priority_label']} ${i['title']}'),
                          subtitle: Text(i['recommendation'] ?? ''),
                        ),
                      ),
                    )),
                ],
              ),
            ),
    );
  }
}

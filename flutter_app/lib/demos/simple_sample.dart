import 'package:flutter/material.dart';

abstract final class AppColors {
  static const Color c111111 = Color(0xFF111111);
  static const Color ce5e5ea = Color(0xFFE5E5EA);
  static const Color cf5f5f7 = Color(0xFFF5F5F7);
  static const Color cffffff = Color(0xFFFFFFFF);
}

abstract final class AppSpacing {
  static const double s16 = 16;
  static const double s24 = 24;
  static const double s8 = 8;
}

abstract final class AppTextStyles {
  static const TextStyle s16w600 = TextStyle(fontSize: 16, fontWeight: FontWeight.w600);
  static const TextStyle s24w700 = TextStyle(fontSize: 24, fontWeight: FontWeight.w700);
}

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cffffff,
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: AppSpacing.s16, vertical: AppSpacing.s24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisAlignment: MainAxisAlignment.start,
            spacing: AppSpacing.s16,
            children: [
              Text(
                'Welcome back',
                style: AppTextStyles.s24w700.copyWith(color: AppColors.c111111),
                textAlign: TextAlign.left,
              ),
              ClipRRect(
                borderRadius: BorderRadius.circular(40),
                child: Image.network(
                  'assets/avatar.png',
                  width: 80,
                  height: 80,
                  fit: BoxFit.cover,
                ),
              ),
              const InfoCard(),
            ],
          ),
        ),
      ),
    );
  }
}

class InfoCard extends StatelessWidget {
  const InfoCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cf5f5f7,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: EdgeInsets.all(AppSpacing.s16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.start,
          spacing: AppSpacing.s8,
          children: [
            Text(
              'Account',
              style: AppTextStyles.s16w600.copyWith(color: AppColors.c111111),
            ),
            Container(
              width: 100,
              height: 1,
              color: AppColors.ce5e5ea,
            ),
          ],
        ),
      ),
    );
  }
}

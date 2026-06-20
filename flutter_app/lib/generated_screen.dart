import 'package:flutter/material.dart';

abstract final class AppColors {
  static const Color black = Color(0xFF000000);
  static const Color cbdc5cd = Color(0xFFBDC5CD);
  static const Color cfafafa = Color(0xFFFAFAFA);
  static const Color gray01 = Color(0xFFF6F6F6);
  static const Color gray02 = Color(0xFFE8E8E8);
  static const Color gray03 = Color(0xFFBDBDBD);
  static const Color greenPrimary = Color(0xFF5DB075);
  static const Color white = Color(0xFFFFFFFF);
}

abstract final class AppTextStyles {
  static const TextStyle inters14w400 = TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w400);
  static const TextStyle inters16w500 = TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w500);
  static const TextStyle inters16w600 = TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w600);
  static const TextStyle inters30w600 = TextStyle(fontFamily: 'Inter', fontSize: 30, fontWeight: FontWeight.w600);
}

class ProfilePosts extends StatelessWidget {
  const ProfilePosts({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.white,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned(
              left: -1,
              top: 0,
              child: Container(
                width: 376,
                height: 245,
                color: AppColors.greenPrimary,
              ),
            ),
            Positioned(
              left: 108,
              top: 128,
              child: Container(
                width: 158,
                height: 158,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppColors.white,
                    width: 4,
                  ),
                ),
              ),
            ),
            Positioned(
              left: 0,
              top: 0,
              child: const IOSStatusBarWhite(),
            ),
            Positioned(
              left: 16,
              top: 60,
              child: const PageHeader(),
            ),
            Positioned(
              left: 52,
              top: 302,
              child: const NameBio(),
            ),
            Positioned(
              left: 16,
              top: 389,
              child: const SegmentedControlLeft(),
            ),
            Positioned(
              left: 16,
              top: 455,
              child: const ContentContentBlockSmall(),
            ),
            Positioned(
              left: 16,
              top: 548,
              child: const ContentContentBlockSmall(),
            ),
            Positioned(
              left: 16,
              top: 641,
              child: const ContentContentBlockSmall(),
            ),
            Positioned(
              left: 16,
              top: 734,
              child: const ContentContentBlockSmall(),
            ),
            Positioned(
              left: 0,
              top: 729,
              child: const IOSBottomBar5Tabs(),
            ),
          ],
        ),
      ),
    );
  }
}

class BG extends StatelessWidget {
  const BG({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 375,
      height: 46,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 2,
            child: Container(
              width: 375,
              height: 44,
              color: AppColors.black,
            ),
          ),
          Positioned(
            left: 78,
            top: 0,
            child: SizedBox(
              width: 219,
              height: 30,
            ),
          ),
        ],
      ),
    );
  }
}

class Battery extends StatelessWidget {
  const Battery({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 24.32803726196289,
      height: 11.333333015441895,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: SizedBox(
              width: 22,
              height: 11.333333015441895,
            ),
          ),
          Positioned(
            left: 23,
            top: 3.6666717529296875,
            child: SizedBox(
              width: 1.328037977218628,
              height: 4,
            ),
          ),
          Positioned(
            left: 2,
            top: 2,
            child: Container(
              width: 18,
              height: 7.333333492279053,
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(1.3333333730697632),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class RightSide extends StatelessWidget {
  const RightSide({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 66.661376953125,
      height: 11.336018562316895,
      child: Stack(
        children: [
          Positioned(
            left: 42.333251953125,
            top: 0.002685546875,
            child: const Battery(),
          ),
        ],
      ),
    );
  }
}

class LeftSide extends StatelessWidget {
  const LeftSide({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 28.42616844177246,
      height: 11.0888671875,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: SizedBox(
              width: 28.42616844177246,
              height: 11.0888671875,
            ),
          ),
        ],
      ),
    );
  }
}

class IOSStatusBarBlack extends StatelessWidget {
  const IOSStatusBarBlack({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 375,
      height: 44,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: -2,
            child: const BG(),
          ),
          Positioned(
            left: 293.666748046875,
            top: 17.3306884765625,
            child: const RightSide(),
          ),
          Positioned(
            left: 33.45361328125,
            top: 17.16748046875,
            child: const LeftSide(),
          ),
        ],
      ),
    );
  }
}

class IOSStatusBarWhite extends StatelessWidget {
  const IOSStatusBarWhite({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 375,
      height: 44,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: const IOSStatusBarBlack(),
          ),
        ],
      ),
    );
  }
}

class IconX extends StatelessWidget {
  const IconX({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 22.627416610717773,
      height: 22.627416610717773,
      child: Stack(
        children: <Widget>[],
      ),
    );
  }
}

class PageHeader extends StatelessWidget {
  const PageHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 343,
      height: 36,
      child: Stack(
        children: [
          Positioned(
            left: 289,
            top: 8,
            child: Text(
              'Logout',
              style: AppTextStyles.inters16w500.copyWith(color: AppColors.white, height: 1.21),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 126,
            top: 0,
            child: Text(
              'Profile',
              style: AppTextStyles.inters30w600.copyWith(color: AppColors.white, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: -0.313720703125,
            top: 4.686291694641113,
            child: const IconX(),
          ),
          Positioned(
            left: 0,
            top: 8,
            child: Text(
              'Settings',
              style: AppTextStyles.inters16w500.copyWith(color: AppColors.white, height: 1.21),
              textAlign: TextAlign.left,
            ),
          ),
        ],
      ),
    );
  }
}

class NameBio extends StatelessWidget {
  const NameBio({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 272,
      height: 63,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Text(
              'Victoria Robertson',
              style: AppTextStyles.inters30w600.copyWith(color: AppColors.black, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: 61,
            top: 44,
            child: Text(
              'A mantra goes here',
              style: AppTextStyles.inters16w600.copyWith(color: AppColors.black, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class LeftSelected extends StatelessWidget {
  const LeftSelected({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 171.5,
      height: 46,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
      ),
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 171.5,
              height: 46,
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 64,
            top: 14,
            child: Text(
              'Posts',
              style: AppTextStyles.inters16w600.copyWith(color: AppColors.greenPrimary, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class RightSelected extends StatelessWidget {
  const RightSelected({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 171.5,
      height: 46,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
      ),
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 171.5,
              height: 46,
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 59,
            top: 14,
            child: Text(
              'Search',
              style: AppTextStyles.inters16w600.copyWith(color: AppColors.greenPrimary, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class SegmentedControlStructure extends StatelessWidget {
  const SegmentedControlStructure({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 343,
      height: 50,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 343,
              height: 50,
              decoration: BoxDecoration(
                color: AppColors.gray01,
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: AppColors.gray02,
                  width: 1,
                ),
              ),
            ),
          ),
          Positioned(
            left: 228,
            top: 16,
            child: Text(
              'Photos',
              style: AppTextStyles.inters16w500.copyWith(color: AppColors.gray03, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: 61,
            top: 16,
            child: Text(
              'Search',
              style: AppTextStyles.inters16w500.copyWith(color: AppColors.gray03, height: 1.21),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: 2,
            top: 2,
            child: const LeftSelected(),
          ),
          Positioned(
            left: 169,
            top: 2,
            child: const RightSelected(),
          ),
        ],
      ),
    );
  }
}

class SegmentedControlLeft extends StatelessWidget {
  const SegmentedControlLeft({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 343,
      height: 50,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: const SegmentedControlStructure(),
          ),
        ],
      ),
    );
  }
}

class ContentContentBlockSmall extends StatelessWidget {
  const ContentContentBlockSmall({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 343,
      height: 77.0000228881836,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: AppColors.gray01,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 0,
            child: Text(
              'Header',
              style: AppTextStyles.inters16w600.copyWith(color: AppColors.black, height: 1.21),
              textAlign: TextAlign.left,
            ),
          ),
          Positioned(
            left: 293,
            top: 2,
            child: Text(
              '8m ago',
              style: AppTextStyles.inters14w400.copyWith(color: AppColors.gray03, height: 1.21),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 66,
            top: 27,
            child: SizedBox(
              width: 269,
              child: Text(
                'He\'ll want to use your yacht, and I don\'t want this thing smelling like fish.',
                style: AppTextStyles.inters14w400.copyWith(color: AppColors.black, height: 1.21),
                textAlign: TextAlign.left,
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 76.99997578388889,
            child: Container(
              width: 277,
              height: 1,
              color: AppColors.gray02,
            ),
          ),
        ],
      ),
    );
  }
}

class HomeIndicator extends StatelessWidget {
  const HomeIndicator({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 134,
      height: 5,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
      ),
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 134,
              height: 5,
              decoration: BoxDecoration(
                color: AppColors.black,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class IPhoneUI extends StatelessWidget {
  const IPhoneUI({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 375,
      height: 83,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 375,
              height: 83,
              color: AppColors.cfafafa,
            ),
          ),
          Positioned(
            left: 120,
            top: 69,
            child: const HomeIndicator(),
          ),
        ],
      ),
    );
  }
}

class Tabs extends StatelessWidget {
  const Tabs({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 320,
      height: 32,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
      ),
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.greenPrimary,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 72,
            top: 0,
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.gray02,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 144,
            top: 0,
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.gray02,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 216,
            top: 0,
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.gray02,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
          Positioned(
            left: 288,
            top: 0,
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.gray02,
                borderRadius: BorderRadius.circular(100),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class IOSBottomBar5Tabs extends StatelessWidget {
  const IOSBottomBar5Tabs({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 375,
      height: 83.5,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0.5,
            child: const IPhoneUI(),
          ),
          Positioned(
            left: 26,
            top: 15,
            child: const Tabs(),
          ),
          Positioned(
            left: 0,
            top: 0,
            child: Container(
              width: 375,
              height: 0.5,
              color: AppColors.cbdc5cd,
            ),
          ),
        ],
      ),
    );
  }
}

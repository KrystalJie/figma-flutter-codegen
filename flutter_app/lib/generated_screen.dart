import 'package:flutter/material.dart';

class ProfilePosts extends StatelessWidget {
  const ProfilePosts({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFFFFFFF),
      body: SafeArea(
        child: Stack(
          children: [
            Positioned(
              left: -1,
              top: 0,
              child: Container(
                width: 376,
                height: 245,
                color: Color(0xFF5DB075),
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
                  image: DecorationImage(
                    image: AssetImage('assets/images/80ba23780f992d6275fd95498e163d7b4c6dd13a.png'),
                    fit: BoxFit.cover,
                  ),
                  border: Border.all(
                    color: Color(0xFFFFFFFF),
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
              child: const ContentContentBlockSmall2(),
            ),
            Positioned(
              left: 16,
              top: 641,
              child: const ContentContentBlockSmall3(),
            ),
            Positioned(
              left: 16,
              top: 734,
              child: const ContentContentBlockSmall4(),
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
              color: Color(0xFF000000),
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
        children: <Widget>[],
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
        children: <Widget>[],
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
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFFFFFFFF),
              ),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 126,
            top: 0,
            child: Text(
              'Profile',
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w600,
                color: Color(0xFFFFFFFF),
              ),
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
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFFFFFFFF),
              ),
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
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: 61,
            top: 44,
            child: Text(
              'A mantra goes here',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
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
            left: 64,
            top: 14,
            child: Text(
              'Posts',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF5DB075),
              ),
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
            left: 59,
            top: 14,
            child: Text(
              'Search',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF5DB075),
              ),
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
            left: 228,
            top: 16,
            child: Text(
              'Photos',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFFBDBDBD),
              ),
              textAlign: TextAlign.center,
            ),
          ),
          Positioned(
            left: 61,
            top: 16,
            child: Text(
              'Search',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFFBDBDBD),
              ),
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
                color: Color(0xFFF6F6F6),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 0,
            child: Text(
              'Header',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
          Positioned(
            left: 293,
            top: 2,
            child: Text(
              '8m ago',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFFBDBDBD),
              ),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 66,
            top: 27,
            child: Text(
              'He\'ll want to use your yacht, and I don\'t want this thing smelling like fish.',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
        ],
      ),
    );
  }
}

class ContentContentBlockSmall2 extends StatelessWidget {
  const ContentContentBlockSmall2({super.key});

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
                color: Color(0xFFF6F6F6),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 0,
            child: Text(
              'Header',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
          Positioned(
            left: 293,
            top: 2,
            child: Text(
              '8m ago',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFFBDBDBD),
              ),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 66,
            top: 27,
            child: Text(
              'He\'ll want to use your yacht, and I don\'t want this thing smelling like fish.',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
        ],
      ),
    );
  }
}

class ContentContentBlockSmall3 extends StatelessWidget {
  const ContentContentBlockSmall3({super.key});

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
                color: Color(0xFFF6F6F6),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 0,
            child: Text(
              'Header',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
          Positioned(
            left: 293,
            top: 2,
            child: Text(
              '8m ago',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFFBDBDBD),
              ),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 66,
            top: 27,
            child: Text(
              'He\'ll want to use your yacht, and I don\'t want this thing smelling like fish.',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
        ],
      ),
    );
  }
}

class ContentContentBlockSmall4 extends StatelessWidget {
  const ContentContentBlockSmall4({super.key});

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
                color: Color(0xFFF6F6F6),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            left: 66,
            top: 0,
            child: Text(
              'Header',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
            ),
          ),
          Positioned(
            left: 293,
            top: 2,
            child: Text(
              '8m ago',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFFBDBDBD),
              ),
              textAlign: TextAlign.right,
            ),
          ),
          Positioned(
            left: 66,
            top: 27,
            child: Text(
              'He\'ll want to use your yacht, and I don\'t want this thing smelling like fish.',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFF000000),
              ),
              textAlign: TextAlign.left,
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
                color: Color(0xFF000000),
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
              color: Color(0xFFFAFAFA),
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
                color: Color(0xFF5DB075),
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
                color: Color(0xFFE8E8E8),
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
                color: Color(0xFFE8E8E8),
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
                color: Color(0xFFE8E8E8),
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
                color: Color(0xFFE8E8E8),
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
              color: Color(0xFFBDC5CD),
            ),
          ),
        ],
      ),
    );
  }
}

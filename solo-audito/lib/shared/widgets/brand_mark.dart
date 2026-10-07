import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class BrandMark extends StatelessWidget {
  final double size;
  const BrandMark({super.key, this.size = 56});
  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        colors: [AppColors.violet, Color(0xFFAD96FF)],
      ),
      borderRadius: BorderRadius.circular(size * .3),
    ),
    child: Icon(
      Icons.auto_awesome_rounded,
      color: Colors.white,
      size: size * .5,
    ),
  );
}

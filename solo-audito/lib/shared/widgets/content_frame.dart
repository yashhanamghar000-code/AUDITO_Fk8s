import 'package:flutter/material.dart';

class ContentFrame extends StatelessWidget {
  final Widget child;
  const ContentFrame({super.key, required this.child});
  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.topCenter,
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 720),
      child: child,
    ),
  );
}

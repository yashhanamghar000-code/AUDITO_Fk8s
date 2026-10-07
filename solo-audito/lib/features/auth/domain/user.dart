class AuditoUser {
  final int id;
  final String name;
  final String email;
  const AuditoUser({required this.id, required this.name, required this.email});
  factory AuditoUser.fromJson(Map<String, dynamic> json) => AuditoUser(
    id: json['id'] as int,
    name: json['name'] as String,
    email: json['email'] as String,
  );
}

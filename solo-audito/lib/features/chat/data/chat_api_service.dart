import 'package:dio/dio.dart';

import '../../../core/config/api_config.dart';

class ChatApiService {
  final Dio dio;
  ChatApiService(this.dio);
  Future<Map<String, dynamic>> conversations() async =>
      Map<String, dynamic>.from(
        (await dio.get(ApiConfig.conversations)).data as Map,
      );
  Future<Map<String, dynamic>> history(int user, String session) async =>
      Map<String, dynamic>.from(
        (await dio.get(ApiConfig.history(user, session))).data as Map,
      );
  Future<Map<String, dynamic>> send(String query, String session) async =>
      Map<String, dynamic>.from(
        (await dio.post(
              ApiConfig.chat,
              data: FormData.fromMap({'query': query, 'session_id': session}),
            )).data
            as Map,
      );
}

import 'dart:convert';

import 'package:dio/dio.dart';

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);
  factory ApiException.from(Object error) {
    if (error is ApiException) return error;
    if (error is FormatException) return ApiException(error.message);
    if (error is DioException) {
      final response = error.response;
      if (response != null) {
        dynamic body = response.data;
        if (body is String) {
          try {
            body = jsonDecode(body);
          } on FormatException {
            /* Non-JSON proxy response. */
          }
        }
        final detail = body is Map ? body['detail'] : null;
        if (detail is String && detail.trim().isNotEmpty) {
          return ApiException(detail);
        }
        if (detail is List) {
          final messages = detail
              .whereType<Map>()
              .map((e) => e['msg'])
              .whereType<String>()
              .toList();
          if (messages.isNotEmpty) return ApiException(messages.join('\n'));
        }
        return ApiException(switch (response.statusCode) {
          401 => 'Your session expired. Please sign in again.',
          403 => 'You do not have permission to access this resource.',
          404 => 'The requested document or conversation was not found.',
          413 =>
            'This file is too large for the server. Choose a smaller document.',
          415 => 'This document type is not supported.',
          422 => 'Please check your details and try again.',
          429 => 'Too many requests. Please wait a moment.',
          _ =>
            'Audito could not complete this request (HTTP ${response.statusCode ?? 'error'}). Please try again.',
        });
      }
      if (error.type == DioExceptionType.cancel) {
        return const ApiException('Request cancelled.');
      }
      return const ApiException(
        'Could not reach Audito. Check your connection and try again.',
      );
    }
    return const ApiException('Something went wrong. Please try again.');
  }
  @override
  String toString() => message;
}

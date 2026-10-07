import 'package:file_picker/file_picker.dart';

import '../../../core/network/api_exception.dart';
import '../domain/document_models.dart';

abstract interface class DocumentPicker {
  Future<SelectedDocument?> pick();
}

class NativeDocumentPicker implements DocumentPicker {
  @override
  Future<SelectedDocument?> pick() async {
    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: SelectedDocument.extensions,
    );
    if (file == null) return null;
    final size = await file.length();
    if (size > SelectedDocument.maxBytes) {
      throw const ApiException('Choose a document smaller than 200 MB.');
    }
    return SelectedDocument(
      name: file.name,
      size: size,
      path: file.path,
      readStream: file.readAsByteStream,
    );
  }
}

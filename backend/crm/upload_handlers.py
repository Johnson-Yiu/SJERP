"""Streaming protections for CSV import uploads."""

from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadhandler import FileUploadHandler, StopFutureHandlers, StopUpload


_CSV_IMPORT_PATHS = frozenset({
    "/api/import/csv",
    "/api/import/csv/preview",
    "/api/import/csv/execute",
})


class CsvImportSizeLimitUploadHandler(FileUploadHandler):
    """Reject oversized CSV endpoint file streams before downstream storage."""

    chunk_size = 64 * 1024

    def __init__(self, request=None):
        super().__init__(request)
        path_info = getattr(request, "path_info", "")
        self.enabled = path_info.rstrip("/") in _CSV_IMPORT_PATHS
        self.limit = settings.CSV_IMPORT_MAX_BYTES
        self.bytes_seen = 0
        self.bytes_forwarded = 0
        self._current_file_buffer = None

    def new_file(self, field_name, file_name, content_type, content_length, charset=None, content_type_extra=None):
        super().new_file(field_name, file_name, content_type, content_length, charset, content_type_extra)
        if self.enabled:
            self._current_file_buffer = BytesIO()
            raise StopFutureHandlers

    def receive_data_chunk(self, raw_data, start):
        if not self.enabled:
            return raw_data

        self.bytes_seen += len(raw_data)
        if self.bytes_seen > self.limit:
            self.request._csv_import_upload_limit_exceeded = {
                "limit": self.limit,
                "bytes_seen": self.bytes_seen,
                "bytes_forwarded": self.bytes_forwarded,
            }
            if self._current_file_buffer is not None:
                self._current_file_buffer.close()
                self._current_file_buffer = None
            # Discard the bounded prefix and stop parsing; do not forward any
            # part of an oversized CSV to Django's memory or temporary-file handlers.
            raise StopUpload(connection_reset=True)

        if self._current_file_buffer is None:
            self._current_file_buffer = BytesIO()
        self._current_file_buffer.write(raw_data)
        # A None chunk tells Django not to pass this data to later upload
        # handlers. On file_complete, only a complete, under-limit file is
        # exposed as an UploadedFile.
        return None

    def file_complete(self, file_size):
        if not self.enabled or self._current_file_buffer is None:
            return None

        file_buffer = self._current_file_buffer
        self._current_file_buffer = None
        file_buffer.seek(0)
        return InMemoryUploadedFile(
            file=file_buffer,
            field_name=self.field_name,
            name=self.file_name,
            content_type=self.content_type,
            size=file_size,
            charset=self.charset,
            content_type_extra=self.content_type_extra,
        )

    def upload_complete(self):
        if self._current_file_buffer is not None:
            self._current_file_buffer.close()
            self._current_file_buffer = None
        return None

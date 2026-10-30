"""Streaming protections for CSV import uploads."""

from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload


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
            # Stop the multipart parser immediately. Because this handler is
            # first, the over-limit chunk never reaches memory/disk handlers.
            raise StopUpload(connection_reset=True)

        self.bytes_forwarded += len(raw_data)
        return raw_data

    def file_complete(self, file_size):
        return None

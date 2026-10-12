from rest_framework.filters import SearchFilter


class PermissionAwareSearchFilter(SearchFilter):
    """Allow viewsets to remove related search fields the user cannot view."""

    def get_search_fields(self, view, request):
        resolver = getattr(view, "get_search_fields", None)
        if callable(resolver):
            return resolver(request)
        return super().get_search_fields(view, request)

from rest_framework.pagination import PageNumberPagination

# ──────────────────────────── pagination -------------------------------------
class CustomPage(PageNumberPagination):
    page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"
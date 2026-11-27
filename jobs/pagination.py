from rest_framework.pagination import PageNumberPagination

class JobPagination(PageNumberPagination):
    page_size = 5

    # Allows the client to pass ?page_size=10 (or any number) in the URL
    page_size_query_param = 'page_size'

    max_page_size = 20

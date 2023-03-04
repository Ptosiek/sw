class HTMXMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_htmx = bool(request.META.get("HTTP_HX_REQUEST", False))
        return self.get_response(request)

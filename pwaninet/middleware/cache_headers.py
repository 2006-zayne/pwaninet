"""
HTTP Caching Headers Middleware
Adds cache control headers to improve performance by allowing browsers to cache static resources
"""

class CacheHeadersMiddleware:
    """
    Middleware to add cache control headers to responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        from django.utils.cache import patch_vary_headers

        # Cache static assets for 1 year
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

        # Don't cache dynamic content (API, POST, and all HTML pages)
        content_type = response.get('Content-Type', '').lower()
        is_html = 'text/html' in content_type

        if is_html:
            patch_vary_headers(response, ['HX-Request'])

        if request.path.startswith('/api/') or request.method in ('POST', 'PUT', 'PATCH', 'DELETE') or is_html or request.path.endswith('.html'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response

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
        
        # Don't cache dynamic content
        if request.path.startswith('/api/') or request.method == 'POST':
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        
        # Cache static assets for 1 year
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response
        
        # Default: don't cache HTML pages (they may have user-specific content)
        if request.path.endswith('.html'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response

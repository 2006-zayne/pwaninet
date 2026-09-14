from django.test import SimpleTestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from unittest.mock import patch, MagicMock
from search.views import search_suggest_view, unified_search_view


class SearchViewsTestCase(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_search_suggest_short_query(self):
        request = self.factory.get(reverse('search:search_suggest'), {'q': 'a'})
        request.user = AnonymousUser()
        response = search_suggest_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_search_suggest_empty_query(self):
        request = self.factory.get(reverse('search:search_suggest'), {'q': ''})
        request.user = AnonymousUser()
        response = search_suggest_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    @patch('search.views.cache')
    @patch('search.views.UnifiedSearchService')
    def test_search_suggest_success(self, MockSearchService, mock_cache):
        mock_cache.get.return_value = None
        mock_instance = MockSearchService.return_value
        mock_instance.search.return_value = {
            'results': {'people': [], 'documents': [], 'posts': [], 'groups': []},
            'counts': {'all': 0, 'people': 0, 'documents': 0, 'posts': 0, 'groups': 0},
        }
        request = self.factory.get(reverse('search:search_suggest'), {'q': 'pwani'})
        request.user = AnonymousUser()
        response = search_suggest_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No results found', response.content)

    @patch('search.views.cache')
    @patch('search.views.UnifiedSearchService')
    @patch('search.views.logger')
    def test_search_suggest_exception_logged_and_handled_safely(self, mock_logger, MockSearchService, mock_cache):
        mock_cache.get.return_value = None
        mock_instance = MockSearchService.return_value
        mock_instance.search.side_effect = RuntimeError("Simulated search failure")

        request = self.factory.get(reverse('search:search_suggest'), {'q': 'crashme'})
        request.user = AnonymousUser()
        response = search_suggest_view(request)

        # Must not raise 500; must return empty 200 string
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        # Must log with exc_info=True
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        self.assertIn("crashme", args[1])
        self.assertTrue(kwargs.get('exc_info'))

    @patch('search.views.search_suggest_view')
    def test_unified_search_guard_for_dropdown_target(self, mock_suggest_view):
        mock_suggest_view.return_value = "suggest_response"
        request = self.factory.get(
            reverse('search:unified_search'),
            {'q': 'test'},
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='search-dropdown-results'
        )
        request.user = AnonymousUser()
        response = unified_search_view(request)
        mock_suggest_view.assert_called_once_with(request)
        self.assertEqual(response, "suggest_response")

package com.pwaninet.app;

import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.activity.EdgeToEdge;
import androidx.activity.SystemBarStyle;
import androidx.core.graphics.Insets;
import androidx.core.splashscreen.SplashScreen;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebViewClient;
import com.getcapacitor.WebViewListener;

import android.os.Handler;
import android.os.Looper;
import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;

public class MainActivity extends BridgeActivity {
    private boolean isNetworkAvailable = true;
    private boolean isOfflinePageShowing = false;
    private static final String WEBVIEW_STATE_KEY = "WEBVIEW_STATE";
    private volatile boolean isPageReady = false;
    private static final long SPLASH_WATCHDOG_TIMEOUT_MS = 6000L;

    private int lastSafeTop = 0;
    private int lastSafeBottom = 0;
    private int lastSafeLeft = 0;
    private int lastSafeRight = 0;

    public static class WebAppInterface {
        private final java.lang.ref.WeakReference<MainActivity> activityRef;

        public WebAppInterface(MainActivity activity) {
            this.activityRef = new java.lang.ref.WeakReference<>(activity);
        }

        @JavascriptInterface
        public void setSystemBarTheme(String theme) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                boolean isLight = !"dark".equalsIgnoreCase(theme);
                activity.applySystemBarTheme(isLight);
            }
        }

        @JavascriptInterface
        public void setNavigationBarTheme(String theme) {
            setSystemBarTheme(theme);
        }

        @JavascriptInterface
        public void openExternalUrl(String url) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.openExternalUrl(url);
            }
        }
    }

    public void applySystemBarTheme(boolean isLight) {
        runOnUiThread(() -> {
            try {
                Window window = getWindow();
                if (window == null) return;

                View decorView = window.getDecorView();
                WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, decorView);
                if (controller != null) {
                    controller.setAppearanceLightStatusBars(isLight);
                    controller.setAppearanceLightNavigationBars(isLight);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    private void setupAndroidBridge() {
        if (getBridge() != null && getBridge().getWebView() != null) {
            WebView webView = getBridge().getWebView();
            WebAppInterface bridge = new WebAppInterface(this);
            webView.addJavascriptInterface(bridge, "AndroidBridge");
            webView.addJavascriptInterface(bridge, "PwaninetBridge");
        }
    }

    public void injectThemeObserver() {
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                String js =
                    "(function() {" +
                    "  function syncTheme() {" +
                    "    var root = document.documentElement;" +
                    "    var theme = root.getAttribute('data-theme');" +
                    "    if (!theme || theme === 'system') {" +
                    "      var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;" +
                    "      theme = prefersDark ? 'dark' : 'light';" +
                    "    }" +
                    "    var isLight = theme !== 'dark';" +
                    "    var bridge = window.AndroidBridge || window.PwaninetBridge;" +
                    "    if (bridge && bridge.setSystemBarTheme) {" +
                    "      bridge.setSystemBarTheme(theme);" +
                    "    } else if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.NavigationBar) {" +
                    "      window.Capacitor.Plugins.NavigationBar.setStyle({ style: isLight ? 'LIGHT' : 'DARK' });" +
                    "    }" +
                    "  }" +
                    "  if (!window._pwaninet_native_theme_observer_active) {" +
                    "    window._pwaninet_native_theme_observer_active = true;" +
                    "    var observer = new MutationObserver(function(mutations) {" +
                    "      for (var i = 0; i < mutations.length; i++) {" +
                    "        if (mutations[i].attributeName === 'data-theme') {" +
                    "          syncTheme();" +
                    "          break;" +
                    "        }" +
                    "      }" +
                    "    });" +
                    "    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });" +
                    "    document.addEventListener('click', function() { setTimeout(syncTheme, 150); }, { passive: true });" +
                    "    window.addEventListener('storage', function(e) { if (e.key === 'theme') syncTheme(); });" +
                    "  }" +
                    "  syncTheme();" +
                    "})();";
                getBridge().getWebView().evaluateJavascript(js, null);
            }
        });
    }

    private void syncSystemBarThemeFromDom() {
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().evaluateJavascript(
                    "(function() {" +
                    "  var theme = document.documentElement.getAttribute('data-theme');" +
                    "  if (!theme || theme === 'system') {" +
                    "    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;" +
                    "    theme = prefersDark ? 'dark' : 'light';" +
                    "  }" +
                    "  return theme;" +
                    "})();",
                    themeValue -> {
                        if (themeValue != null) {
                            String cleanTheme = themeValue.replace("\"", "").trim();
                            if (!cleanTheme.isEmpty() && !"null".equalsIgnoreCase(cleanTheme) && !"undefined".equalsIgnoreCase(cleanTheme)) {
                                boolean isLight = !"dark".equalsIgnoreCase(cleanTheme);
                                applySystemBarTheme(isLight);
                            }
                        }
                    }
                );
            }
        });
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Keep splash screen on screen until WebView renders initial page content
        SplashScreen splashScreen = SplashScreen.installSplashScreen(this);
        splashScreen.setKeepOnScreenCondition(() -> !isPageReady);

        // Safety watchdog: ensure splash screen dismisses if network is slow or hangs
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            isPageReady = true;
        }, SPLASH_WATCHDOG_TIMEOUT_MS);

        registerPlugin(NavigationBarPlugin.class);

        // Configure edge-to-edge once at Activity creation
        EdgeToEdge.enable(this,
            SystemBarStyle.dark(Color.TRANSPARENT),
            SystemBarStyle.dark(Color.TRANSPARENT)
        );

        super.onCreate(savedInstanceState);

        boolean isSystemNight = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        applySystemBarTheme(!isSystemNight);

        setupAndroidBridge();
        setupSafeAreaInsets();
        setupNetworkMonitoring();
        setupCustomWebViewClient();
        setupWebViewCaching();

        // Ensure custom user agent identifier is appended
        if (this.bridge != null && this.bridge.getWebView() != null) {
            WebSettings settings = this.bridge.getWebView().getSettings();
            String defaultUserAgent = settings.getUserAgentString();
            settings.setUserAgentString(defaultUserAgent + " PwaniNetApp/Android");
        }
        
        // Restore WebView state if available
        if (savedInstanceState != null) {
            restoreWebViewState(savedInstanceState);
        }
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        
        // Save WebView state
        if (getBridge() != null && getBridge().getWebView() != null) {
            WebView webView = getBridge().getWebView();
            Bundle webViewState = new Bundle();
            webView.saveState(webViewState);
            outState.putBundle(WEBVIEW_STATE_KEY, webViewState);
            System.out.println("[MainActivity] WebView state saved");
        }
    }

    @Override
    public void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);
        
        // Restore WebView state
        if (savedInstanceState != null) {
            restoreWebViewState(savedInstanceState);
        }
    }

    private void restoreWebViewState(Bundle savedInstanceState) {
        if (getBridge() != null && getBridge().getWebView() != null) {
            Bundle webViewState = savedInstanceState.getBundle(WEBVIEW_STATE_KEY);
            if (webViewState != null) {
                WebView webView = getBridge().getWebView();
                webView.restoreState(webViewState);
                System.out.println("[MainActivity] WebView state restored");
            }
        }
    }

    private void setupNetworkMonitoring() {
        ConnectivityManager connectivityManager = 
            (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        
        if (connectivityManager != null) {
            NetworkRequest networkRequest = new NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build();
            
            connectivityManager.registerNetworkCallback(networkRequest, 
                new ConnectivityManager.NetworkCallback() {
                    @Override
                    public void onAvailable(Network network) {
                        boolean wasOffline = !isNetworkAvailable;
                        isNetworkAvailable = true;
                        runOnUiThread(() -> {
                            // Only reload or navigate if we were previously offline or currently showing the offline page
                            if ((wasOffline || isOfflinePageShowing) && getBridge() != null && getBridge().getWebView() != null) {
                                isOfflinePageShowing = false;
                                getBridge().getWebView().loadUrl("https://pwaninet.app");
                            }
                        });
                    }

                    @Override
                    public void onLost(Network network) {
                        isNetworkAvailable = false;
                    }
                });
            
            // Check initial network state
            Network activeNetwork = connectivityManager.getActiveNetwork();
            if (activeNetwork == null) {
                isNetworkAvailable = false;
            }
        }
    }

    public void openExternalUrl(String url) {
        if (url == null || url.trim().isEmpty()) return;
        runOnUiThread(() -> {
            try {
                Uri uri = Uri.parse(url.trim());
                Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                intent.addCategory(Intent.CATEGORY_BROWSABLE);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    private boolean isInternalHost(String host) {
        if (host == null) return true;
        host = host.toLowerCase(Locale.US);

        if (getBridge() != null && getBridge().getServerUrl() != null) {
            try {
                Uri serverUri = Uri.parse(getBridge().getServerUrl());
                if (serverUri != null && serverUri.getHost() != null && host.equalsIgnoreCase(serverUri.getHost())) {
                    return true;
                }
            } catch (Exception ignored) {}
        }

        return host.equals("pwaninet.app") ||
               host.endsWith(".pwaninet.app") ||
               host.equals("localhost") ||
               host.equals("127.0.0.1") ||
               host.equals("10.0.2.2") ||
               host.startsWith("192.168.");
    }

    private boolean handleExternalUri(Uri uri) {
        if (uri == null) return false;
        String scheme = uri.getScheme();
        if (scheme == null) return false;
        scheme = scheme.toLowerCase(Locale.US);

        // Allow WebView to handle internal data/blob/about/javascript
        if (scheme.equals("data") || scheme.equals("blob") || scheme.equals("about") || scheme.equals("javascript")) {
            return false;
        }

        // Custom protocols (e.g., tel:, mailto:, sms:, whatsapp:, market:)
        if (!scheme.equals("http") && !scheme.equals("https")) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
                return true;
            } catch (Exception e) {
                e.printStackTrace();
                return true;
            }
        }

        // For http/https, if host is external, launch via native Intent
        String host = uri.getHost();
        if (host != null && !isInternalHost(host)) {
            openExternalUrl(uri.toString());
            return true;
        }

        return false;
    }

    private void setupCustomWebViewClient() {
        if (getBridge() != null) {
            getBridge().setWebViewClient(new BridgeWebViewClient(getBridge()) {
                @Override
                public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    if (request != null && request.getUrl() != null) {
                        if (handleExternalUri(request.getUrl())) {
                            return true;
                        }
                    }
                    return super.shouldOverrideUrlLoading(view, request);
                }

                @Override
                public boolean shouldOverrideUrlLoading(WebView view, String url) {
                    if (url != null) {
                        if (handleExternalUri(Uri.parse(url))) {
                            return true;
                        }
                    }
                    return super.shouldOverrideUrlLoading(view, url);
                }

                @Override
                public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                    super.onReceivedError(view, request, error);
                    // Only handle genuine network failures on top-level main frame navigation
                    if (request != null && request.isForMainFrame()) {
                        int errorCode = 0;
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                            errorCode = error.getErrorCode();
                        }
                        if (errorCode == WebViewClient.ERROR_HOST_LOOKUP ||
                            errorCode == WebViewClient.ERROR_CONNECT ||
                            errorCode == WebViewClient.ERROR_TIMEOUT ||
                            !isNetworkAvailable) {
                            isPageReady = true;
                            isOfflinePageShowing = true;
                            loadOfflinePage(view);
                        }
                    }
                }

                @Override
                public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                    super.onReceivedError(view, errorCode, description, failingUrl);
                    if (errorCode == WebViewClient.ERROR_HOST_LOOKUP ||
                        errorCode == WebViewClient.ERROR_CONNECT ||
                        errorCode == WebViewClient.ERROR_TIMEOUT ||
                        !isNetworkAvailable) {
                        isPageReady = true;
                        isOfflinePageShowing = true;
                        loadOfflinePage(view);
                    }
                }
            });

            getBridge().addWebViewListener(new WebViewListener() {
                @Override
                public void onPageLoaded(WebView webView) {
                    isPageReady = true;
                    isOfflinePageShowing = false;
                    setupAndroidBridge();
                    injectSafeAreaInsets();
                    syncSystemBarThemeFromDom();
                    injectThemeObserver();
                }

                @Override
                public void onPageCommitVisible(WebView view, String url) {
                    isPageReady = true;
                    isOfflinePageShowing = false;
                    setupAndroidBridge();
                    injectSafeAreaInsets();
                    syncSystemBarThemeFromDom();
                    injectThemeObserver();
                }

                @Override
                public void onReceivedError(WebView webView) {
                    // Do NOT trigger loadOfflinePage here because WebViewListener
                    // receives callbacks for all subresources (images, fonts, canceled requests).
                    isPageReady = true;
                }
            });
        }
    }

    private void setupSafeAreaInsets() {
        View decorView = getWindow().getDecorView();
        ViewCompat.setOnApplyWindowInsetsListener(decorView, (v, windowInsets) -> {
            updateInsetsFrom(windowInsets);
            return ViewCompat.onApplyWindowInsets(v, windowInsets);
        });

        View contentView = findViewById(android.R.id.content);
        if (contentView != null) {
            ViewCompat.setOnApplyWindowInsetsListener(contentView, (v, windowInsets) -> {
                updateInsetsFrom(windowInsets);
                return ViewCompat.onApplyWindowInsets(v, windowInsets);
            });
        }

        // Check root insets immediately if already available
        WindowInsetsCompat rootInsets = ViewCompat.getRootWindowInsets(decorView);
        if (rootInsets != null) {
            updateInsetsFrom(rootInsets);
        } else if (hasNavigationBar()) {
            lastSafeBottom = getNavigationBarHeightDp();
            injectSafeAreaInsets();
        }
    }

    private void updateInsetsFrom(WindowInsetsCompat windowInsets) {
        if (windowInsets == null) return;

        Insets sysBars = windowInsets.getInsets(
            WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
        );
        Insets navBars = windowInsets.getInsets(WindowInsetsCompat.Type.navigationBars());

        float density = getResources().getDisplayMetrics().density;
        if (density > 0) {
            int top = Math.round(sysBars.top / density);
            int bottom = Math.round(Math.max(sysBars.bottom, navBars.bottom) / density);
            int left = Math.round(sysBars.left / density);
            int right = Math.round(sysBars.right / density);

            // Fallback for 3-button navigation if bottom reports 0 but system navigation bar exists
            if (bottom == 0 && hasNavigationBar()) {
                bottom = getNavigationBarHeightDp();
            }

            lastSafeTop = top;
            lastSafeBottom = bottom;
            lastSafeLeft = left;
            lastSafeRight = right;

            injectSafeAreaInsets();
        }
    }

    private boolean hasNavigationBar() {
        int id = getResources().getIdentifier("config_showNavigationBar", "bool", "android");
        return id > 0 && getResources().getBoolean(id);
    }

    private int getNavigationBarHeightDp() {
        int resourceId = getResources().getIdentifier("navigation_bar_height", "dimen", "android");
        if (resourceId > 0) {
            float density = getResources().getDisplayMetrics().density;
            if (density > 0) {
                return Math.round(getResources().getDimensionPixelSize(resourceId) / density);
            }
        }
        return 48; // Standard Android 3-button navigation height in dp
    }

    private void injectSafeAreaInsets() {
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                if (lastSafeBottom == 0) {
                    View decorView = getWindow().getDecorView();
                    WindowInsetsCompat rootInsets = ViewCompat.getRootWindowInsets(decorView);
                    if (rootInsets != null) {
                        float density = getResources().getDisplayMetrics().density;
                        if (density > 0) {
                            Insets navBars = rootInsets.getInsets(WindowInsetsCompat.Type.navigationBars());
                            Insets sysBars = rootInsets.getInsets(WindowInsetsCompat.Type.systemBars());
                            int b = Math.round(Math.max(sysBars.bottom, navBars.bottom) / density);
                            if (b > 0) lastSafeBottom = b;
                            int t = Math.round(sysBars.top / density);
                            if (t > 0) lastSafeTop = t;
                        }
                    }
                    if (lastSafeBottom == 0 && hasNavigationBar()) {
                        lastSafeBottom = getNavigationBarHeightDp();
                    }
                }

                String js = String.format(Locale.US,
                    "(function() {" +
                    "  var root = document.documentElement;" +
                    "  root.classList.add('is-capacitor', 'is-native-app');" +
                    "  root.style.setProperty('--pwaninet-safe-area-top', '%dpx');" +
                    "  root.style.setProperty('--pwaninet-safe-area-bottom', '%dpx');" +
                    "  root.style.setProperty('--pwaninet-safe-area-left', '%dpx');" +
                    "  root.style.setProperty('--pwaninet-safe-area-right', '%dpx');" +
                    "  if (document.body) {" +
                    "    document.body.classList.add('is-capacitor', 'is-native-app');" +
                    "    document.body.style.setProperty('--pwaninet-safe-area-top', '%dpx');" +
                    "    document.body.style.setProperty('--pwaninet-safe-area-bottom', '%dpx');" +
                    "  }" +
                    "  window.dispatchEvent(new CustomEvent('pwaninet:safe-area-changed', { detail: { top: %d, bottom: %d, left: %d, right: %d } }));" +
                    "})();",
                    lastSafeTop, lastSafeBottom, lastSafeLeft, lastSafeRight,
                    lastSafeTop, lastSafeBottom,
                    lastSafeTop, lastSafeBottom, lastSafeLeft, lastSafeRight
                );
                getBridge().getWebView().evaluateJavascript(js, null);
            }
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        injectSafeAreaInsets();
        syncSystemBarThemeFromDom();
        injectThemeObserver();
    }

    private void setupWebViewCaching() {
        if (getBridge() != null && getBridge().getWebView() != null) {
            WebView webView = getBridge().getWebView();
            
            // Set initial WebView background to match system splash background
            boolean isSystemNight = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
            webView.setBackgroundColor(isSystemNight ? Color.parseColor("#0f172a") : Color.WHITE);

            // Enable caching for better performance and offline support
            webView.getSettings().setDomStorageEnabled(true);
            webView.getSettings().setDatabaseEnabled(true);
            
            // Enable more aggressive caching - use cache when network is unavailable
            webView.getSettings().setCacheMode(android.webkit.WebSettings.LOAD_CACHE_ELSE_NETWORK);
            
            // Enable hardware acceleration for better performance
            webView.setLayerType(WebView.LAYER_TYPE_HARDWARE, null);
            
            System.out.println("[MainActivity] WebView caching enabled with hardware acceleration");
        }
    }

    private void loadOfflinePage(WebView webView) {
        isOfflinePageShowing = true;
        try {
            // Load the offline.html file from assets
            InputStream inputStream = getAssets().open("public/offline.html");
            StringBuilder htmlBuilder = new StringBuilder();
            
            byte[] buffer = new byte[1024];
            int length;
            while ((length = inputStream.read(buffer)) != -1) {
                htmlBuilder.append(new String(buffer, 0, length));
            }
            inputStream.close();
            
            webView.loadDataWithBaseURL("file:///android_asset/public/", 
                htmlBuilder.toString(), "text/html", "UTF-8", null);
        } catch (IOException e) {
            e.printStackTrace();
            // Fallback to simple error message if offline.html fails to load
            String fallbackHtml = "<html><body style='display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:sans-serif;text-align:center;'>" +
                "<div><h1>YOU ARE OFFLINE</h1><p>WE WILL RECONNECT WHEN YOU HAVE INTERNET ACCESS</p>" +
                "<button onclick='location.reload()'>Retry</button></div></body></html>";
            webView.loadData(fallbackHtml, "text/html", "UTF-8");
        }
    }
}

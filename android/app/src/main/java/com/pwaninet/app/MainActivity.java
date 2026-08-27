package com.pwaninet.app;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.activity.EdgeToEdge;
import androidx.activity.SystemBarStyle;

import com.getcapacitor.BridgeActivity;

import java.io.IOException;
import java.io.InputStream;

public class MainActivity extends BridgeActivity {
    private boolean isNetworkAvailable = true;
    private static final String WEBVIEW_STATE_KEY = "WEBVIEW_STATE";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Fixed style, not auto() — auto() continuously re-derives icon
        // appearance from the DEVICE's system theme and overrides any style
        // set via the StatusBar JS plugin, which is why in-app theme changes
        // were never reflected in the status/nav bar icons. The StatusBar
        // plugin (driven by data-theme, see initStatusBar()/
        // updateStatusBarForTheme() in the JS) is now the single source of
        // truth for icon appearance.
        EdgeToEdge.enable(this,
            SystemBarStyle.dark(Color.TRANSPARENT),
            SystemBarStyle.dark(Color.TRANSPARENT));
        
        // StatusBar plugin handles system bar transparency and edge-to-edge layout
        
        setupNetworkMonitoring();
        setupCustomWebViewClient();
        setupWebViewCaching();
        
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
                        isNetworkAvailable = true;
                        runOnUiThread(() -> {
                            // Reload the page when network becomes available
                            if (getBridge() != null && getBridge().getWebView() != null) {
                                getBridge().getWebView().reload();
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

    private void setupCustomWebViewClient() {
        if (getBridge() != null && getBridge().getWebView() != null) {
            getBridge().getWebView().setWebViewClient(new WebViewClient() {
                @Override
                public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                    // Handle network errors for navigation requests
                    if (request.isForMainFrame()) {
                        loadOfflinePage(view);
                    }
                }

                @Override
                public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    // Allow the WebView to handle all URL loading
                    return false;
                }
            });
        }
    }

    private void setupWebViewCaching() {
        if (getBridge() != null && getBridge().getWebView() != null) {
            WebView webView = getBridge().getWebView();
            
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

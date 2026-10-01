package com.pwaninet.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.DownloadManager;
import android.Manifest;
import android.content.Context;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.PackageInfo;
import android.content.res.Configuration;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.os.Environment;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.DownloadListener;
import android.webkit.CookieManager;
import android.webkit.URLUtil;

import androidx.activity.EdgeToEdge;
import androidx.activity.SystemBarStyle;
import androidx.core.graphics.Insets;
import androidx.core.content.ContextCompat;
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
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.view.HapticFeedbackConstants;
import android.widget.Toast;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLConnection;
import java.util.Locale;
import java.util.ArrayList;
import org.json.JSONObject;

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
    private String pendingDeepLinkPath = null;
    private static final int REQUEST_SPEECH_AUDIO_PERMISSION = 4301;
    private static final int REQUEST_MEDIA_DOWNLOAD_PERMISSION = 4302;
    private PendingMediaDownload pendingMediaDownload;

    private static final class PendingMediaDownload {
        final String url, filename, mimeType, category;
        PendingMediaDownload(String url, String filename, String mimeType, String category) {
            this.url = url; this.filename = filename; this.mimeType = mimeType; this.category = category;
        }
    }
    private SpeechRecognizer speechRecognizer;
    private boolean speechListening = false;
    private boolean speechSessionRequested = false;
    private String pendingSpeechLanguage = "en-US";

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

        @JavascriptInterface
        public boolean saveMediaToGallery(String sourceUri, String filename, String mimeType, String category) {
            MainActivity activity = activityRef.get();
            if (activity == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false;
            Uri collection = "video".equalsIgnoreCase(category)
                ? android.provider.MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                : android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI;
            ContentValues values = new ContentValues();
            values.put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, filename);
            values.put(android.provider.MediaStore.MediaColumns.MIME_TYPE, mimeType);
            values.put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH,
                "video".equalsIgnoreCase(category) ? "Movies/PwaniNet" : "Pictures/PwaniNet");
            values.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 1);
            Uri target = null;
            try {
                target = activity.getContentResolver().insert(collection, values);
                if (target == null) return false;
                try (InputStream input = activity.getContentResolver().openInputStream(Uri.parse(sourceUri));
                     OutputStream output = activity.getContentResolver().openOutputStream(target)) {
                    if (input == null || output == null) throw new IOException("Unable to open media stream");
                    byte[] buffer = new byte[8192];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                }
                ContentValues ready = new ContentValues();
                ready.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 0);
                activity.getContentResolver().update(target, ready, null, null);
                return true;
            } catch (Exception error) {
                if (target != null) activity.getContentResolver().delete(target, null, null);
                return false;
            }
        }

        @JavascriptInterface
        public String startMediaDownload(String url, String filename, String mimeType, String category) {
            MainActivity activity = activityRef.get();
            return activity == null ? "failed" : activity.startMediaDownload(url, filename, mimeType, category);
        }

        @JavascriptInterface
        public void hapticImpact(String style) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.performNativeHapticImpact(style);
            }
        }

        @JavascriptInterface
        public void hapticSelection() {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.performNativeHapticSelection();
            }
        }

        @JavascriptInterface
        public void hapticNotification(String type) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.performNativeHapticNotification(type);
            }
        }

        @JavascriptInterface
        public void vibrate(long durationMs) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.performNativeVibrate(durationMs);
            }
        }

        @JavascriptInterface
        public void showToast(String message) {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                activity.showToast(message);
            }
        }

        @JavascriptInterface
        public void startSpeechRecognition(String language) {
            MainActivity activity = activityRef.get();
            if (activity != null) activity.requestSpeechRecognition(language);
        }

        @JavascriptInterface
        public void stopSpeechRecognition() {
            MainActivity activity = activityRef.get();
            if (activity != null) activity.stopSpeechRecognition();
        }

        @JavascriptInterface
        public void cancelSpeechRecognition() {
            MainActivity activity = activityRef.get();
            if (activity != null) activity.cancelSpeechRecognition();
        }

        @JavascriptInterface
        public String getAppVersionInfo() {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                try {
                    PackageInfo pInfo = activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0);
                    String versionName = pInfo.versionName != null ? pInfo.versionName : "1.0.0";
                    long versionCode = 1;
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        versionCode = pInfo.getLongVersionCode();
                    } else {
                        versionCode = pInfo.versionCode;
                    }
                    return "{\"versionName\":\"" + versionName + "\",\"versionCode\":" + versionCode + "}";
                } catch (Exception e) {
                    return "{\"versionName\":\"1.0.0\",\"versionCode\":1}";
                }
            }
            return "{}";
        }

        @JavascriptInterface
        public boolean isPushNotificationsAvailable() {
            MainActivity activity = activityRef.get();
            if (activity != null) {
                return MainActivity.isFirebaseInitialized(activity);
            }
            return false;
        }
    }

    public static boolean isFirebaseInitialized(Context context) {
        try {
            Class<?> clazz = Class.forName("com.google.firebase.FirebaseApp");
            java.lang.reflect.Method getAppsMethod = clazz.getMethod("getApps", Context.class);
            java.util.List<?> apps = (java.util.List<?>) getAppsMethod.invoke(null, context);
            return apps != null && !apps.isEmpty();
        } catch (Throwable ignored) {
            return false;
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

    private void requestSpeechRecognition(String language) {
        runOnUiThread(() -> {
            speechSessionRequested = true;
            pendingSpeechLanguage = language == null || language.trim().isEmpty() ? "en-US" : language.trim();
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                speechSessionRequested = false;
                dispatchSpeechEvent("", false, "unavailable");
                return;
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[] { Manifest.permission.RECORD_AUDIO }, REQUEST_SPEECH_AUDIO_PERMISSION);
                return;
            }
            startSpeechRecognition();
        });
    }

    private void startSpeechRecognition() {
        runOnUiThread(() -> {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                speechSessionRequested = false;
                dispatchSpeechEvent("", false, "unavailable");
                return;
            }
            destroySpeechRecognizer();
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) { speechListening = true; }
                @Override public void onBeginningOfSpeech() { speechListening = true; }
                @Override public void onRmsChanged(float rmsdB) {
                    float level = Math.max(0f, Math.min(1f, (rmsdB + 2f) / 15f));
                    dispatchSpeechEvent("", false, null, level);
                }
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() { speechListening = false; }
                @Override public void onEvent(int eventType, Bundle params) {}

                @Override
                public void onPartialResults(Bundle partialResults) {
                    ArrayList<String> matches = partialResults == null ? null
                            : partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches != null && !matches.isEmpty()) dispatchSpeechEvent(matches.get(0), false, null);
                }

                @Override
                public void onResults(Bundle results) {
                    speechListening = false;
                    ArrayList<String> matches = results == null ? null
                            : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    // Always send a terminal event. An empty result is still completion and
                    // the WebView must not remain stuck in its transcribing state.
                    dispatchSpeechEvent(matches != null && !matches.isEmpty() ? matches.get(0) : "", true, null);
                    destroySpeechRecognizer();
                    if (speechSessionRequested) {
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            if (speechSessionRequested) startSpeechRecognition();
                        }, 250);
                    }
                }

                @Override
                public void onError(int error) {
                    speechListening = false;
                    boolean recoverable = error == SpeechRecognizer.ERROR_NO_MATCH
                            || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                            || error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY
                            || error == SpeechRecognizer.ERROR_NETWORK
                            || error == SpeechRecognizer.ERROR_NETWORK_TIMEOUT;
                    boolean retry = speechSessionRequested && recoverable;
                    if (!retry) speechSessionRequested = false;
                    dispatchSpeechEvent("", false, speechErrorName(error));
                    destroySpeechRecognizer();
                    if (retry) {
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            if (speechSessionRequested) startSpeechRecognition();
                        }, 400);
                    }
                }
            });

            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, pendingSpeechLanguage);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            // Keep ordinary pauses inside the same recognition session. Restarting after every
            // short silence can replay the Android listening chime and interrupts dictation.
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 8000L);
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 10000L);
            try {
                speechRecognizer.startListening(intent);
                speechListening = true;
            } catch (Exception error) {
                speechListening = false;
                speechSessionRequested = false;
                dispatchSpeechEvent("", false, "start-failed");
                destroySpeechRecognizer();
            }
        });
    }

    private void stopSpeechRecognition() {
        runOnUiThread(() -> {
            speechSessionRequested = false;
            // onResults destroys the recognizer before the continuous-listening restart is
            // scheduled. A stop during that gap must complete the JS session itself.
            if (speechRecognizer == null) {
                dispatchSpeechEvent("", true, null);
                return;
            }
            try {
                speechRecognizer.stopListening();
            } catch (Exception ignored) {
                destroySpeechRecognizer();
                dispatchSpeechEvent("", true, null);
            }
        });
    }

    private void cancelSpeechRecognition() {
        runOnUiThread(() -> {
            speechSessionRequested = false;
            destroySpeechRecognizer();
        });
    }

    private void destroySpeechRecognizer() {
        if (speechRecognizer != null) {
            try { speechRecognizer.setRecognitionListener(null); } catch (Exception ignored) {}
            try { speechRecognizer.cancel(); } catch (Exception ignored) {}
            try { speechRecognizer.destroy(); } catch (Exception ignored) {}
            speechRecognizer = null;
        }
        speechListening = false;
    }

    private void dispatchSpeechEvent(String text, boolean isFinal, String error) {
        dispatchSpeechEvent(text, isFinal, error, null);
    }

    private void dispatchSpeechEvent(String text, boolean isFinal, String error, Float level) {
        JSONObject detail = new JSONObject();
        try {
            detail.put("text", text == null ? "" : text);
            detail.put("final", isFinal);
            detail.put("listening", speechSessionRequested);
            if (level != null) detail.put("level", level);
            if (error != null) detail.put("error", error);
        } catch (Exception ignored) {}
        String js = "window.dispatchEvent(new CustomEvent('pwaninet:native-speech', {detail:" + detail + "}));";
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().evaluateJavascript(js, null);
            }
        });
    }

    private String speechErrorName(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO: return "audio";
            case SpeechRecognizer.ERROR_CLIENT: return "client";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "permission";
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "network";
            case SpeechRecognizer.ERROR_NO_MATCH:
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "no-speech";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "busy";
            case SpeechRecognizer.ERROR_SERVER: return "server";
            default: return "unknown";
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_MEDIA_DOWNLOAD_PERMISSION) {
            PendingMediaDownload pending = pendingMediaDownload;
            pendingMediaDownload = null;
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED && pending != null) {
                startMediaDownload(pending.url, pending.filename, pending.mimeType, pending.category);
            } else {
                Toast.makeText(this, "Storage permission is needed to save media on this Android version.", Toast.LENGTH_LONG).show();
            }
            return;
        }
        if (requestCode != REQUEST_SPEECH_AUDIO_PERMISSION) return;
        if (!speechSessionRequested) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startSpeechRecognition();
        } else {
            speechSessionRequested = false;
            dispatchSpeechEvent("", false, "permission");
        }
    }

    @Override
    public void onDestroy() {
        destroySpeechRecognizer();
        super.onDestroy();
    }

    private void setupNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                NotificationManager notificationManager = getSystemService(NotificationManager.class);
                if (notificationManager != null) {
                    NotificationChannel defaultChannel = new NotificationChannel(
                        "pwaninet_notifications",
                        "PwaniNet Notifications",
                        NotificationManager.IMPORTANCE_HIGH
                    );
                    defaultChannel.setDescription("All social updates, mentions, posts, documents, and messages");
                    defaultChannel.enableVibration(true);
                    defaultChannel.enableLights(true);
                    defaultChannel.setLightColor(Color.parseColor("#2563eb"));
                    notificationManager.createNotificationChannel(defaultChannel);

                    NotificationChannel socialChannel = new NotificationChannel(
                        "pwaninet_social",
                        "Social Updates",
                        NotificationManager.IMPORTANCE_HIGH
                    );
                    socialChannel.setDescription("Likes, comments, shares, follows, and mentions");
                    socialChannel.enableVibration(true);
                    notificationManager.createNotificationChannel(socialChannel);

                    NotificationChannel messagesChannel = new NotificationChannel(
                        "pwaninet_messages",
                        "Direct & Group Messages",
                        NotificationManager.IMPORTANCE_HIGH
                    );
                    messagesChannel.setDescription("Chat messages and conversation updates");
                    messagesChannel.enableVibration(true);
                    notificationManager.createNotificationChannel(messagesChannel);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public void injectThemeObserver() {
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                String js =
                    "(function() {" +
                    "  function syncTheme() {" +
                    "    if (document.body && document.body.classList.contains('reels-active')) {" +
                    "      var bridge = window.AndroidBridge || window.PwaninetBridge;" +
                    "      if (bridge && bridge.setSystemBarTheme) {" +
                    "        bridge.setSystemBarTheme('dark');" +
                    "      } else if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.NavigationBar) {" +
                    "        window.Capacitor.Plugins.NavigationBar.setStyle({ style: 'DARK' });" +
                    "      }" +
                    "      return;" +
                    "    }" +
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
                    "  if (document.body && document.body.classList.contains('reels-active')) {" +
                    "    return 'dark';" +
                    "  }" +
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
        // Crash Guard: intercept uninitialized FirebaseApp crashes on background threads gracefully
        final Thread.UncaughtExceptionHandler defaultHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            boolean isFirebaseMissing = false;
            Throwable current = throwable;
            while (current != null) {
                String msg = current.getMessage();
                if (msg != null && (msg.contains("Default FirebaseApp is not initialized") || msg.contains("FirebaseApp.initializeApp"))) {
                    isFirebaseMissing = true;
                    break;
                }
                current = current.getCause();
            }

            if (isFirebaseMissing) {
                System.err.println("[MainActivity] Gracefully suppressed uninitialized FirebaseApp crash on thread '" + (thread != null ? thread.getName() : "unknown") + "'");
                return;
            }

            if (defaultHandler != null) {
                defaultHandler.uncaughtException(thread, throwable);
            }
        });

        // Initialize Firebase safely if google-services.json was packaged or credentials exist
        try {
            Class<?> clazz = Class.forName("com.google.firebase.FirebaseApp");
            java.lang.reflect.Method getAppsMethod = clazz.getMethod("getApps", Context.class);
            java.util.List<?> apps = (java.util.List<?>) getAppsMethod.invoke(null, this);
            if (apps != null && apps.isEmpty()) {
                java.lang.reflect.Method initMethod = clazz.getMethod("initializeApp", Context.class);
                initMethod.invoke(null, this);
            }
        } catch (Throwable ignored) {}

        // Keep splash screen on screen until WebView renders initial page content
        SplashScreen splashScreen = SplashScreen.installSplashScreen(this);
        splashScreen.setKeepOnScreenCondition(() -> !isPageReady);

        // Safety watchdog: ensure splash screen dismisses if network is slow or hangs
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            isPageReady = true;
        }, SPLASH_WATCHDOG_TIMEOUT_MS);

        registerPlugin(NavigationBarPlugin.class);
        registerPlugin(HapticsPlugin.class);

        // Configure edge-to-edge once at Activity creation
        EdgeToEdge.enable(this,
            SystemBarStyle.dark(Color.TRANSPARENT),
            SystemBarStyle.dark(Color.TRANSPARENT)
        );

        super.onCreate(savedInstanceState);

        boolean isSystemNight = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        applySystemBarTheme(!isSystemNight);

        setupAndroidBridge();
        setupNotificationChannels();
        setupSafeAreaInsets();
        setupNetworkMonitoring();
        setupCustomWebViewClient();
        setupWebViewCaching();
        setupWebViewDownloads();

        // Ensure custom user agent identifier with version and build is appended
        if (this.bridge != null && this.bridge.getWebView() != null) {
            WebSettings settings = this.bridge.getWebView().getSettings();
            String defaultUserAgent = settings.getUserAgentString();
            String appVersion = "1.0.0";
            long appCode = 1;
            try {
                PackageInfo pInfo = getPackageManager().getPackageInfo(getPackageName(), 0);
                if (pInfo.versionName != null) {
                    appVersion = pInfo.versionName;
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    appCode = pInfo.getLongVersionCode();
                } else {
                    appCode = pInfo.versionCode;
                }
            } catch (Exception ignored) {}
            settings.setUserAgentString(defaultUserAgent + " PwaniNetApp/Android/" + appVersion + " (Build/" + appCode + ")");
        }
        
        // Restore WebView state if available
        if (savedInstanceState != null) {
            restoreWebViewState(savedInstanceState);
        }

        // Check if app was launched via deep link Intent
        if (getIntent() != null) {
            handleDeepLinkIntent(getIntent());
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleDeepLinkIntent(intent);
    }

    private void handleDeepLinkIntent(Intent intent) {
        if (intent == null) return;
        Uri data = intent.getData();
        if (data == null) return;

        String path = null;
        String scheme = data.getScheme();
        if ("pwaninet".equalsIgnoreCase(scheme)) {
            String host = data.getHost();
            String dataPath = data.getPath();
            if (host != null && !host.isEmpty() && !host.contains(".")) {
                path = "/" + host + (dataPath != null ? dataPath : "");
            } else if (dataPath != null && !dataPath.isEmpty()) {
                path = dataPath;
            } else {
                path = "/";
            }
        } else if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
            String dataPath = data.getPath();
            String dataQuery = data.getQuery();
            path = (dataPath != null ? dataPath : "/") + (dataQuery != null ? "?" + dataQuery : "");
        }

        if (path != null && !path.isEmpty()) {
            final String targetPath = path;
            if (!isPageReady) {
                pendingDeepLinkPath = targetPath;
            } else {
                executeDeepLinkNavigation(targetPath);
            }
        }
    }

    private void executeDeepLinkNavigation(String targetPath) {
        if (targetPath == null || targetPath.isEmpty()) return;
        runOnUiThread(() -> {
            if (getBridge() != null && getBridge().getWebView() != null) {
                WebView webView = getBridge().getWebView();
                String js = "(function() {" +
                            "  var target = '" + targetPath.replace("'", "\\'") + "';" +
                            "  if (window.htmx && document.getElementById('page-content-target')) {" +
                            "    window.htmx.ajax('GET', target, { target: '#page-content-target', swap: 'innerHTML' });" +
                            "    window.history.pushState({}, '', target);" +
                            "  } else {" +
                            "    window.location.href = target;" +
                            "  }" +
                            "})();";
                webView.evaluateJavascript(js, null);
            }
        });
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
                            // Only reload if showing the offline fallback error page and not actively viewing offline media
                            String currentUrl = (getBridge() != null && getBridge().getWebView() != null) ? getBridge().getWebView().getUrl() : null;
                            boolean isViewingOfflineMedia = currentUrl != null && currentUrl.contains("/offline-media");

                            if (isOfflinePageShowing && !isViewingOfflineMedia && getBridge() != null && getBridge().getWebView() != null) {
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

                    if (pendingDeepLinkPath != null) {
                        String path = pendingDeepLinkPath;
                        pendingDeepLinkPath = null;
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            executeDeepLinkNavigation(path);
                        }, 300);
                    }
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

    private void setupWebViewDownloads() {
        if (getBridge() == null || getBridge().getWebView() == null) return;

        getBridge().getWebView().setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            try {
                Uri downloadUri = Uri.parse(url);
                DownloadManager downloadManager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                if (downloadManager == null) {
                    Toast.makeText(this, "Unable to start download", Toast.LENGTH_SHORT).show();
                    return;
                }

                String filename = URLUtil.guessFileName(url, contentDisposition, mimeType);
                filename = filename == null ? "pwaninet-resource" : filename.replaceAll("[\\\\/:*?\"<>|]", "_");
                DownloadManager.Request downloadRequest = new DownloadManager.Request(downloadUri)
                    .setTitle(filename)
                    .setDescription("Downloading from PwaniNet")
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "PwaniNet/" + filename);

                if (mimeType != null && !mimeType.isEmpty()) downloadRequest.setMimeType(mimeType);
                if (userAgent != null && !userAgent.isEmpty()) downloadRequest.addRequestHeader("User-Agent", userAgent);
                String cookies = CookieManager.getInstance().getCookie(url);
                if (cookies != null && !cookies.isEmpty()) downloadRequest.addRequestHeader("Cookie", cookies);

                downloadManager.enqueue(downloadRequest);
                Toast.makeText(this, "Download started. Find it in Downloads/PwaniNet", Toast.LENGTH_LONG).show();
            } catch (Exception error) {
                System.err.println("[MainActivity] Could not start WebView download: " + error.getMessage());
                Toast.makeText(this, "Unable to start download", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private String startMediaDownload(String url, String filename, String mimeType, String category) {
        if (url == null || !url.startsWith("https://") && !url.startsWith("http://")) return "failed";
        String safeName = filename == null || filename.trim().isEmpty() ? "pwaninet-media" : filename;
        safeName = safeName.replaceAll("[\\\\/:*?\"<>|]", "_");
        boolean isImage = "image".equalsIgnoreCase(category);
        boolean isVideo = "video".equalsIgnoreCase(category) || "reels".equalsIgnoreCase(category);
        if (!isImage && !isVideo && (mimeType == null || mimeType.isEmpty())) {
            mimeType = URLConnection.guessContentTypeFromName(safeName);
        }
        final String resolvedMimeType = mimeType == null || mimeType.isEmpty()
            ? (isImage ? "image/jpeg" : isVideo ? "video/mp4" : "application/octet-stream")
            : mimeType;

        // On Android 10+ write straight into the shared MediaStore collection. This
        // avoids scoped-storage restrictions on DownloadManager's public-directory
        // destination and makes the finished item immediately visible to gallery apps.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && (isImage || isVideo)) {
            final String displayName = safeName;
            final String destination = url;
            final String mediaType = resolvedMimeType;
            final String webViewUserAgent = getBridge() != null && getBridge().getWebView() != null
                ? getBridge().getWebView().getSettings().getUserAgentString()
                : System.getProperty("http.agent", "PwaniNet");
            new Thread(() -> {
                Uri target = null;
                try {
                    java.net.HttpURLConnection connection = (java.net.HttpURLConnection) new java.net.URL(destination).openConnection();
                    connection.setConnectTimeout(20000);
                    connection.setReadTimeout(60000);
                    connection.setInstanceFollowRedirects(true);
                    connection.setRequestProperty("User-Agent", webViewUserAgent);
                    String cookies = CookieManager.getInstance().getCookie(destination);
                    if (cookies != null && !cookies.isEmpty()) connection.setRequestProperty("Cookie", cookies);
                    connection.connect();
                    int responseCode = connection.getResponseCode();
                    if (responseCode < 200 || responseCode >= 300) {
                        throw new IOException("Media server returned HTTP " + responseCode);
                    }
                    String responseMimeType = connection.getContentType();
                    if (responseMimeType != null && responseMimeType.contains(";")) {
                        responseMimeType = responseMimeType.substring(0, responseMimeType.indexOf(';')).trim();
                    }
                    Uri collection = isVideo
                        ? android.provider.MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                        : android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI;
                    ContentValues values = new ContentValues();
                    values.put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, displayName);
                    values.put(android.provider.MediaStore.MediaColumns.MIME_TYPE,
                        responseMimeType != null && responseMimeType.startsWith(isVideo ? "video/" : "image/")
                            ? responseMimeType : mediaType);
                    values.put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH,
                        isVideo ? "Movies/PwaniNet" : "Pictures/PwaniNet");
                    values.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 1);
                    target = getContentResolver().insert(collection, values);
                    if (target == null) throw new IOException("Could not create gallery media entry");

                    try (InputStream input = connection.getInputStream();
                         OutputStream output = getContentResolver().openOutputStream(target, "w")) {
                        if (output == null) throw new IOException("Could not open gallery media entry");
                        byte[] buffer = new byte[32768];
                        int count;
                        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                    } finally {
                        connection.disconnect();
                    }
                    ContentValues ready = new ContentValues();
                    ready.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 0);
                    getContentResolver().update(target, ready, null, null);
                    runOnUiThread(() -> Toast.makeText(this, "Saved to your gallery", Toast.LENGTH_LONG).show());
                } catch (Exception error) {
                    if (target != null) getContentResolver().delete(target, null, null);
                    System.err.println("[MainActivity] Gallery download failed: " + error.getMessage());
                    runOnUiThread(() -> Toast.makeText(this, "Could not save media. Check your connection and try again.", Toast.LENGTH_LONG).show());
                }
            }, "pwaninet-media-download").start();
            Toast.makeText(this, "Saving to your gallery…", Toast.LENGTH_SHORT).show();
            return "started";
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            pendingMediaDownload = new PendingMediaDownload(url, safeName, mimeType, category);
            requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, REQUEST_MEDIA_DOWNLOAD_PERMISSION);
            Toast.makeText(this, "Allow storage access to save this media", Toast.LENGTH_LONG).show();
            return "permission_requested";
        }
        try {
            DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            if (manager == null) return "failed";
            Uri uri = Uri.parse(url);
            String destinationDirectory = isImage ? Environment.DIRECTORY_PICTURES
                : isVideo ? Environment.DIRECTORY_MOVIES : Environment.DIRECTORY_DOWNLOADS;
            DownloadManager.Request request = new DownloadManager.Request(uri)
                .setTitle(safeName)
                .setDescription("Downloading from PwaniNet")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(destinationDirectory, "PwaniNet/" + safeName);
            request.setMimeType(resolvedMimeType);
            String cookies = CookieManager.getInstance().getCookie(url);
            if (cookies != null && !cookies.isEmpty()) request.addRequestHeader("Cookie", cookies);
            request.addRequestHeader("User-Agent", System.getProperty("http.agent", "PwaniNet"));
            manager.enqueue(request);
            Toast.makeText(this, "Download started. You can find it in your gallery or Downloads.", Toast.LENGTH_LONG).show();
            return "started";
        } catch (Exception error) {
            System.err.println("[MainActivity] Could not start media download: " + error.getMessage());
            Toast.makeText(this, "Unable to start download. Check storage permission and try again.", Toast.LENGTH_LONG).show();
            return "failed";
        }
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

    private Vibrator getVibratorService() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                VibratorManager vibratorManager = (VibratorManager) getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                if (vibratorManager != null) {
                    return vibratorManager.getDefaultVibrator();
                }
            }
            return (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        } catch (Exception ignored) {
            return null;
        }
    }

    public void performNativeHapticImpact(String style) {
        runOnUiThread(() -> {
            try {
                String cleanStyle = style != null ? style.trim().toLowerCase(Locale.US) : "light";
                Vibrator vibrator = getVibratorService();
                boolean vibratorHandled = false;
                if (vibrator != null && vibrator.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        int effectId = VibrationEffect.EFFECT_CLICK;
                        if ("light".equals(cleanStyle)) {
                            effectId = VibrationEffect.EFFECT_TICK;
                        } else if ("heavy".equals(cleanStyle)) {
                            effectId = VibrationEffect.EFFECT_HEAVY_CLICK;
                        }
                        try {
                            vibrator.vibrate(VibrationEffect.createPredefined(effectId));
                            vibratorHandled = true;
                        } catch (Exception e) {
                            int amp = "light".equals(cleanStyle) ? 60 : ("heavy".equals(cleanStyle) ? 220 : 130);
                            int dur = "light".equals(cleanStyle) ? 12 : ("heavy".equals(cleanStyle) ? 35 : 20);
                            vibrator.vibrate(VibrationEffect.createOneShot(dur, amp));
                            vibratorHandled = true;
                        }
                    } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        int amplitude = "light".equals(cleanStyle) ? 60 : ("heavy".equals(cleanStyle) ? 220 : 130);
                        int duration = "light".equals(cleanStyle) ? 12 : ("heavy".equals(cleanStyle) ? 35 : 20);
                        vibrator.vibrate(VibrationEffect.createOneShot(duration, amplitude));
                        vibratorHandled = true;
                    }
                }

                if (!vibratorHandled) {
                    View view = getBridge() != null && getBridge().getWebView() != null 
                        ? getBridge().getWebView() 
                        : getWindow().getDecorView();
                    if (view != null) {
                        int feedbackConstant = HapticFeedbackConstants.VIRTUAL_KEY;
                        if ("light".equals(cleanStyle)) {
                            feedbackConstant = HapticFeedbackConstants.KEYBOARD_TAP;
                        } else if ("heavy".equals(cleanStyle)) {
                            feedbackConstant = HapticFeedbackConstants.LONG_PRESS;
                        }
                        view.performHapticFeedback(feedbackConstant, HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
                    }
                }
            } catch (Exception ignored) {}
        });
    }

    public void performNativeHapticSelection() {
        runOnUiThread(() -> {
            try {
                Vibrator vibrator = getVibratorService();
                if (vibrator != null && vibrator.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        vibrator.vibrate(VibrationEffect.createPredefined(VibrationEffect.EFFECT_TICK));
                        return;
                    } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        vibrator.vibrate(VibrationEffect.createOneShot(8, 50));
                        return;
                    }
                }
                View view = getBridge() != null && getBridge().getWebView() != null 
                    ? getBridge().getWebView() 
                    : getWindow().getDecorView();
                view.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK, HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
            } catch (Exception ignored) {}
        });
    }

    public void performNativeHapticNotification(String type) {
        runOnUiThread(() -> {
            try {
                Vibrator vibrator = getVibratorService();
                String cleanType = type != null ? type.trim().toLowerCase(Locale.US) : "success";
                if (vibrator != null && vibrator.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        if ("success".equals(cleanType)) {
                            vibrator.vibrate(VibrationEffect.createPredefined(VibrationEffect.EFFECT_DOUBLE_CLICK));
                            return;
                        }
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        if ("error".equals(cleanType)) {
                            long[] timings = {0, 40, 60, 40, 60, 60};
                            int[] amplitudes = {0, 200, 0, 200, 0, 255};
                            vibrator.vibrate(VibrationEffect.createWaveform(timings, amplitudes, -1));
                            return;
                        } else if ("warning".equals(cleanType)) {
                            long[] timings = {0, 50, 80, 50};
                            int[] amplitudes = {0, 180, 0, 180};
                            vibrator.vibrate(VibrationEffect.createWaveform(timings, amplitudes, -1));
                            return;
                        } else { // success
                            long[] timings = {0, 20, 60, 30};
                            int[] amplitudes = {0, 120, 0, 180};
                            vibrator.vibrate(VibrationEffect.createWaveform(timings, amplitudes, -1));
                            return;
                        }
                    }
                }
                View view = getBridge() != null && getBridge().getWebView() != null 
                    ? getBridge().getWebView() 
                    : getWindow().getDecorView();
                view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY, HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
            } catch (Exception ignored) {}
        });
    }

    public void performNativeVibrate(long durationMs) {
        runOnUiThread(() -> {
            try {
                Vibrator vibrator = getVibratorService();
                if (vibrator != null && vibrator.hasVibrator()) {
                    long dur = Math.max(10, Math.min(durationMs, 2000));
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        vibrator.vibrate(VibrationEffect.createOneShot(dur, VibrationEffect.DEFAULT_AMPLITUDE));
                    } else {
                        vibrator.vibrate(dur);
                    }
                }
            } catch (Exception ignored) {}
        });
    }

    public void showToast(String message) {
        runOnUiThread(() -> {
            try {
                if (message != null && !message.trim().isEmpty()) {
                    Toast.makeText(this, message.trim(), Toast.LENGTH_SHORT).show();
                }
            } catch (Exception ignored) {}
        });
    }
}

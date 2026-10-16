package com.vasto.app;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;

/**
 * In-place APK updater for sideloaded (non-Play) distribution.
 *
 * Same signing key + higher versionCode installs cleanly OVER the
 * existing app, preserving login, sessions and app data — no uninstall.
 * Android always shows one system "Install" confirmation; silent install
 * is reserved for Play/system updaters and is not possible here.
 */
@CapacitorPlugin(name = "AppUpdater")
public class AppUpdaterPlugin extends Plugin {

    private static final String APK_FILE_NAME = "vasto-update.apk";
    private static final String APK_MIME = "application/vnd.android.package-archive";

    private BroadcastReceiver completionReceiver = null;
    private long activeDownloadId = -1;
    private PluginCall pendingCall = null;

    @PluginMethod
    public void downloadAndInstall(final PluginCall call) {
        String url = call.getString("url");
        if (url == null || url.isEmpty()) {
            call.reject("url is required");
            return;
        }
        // One update at a time; a repeat tap while downloading is a no-op.
        if (pendingCall != null) {
            call.reject("update already in progress");
            return;
        }
        pendingCall = call;
        // Keep the call alive until download completes or fails.
        call.setKeepAlive(true);

        try {
            Context ctx = getContext();
            File target = new File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    APK_FILE_NAME);
            if (target.exists()) {
                //noinspection ResultOfMethodCallIgnored
                target.delete();
            }

            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle("Vasto update");
            request.setDescription("Downloading new version…");
            request.setMimeType(APK_MIME);
            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationUri(Uri.fromFile(target));
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
                //noinspection deprecation
                request.allowScanningByMediaScanner();
            }

            DownloadManager dm = (DownloadManager) ctx.getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm == null) {
                finishWithError("download service unavailable");
                return;
            }
            activeDownloadId = dm.enqueue(request);
            registerCompletionReceiver(ctx);
        } catch (Exception e) {
            finishWithError("failed to start download: " + e.getMessage());
        }
    }

    @PluginMethod
    public void getStatus(final PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("supported", true);
        ret.put("downloading", pendingCall != null);
        call.resolve(ret);
    }

    private void registerCompletionReceiver(Context ctx) {
        unregisterCompletionReceiver(ctx);
        completionReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                if (id != activeDownloadId) {
                    return;
                }
                handleDownloadFinished(context);
            }
        };
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ctx.registerReceiver(completionReceiver,
                    new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
                    Context.RECEIVER_NOT_EXPORTED);
        } else {
            ctx.registerReceiver(completionReceiver,
                    new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
        }
    }

    private void unregisterCompletionReceiver(Context ctx) {
        if (completionReceiver != null) {
            try {
                ctx.unregisterReceiver(completionReceiver);
            } catch (IllegalArgumentException ignored) {
                // Already unregistered.
            }
            completionReceiver = null;
        }
    }

    private void handleDownloadFinished(Context ctx) {
        DownloadManager dm = (DownloadManager) ctx.getSystemService(Context.DOWNLOAD_SERVICE);
        boolean ok = false;
        String localUri = null;
        if (dm != null) {
            DownloadManager.Query query = new DownloadManager.Query().setFilterById(activeDownloadId);
            try (Cursor cursor = dm.query(query)) {
                if (cursor != null && cursor.moveToFirst()) {
                    int status = cursor.getInt(
                            cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
                    if (status == DownloadManager.STATUS_SUCCESSFUL) {
                        ok = true;
                        int uriIdx = cursor.getColumnIndex(DownloadManager.COLUMN_LOCAL_URI);
                        if (uriIdx != -1) {
                            localUri = cursor.getString(uriIdx);
                        }
                    }
                }
            } catch (Exception e) {
                ok = false;
            }
        }
        if (!ok) {
            finishWithError("download failed — check connection and retry");
            return;
        }

        try {
            File apk = new File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    APK_FILE_NAME);
            Uri contentUri = FileProvider.getUriForFile(
                    ctx, ctx.getPackageName() + ".fileprovider", apk);
            // localUri unused beyond verification; FileProvider path is authoritative.
            if (localUri == null) {
                android.util.Log.w("AppUpdater", "No local URI; using FileProvider path");
            }
            Intent install = new Intent(Intent.ACTION_VIEW);
            install.setDataAndType(contentUri, APK_MIME);
            install.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            ctx.startActivity(install);

            JSObject ret = new JSObject();
            ret.put("status", "install_started");
            finishWithResult(ret);
        } catch (Exception e) {
            finishWithError("could not launch installer: " + e.getMessage());
        }
    }

    private void finishWithResult(JSObject ret) {
        PluginCall call = pendingCall;
        cleanup();
        if (call != null) {
            call.resolve(ret);
        }
    }

    private void finishWithError(String message) {
        PluginCall call = pendingCall;
        cleanup();
        if (call != null) {
            call.reject(message);
        }
    }

    private void cleanup() {
        pendingCall = null;
        activeDownloadId = -1;
        try {
            unregisterCompletionReceiver(getContext());
        } catch (Exception ignored) {
        }
    }
}

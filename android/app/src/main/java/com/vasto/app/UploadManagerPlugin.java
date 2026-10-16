package com.vasto.app;

import android.content.Context;
import android.net.Uri;
import android.webkit.CookieManager;

import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkInfo;
import androidx.work.WorkManager;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Phase 4: Capacitor bridge for headless uploads.
 *
 * Files are copied into app-private staging so the worker owns the bytes
 * independent of the WebView. WorkManager persists the job across app close,
 * process kill, and reboot (force-stop excepted — an OS rule).
 */
@CapacitorPlugin(name = "UploadManager")
public class UploadManagerPlugin extends Plugin {

    private static final String STAGING_DIR = "upload_staging";

    @PluginMethod
    public void ensureUpload(final PluginCall call) {
        final String clientUploadId = call.getString("clientUploadId");
        if (clientUploadId == null || clientUploadId.isEmpty()) {
            call.reject("clientUploadId is required");
            return;
        }
        new Thread(() -> {
            try {
                Context ctx = getContext();
                List<WorkInfo> infos = WorkManager.getInstance(ctx)
                        .getWorkInfosForUniqueWork(clientUploadId).get();
                for (WorkInfo info : infos) {
                    WorkInfo.State state = info.getState();
                    if (state == WorkInfo.State.ENQUEUED || state == WorkInfo.State.RUNNING) {
                        JSObject ret = new JSObject();
                        ret.put("workId", info.getId().toString());
                        ret.put("state", state.name());
                        ret.put("resumed", true);
                        call.resolve(ret);
                        return;
                    }
                }
                // No live worker: (re)stage bytes if a fresh URI was supplied, then enqueue.
                String fileUri = call.getString("fileUri");
                File staged = stagedFile(ctx, clientUploadId);
                if (fileUri != null && !fileUri.isEmpty()) {
                    stageUri(ctx, Uri.parse(fileUri), staged);
                    writeMeta(ctx, clientUploadId, call.getData());
                }
                if (!staged.exists()) {
                    call.reject("FILE_MISSING",
                            "Original file unavailable — ask the user to re-select it");
                    return;
                }
                enqueue(ctx, call, staged);
            } catch (Exception e) {
                call.reject("Enqueue failed: " + e.getMessage());
            }
        }).start();
    }

    /** Re-enqueue every staged job that has no live worker (post-restart sweep). */
    @PluginMethod
    public void resumePending(final PluginCall call) {
        new Thread(() -> {
            try {
                Context ctx = getContext();
                File dir = new File(ctx.getFilesDir(), STAGING_DIR);
                File[] entries = dir.listFiles();
                int resumed = 0;
                if (entries != null) {
                    for (File entry : entries) {
                        File meta = new File(entry, "meta.json");
                        File source = new File(entry, "source");
                        if (!meta.exists() || !source.exists()) continue;
                        String clientUploadId = entry.getName();
                        List<WorkInfo> infos = WorkManager.getInstance(ctx)
                                .getWorkInfosForUniqueWork(clientUploadId).get();
                        boolean live = false;
                        for (WorkInfo info : infos) {
                            WorkInfo.State state = info.getState();
                            if (state == WorkInfo.State.ENQUEUED || state == WorkInfo.State.RUNNING) {
                                live = true;
                                break;
                            }
                        }
                        if (!live) {
                            enqueueFromMeta(ctx, clientUploadId);
                            resumed++;
                        }
                    }
                }
                JSObject ret = new JSObject();
                ret.put("resumed", resumed);
                call.resolve(ret);
            } catch (Exception e) {
                call.reject("Resume sweep failed: " + e.getMessage());
            }
        }).start();
    }

    @PluginMethod
    public void cancelUpload(final PluginCall call) {
        final String clientUploadId = call.getString("clientUploadId");
        if (clientUploadId == null || clientUploadId.isEmpty()) {
            call.reject("clientUploadId is required");
            return;
        }
        WorkManager.getInstance(getContext()).cancelUniqueWork(clientUploadId);
        JSObject ret = new JSObject();
        ret.put("cancelled", true);
        call.resolve(ret);
    }

    @PluginMethod
    public void getStatus(final PluginCall call) {
        final String clientUploadId = call.getString("clientUploadId");
        if (clientUploadId == null || clientUploadId.isEmpty()) {
            call.reject("clientUploadId is required");
            return;
        }
        new Thread(() -> {
            try {
                List<WorkInfo> infos = WorkManager.getInstance(getContext())
                        .getWorkInfosForUniqueWork(clientUploadId).get();
                JSObject ret = new JSObject();
                if (infos.isEmpty()) {
                    ret.put("state", "NONE");
                } else {
                    WorkInfo info = infos.get(0);
                    ret.put("state", info.getState().name());
                    ret.put("progress", info.getProgress().getInt("progress", 0));
                    ret.put("post_id", info.getOutputData().getString("post_id"));
                    ret.put("error_code", info.getOutputData().getString("error_code"));
                }
                call.resolve(ret);
            } catch (Exception e) {
                call.reject("Status failed: " + e.getMessage());
            }
        }).start();
    }

    private void enqueue(Context ctx, PluginCall call, File staged) throws Exception {
        String baseUrl = call.getString("baseUrl", "https://pwaninet.app");
        Data input = new Data.Builder()
                .putString("base_url", baseUrl)
                .putString("server_id", call.getString("serverId"))
                .putString("client_upload_id", call.getString("clientUploadId"))
                .putString("file_path", staged.getAbsolutePath())
                .putString("filename", call.getString("fileName", "upload"))
                .putString("mime", call.getString("mimeType", ""))
                .putLong("file_size", call.getLong("fileSize", staged.length()))
                .putInt("part_size", call.getInt("partSize", 8 * 1024 * 1024))
                .putInt("total_parts", call.getInt("totalParts", 1))
                .putString("protocol", call.getString("protocol", "s3-multipart"))
                .putString("post_content", call.getString("postContent", ""))
                .putString("post_visibility", call.getString("postVisibility", "AUTHENTICATED"))
                .putString("cookie", sessionCookie(baseUrl))
                .putString("csrf", csrfToken(baseUrl))
                .build();
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(UploadWorker.class)
                .setInputData(input)
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .addTag(UploadWorker.TAG)
                .build();
        WorkManager.getInstance(ctx).enqueueUniqueWork(
                call.getString("clientUploadId"), ExistingWorkPolicy.REPLACE, request);
        JSObject ret = new JSObject();
        ret.put("workId", request.getId().toString());
        ret.put("state", "ENQUEUED");
        call.resolve(ret);
    }

    private void enqueueFromMeta(Context ctx, String clientUploadId) throws Exception {
        File meta = new File(new File(ctx.getFilesDir(), STAGING_DIR + "/" + clientUploadId), "meta.json");
        StringBuilder sb = new StringBuilder();
        try (InputStream in = new java.io.FileInputStream(meta)) {
            byte[] buf = new byte[4096];
            int read;
            while ((read = in.read(buf)) > 0) {
                sb.append(new String(buf, 0, read, "UTF-8"));
            }
        }
        JSONObject params = new JSONObject(sb.toString());
        File staged = stagedFile(ctx, clientUploadId);
        String baseUrl = params.optString("baseUrl", "https://pwaninet.app");
        Data input = new Data.Builder()
                .putString("base_url", baseUrl)
                .putString("server_id", params.optString("serverId"))
                .putString("client_upload_id", clientUploadId)
                .putString("file_path", staged.getAbsolutePath())
                .putString("filename", params.optString("fileName", "upload"))
                .putString("mime", params.optString("mimeType", ""))
                .putLong("file_size", params.optLong("fileSize", staged.length()))
                .putInt("part_size", params.optInt("partSize", 8 * 1024 * 1024))
                .putInt("total_parts", params.optInt("totalParts", 1))
                .putString("protocol", params.optString("protocol", "s3-multipart"))
                .putString("post_content", params.optString("postContent", ""))
                .putString("post_visibility", params.optString("postVisibility", "AUTHENTICATED"))
                .putString("cookie", sessionCookie(baseUrl))
                .putString("csrf", csrfToken(baseUrl))
                .build();
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(UploadWorker.class)
                .setInputData(input)
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .addTag(UploadWorker.TAG)
                .build();
        WorkManager.getInstance(ctx).enqueueUniqueWork(
                clientUploadId, ExistingWorkPolicy.REPLACE, request);
    }

    private File stagedFile(Context ctx, String clientUploadId) {
        return new File(new File(ctx.getFilesDir(), STAGING_DIR + "/" + clientUploadId), "source");
    }

    private void stageUri(Context ctx, Uri uri, File dest) throws Exception {
        dest.getParentFile().mkdirs();
        try (InputStream in = ctx.getContentResolver().openInputStream(uri);
             OutputStream out = new FileOutputStream(dest)) {
            if (in == null) throw new IllegalArgumentException("Cannot open URI");
            byte[] buf = new byte[256 * 1024];
            int read;
            while ((read = in.read(buf)) > 0) {
                out.write(buf, 0, read);
            }
        }
    }

    private void writeMeta(Context ctx, String clientUploadId, JSObject params) throws Exception {
        File dir = new File(ctx.getFilesDir(), STAGING_DIR + "/" + clientUploadId);
        dir.mkdirs();
        try (OutputStream out = new FileOutputStream(new File(dir, "meta.json"))) {
            out.write(params.toString().getBytes("UTF-8"));
        }
    }

    private String sessionCookie(String baseUrl) {
        try {
            String cookies = CookieManager.getInstance().getCookie(baseUrl);
            return cookies != null ? cookies : "";
        } catch (Exception e) {
            return "";
        }
    }

    private String csrfToken(String baseUrl) {
        String cookies = sessionCookie(baseUrl);
        for (String part : cookies.split(";")) {
            String[] kv = part.trim().split("=", 2);
            if (kv.length == 2 && (kv[0].equals("csrftoken") || kv[0].equals("vasto_local_csrftoken"))) {
                return kv[1];
            }
        }
        return "";
    }
}

package com.vasto.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.pm.ServiceInfo;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;
import androidx.work.Data;
import androidx.work.ForegroundInfo;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.RandomAccessFile;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Phase 4: headless direct-to-R2 chunk uploader.
 *
 * WorkManager owns scheduling, backoff, and reboot persistence. The worker
 * reads bytes from app-private staging (never from the WebView), verifies
 * progress against Django, and finalizes idempotently — retries overwrite the
 * same part numbers and complete() can run twice safely.
 */
public class UploadWorker extends Worker {

    public static final String TAG = "vasto-upload";
    private static final String CHANNEL_ID = "vasto_uploads";
    private static final int NOTIFICATION_ID = 4201;
    private static final int PART_TIMEOUT_MS = 120000;

    public UploadWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Data in = getInputData();
        String baseUrl = in.getString("base_url");
        String serverId = in.getString("server_id");
        File source = new File(in.getString("file_path"));
        if (baseUrl == null || serverId == null || !source.exists()) {
            return Result.failure(errorData("STAGED_FILE_MISSING"));
        }
        String cookie = in.getString("cookie");
        String csrf = in.getString("csrf");
        String protocol = in.getString("protocol");
        int partSize = in.getInt("part_size", 8 * 1024 * 1024);
        int totalParts = in.getInt("total_parts", 1);
        long fileSize = in.getLong("file_size", source.length());

        try {
            setForegroundAsync(createForegroundInfo(0, "Starting upload…")).get(10, TimeUnit.SECONDS);

            // 1. Authoritative status: never trust local progress alone.
            JSONObject status = api(baseUrl, "GET", "/api/uploads/" + serverId + "/",
                    null, cookie, csrf);
            String state = status.optString("status", "");
            if ("completed".equals(state)) {
                return Result.success(new Data.Builder()
                        .putString("post_id", String.valueOf(status.opt("post_id")))
                        .build());
            }
            if ("cancelled".equals(state)) {
                return Result.failure(errorData("CANCELLED"));
            }
            Set<Integer> verified = new HashSet<>();
            JSONArray verifiedJson = status.optJSONArray("verified_parts");
            if (verifiedJson != null) {
                for (int i = 0; i < verifiedJson.length(); i++) {
                    verified.add(verifiedJson.optInt(i));
                }
            }

            // 2. Fresh short-lived credentials for missing parts only.
            List<Integer> missing = new ArrayList<>();
            if ("single-put".equals(protocol)) {
                if (!verified.contains(1)) missing.add(1);
            } else {
                for (int n = 1; n <= totalParts; n++) {
                    if (!verified.contains(n)) missing.add(n);
                }
            }
            if (missing.isEmpty() && !"single-put".equals(protocol)) {
                return finishComplete(baseUrl, serverId, new ArrayList<>(), in, cookie, csrf);
            }
            JSONObject partsBody = new JSONObject();
            partsBody.put("parts", new JSONArray(missing));
            JSONObject auth = api(baseUrl, "POST", "/api/uploads/" + serverId + "/authorize/",
                    partsBody.toString(), cookie, csrf);
            String uploadId = auth.optString("upload_id", "");
            JSONArray urls = auth.optJSONArray("parts");
            if (urls == null || urls.length() == 0) {
                return Result.retry();
            }

            // 3. PUT each part straight to R2.
            List<JSONObject> etags = new ArrayList<>();
            long done = verified.size() * (long) partSize;
            for (int i = 0; i < urls.length(); i++) {
                if (isStopped()) {
                    return Result.retry();
                }
                JSONObject target = urls.getJSONObject(i);
                int partNumber = target.getInt("part_number");
                String url = target.getString("url");
                long offset = (long) (partNumber - 1) * partSize;
                long length = Math.min(partSize, fileSize - offset);
                String etag = putPart(url, source, offset, length, in.getString("mime"));
                JSONObject e = new JSONObject();
                e.put("part_number", partNumber);
                e.put("etag", etag.replace("\"", ""));
                etags.add(e);
                done += length;
                int pct = fileSize > 0 ? (int) (100 * done / fileSize) : 100;
                setProgressAsync(new Data.Builder().putInt("progress", pct).build());
                try {
                    setForegroundAsync(createForegroundInfo(pct, "Uploading… " + pct + "%"))
                            .get(10, TimeUnit.SECONDS);
                } catch (Exception ignored) {
                }
            }

            // 4. Idempotent verify + finalize + publish.
            return finishComplete(baseUrl, serverId, etags, in, cookie, csrf);
        } catch (AuthException e) {
            // Session/cookie dead: user must reopen the app to refresh auth.
            return Result.failure(errorData("AUTH_EXPIRED"));
        } catch (Exception e) {
            return Result.retry();
        }
    }

    private Result finishComplete(String baseUrl, String serverId, List<JSONObject> etags,
                                  Data in, String cookie, String csrf) throws Exception {
        JSONObject body = new JSONObject();
        body.put("parts", new JSONArray(etags));
        JSONObject post = new JSONObject();
        post.put("content", in.getString("post_content") != null ? in.getString("post_content") : "");
        post.put("visibility", in.getString("post_visibility") != null ? in.getString("post_visibility") : "AUTHENTICATED");
        body.put("post", post);
        try {
            JSONObject done = api(baseUrl, "POST", "/api/uploads/" + serverId + "/complete/",
                    body.toString(), cookie, csrf);
            return Result.success(new Data.Builder()
                    .putString("post_id", String.valueOf(done.opt("post_id")))
                    .build());
        } catch (ApiException e) {
            if (e.statusCode == 422) {
                // Parts mismatch: next run re-verifies and refills gaps.
                return Result.retry();
            }
            if (e.statusCode == 409 || e.statusCode == 410) {
                return Result.failure(errorData("BAD_STATE"));
            }
            throw e;
        }
    }

    private String putPart(String url, File source, long offset, long length, String mime) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("PUT");
        conn.setDoOutput(true);
        conn.setConnectTimeout(30000);
        conn.setReadTimeout(PART_TIMEOUT_MS);
        conn.setFixedLengthStreamingMode(length);
        if (mime != null && !mime.isEmpty()) {
            conn.setRequestProperty("Content-Type", mime);
        }
        try (RandomAccessFile raf = new RandomAccessFile(source, "r");
             OutputStream out = conn.getOutputStream()) {
            raf.seek(offset);
            byte[] buf = new byte[256 * 1024];
            long remaining = length;
            while (remaining > 0) {
                if (isStopped()) {
                    conn.disconnect();
                    throw new InterruptedException("stopped");
                }
                int read = raf.read(buf, 0, (int) Math.min(buf.length, remaining));
                if (read < 0) break;
                out.write(buf, 0, read);
                remaining -= read;
            }
        }
        int code = conn.getResponseCode();
        if (code < 200 || code >= 300) {
            throw new ApiException(code, "part PUT failed");
        }
        String etag = conn.getHeaderField("ETag");
        conn.disconnect();
        return etag != null ? etag : "";
    }

    private JSONObject api(String baseUrl, String method, String path,
                           String jsonBody, String cookie, String csrf) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(30000);
        conn.setReadTimeout(60000);
        conn.setRequestProperty("Accept", "application/json");
        if (cookie != null && !cookie.isEmpty()) {
            conn.setRequestProperty("Cookie", cookie);
        }
        if (csrf != null && !csrf.isEmpty()) {
            conn.setRequestProperty("X-CSRFToken", csrf);
            conn.setRequestProperty("X-Requested-With", "XMLHttpRequest");
        }
        if (jsonBody != null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");
            try (OutputStream out = conn.getOutputStream()) {
                out.write(jsonBody.getBytes(StandardCharsets.UTF_8));
            }
        }
        int code = conn.getResponseCode();
        InputStream stream = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
        StringBuilder sb = new StringBuilder();
        if (stream != null) {
            byte[] buf = new byte[8192];
            int read;
            while ((read = stream.read(buf)) > 0) {
                sb.append(new String(buf, 0, read, StandardCharsets.UTF_8));
            }
            stream.close();
        }
        conn.disconnect();
        if (code == 401 || code == 403) {
            throw new AuthException("auth expired");
        }
        if (code < 200 || code >= 300) {
            throw new ApiException(code, sb.toString());
        }
        return new JSONObject(sb.toString());
    }

    private ForegroundInfo createForegroundInfo(int progress, String text) {
        Context ctx = getApplicationContext();
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null && nm.getNotificationChannel(CHANNEL_ID) == null) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Uploads", NotificationManager.IMPORTANCE_LOW);
            nm.createNotificationChannel(channel);
        }
        Notification notification = new NotificationCompat.Builder(ctx, CHANNEL_ID)
                .setContentTitle("Uploading to Vasto")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_sys_upload)
                .setProgress(100, progress, false)
                .setOngoing(true)
                .build();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return new ForegroundInfo(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        }
        return new ForegroundInfo(NOTIFICATION_ID, notification);
    }

    private Data errorData(String code) {
        return new Data.Builder().putString("error_code", code).build();
    }

    private static class ApiException extends Exception {
        final int statusCode;

        ApiException(int statusCode, String message) {
            super(message);
            this.statusCode = statusCode;
        }
    }

    private static class AuthException extends Exception {
        AuthException(String message) {
            super(message);
        }
    }
}

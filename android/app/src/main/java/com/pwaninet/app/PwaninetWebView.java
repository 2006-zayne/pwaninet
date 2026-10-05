package com.pwaninet.app;

import android.content.Context;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.AttributeSet;
import android.util.Base64;
import android.util.Log;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;

import androidx.core.view.inputmethod.EditorInfoCompat;
import androidx.core.view.inputmethod.InputConnectionCompat;
import androidx.core.view.inputmethod.InputContentInfoCompat;

import com.getcapacitor.CapacitorWebView;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/**
 * WebView that advertises rich-content (image) support to soft keyboards.
 *
 * By default Android's WebView does not declare any contentMimeTypes on its
 * EditorInfo, so Gboard/SwiftKey refuse to insert screenshots, clipboard images,
 * GIFs or stickers and show "PwaniNet does not allow attachments here".
 *
 * This subclass declares image MIME types and wraps the InputConnection with a
 * commitContent listener. The committed image is read natively (with the
 * temporary URI grant from the keyboard) and handed to the web layer through a
 * `pwaninet:native-image-paste` window event, where MediaPicker attaches it to
 * the focused comment composer.
 */
public class PwaninetWebView extends CapacitorWebView {
    private static final String TAG = "PwaninetWebView";
    private static final long MAX_IMAGE_BYTES = 15L * 1024L * 1024L;
    private static final String[] IMAGE_MIME_TYPES = new String[] {
        "image/png", "image/jpeg", "image/gif", "image/webp", "image/heic", "image/heif", "image/*"
    };

    public PwaninetWebView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Override
    public InputConnection onCreateInputConnection(EditorInfo outAttrs) {
        InputConnection ic = super.onCreateInputConnection(outAttrs);
        if (ic == null || outAttrs == null) return ic;

        EditorInfoCompat.setContentMimeTypes(outAttrs, IMAGE_MIME_TYPES);

        @SuppressWarnings("deprecation")
        InputConnection wrapped = InputConnectionCompat.createWrapper(ic, outAttrs, this::handleCommitContent);
        return wrapped;
    }

    private boolean handleCommitContent(InputContentInfoCompat info, int flags, android.os.Bundle opts) {
        if (info == null) return false;
        String mimeType = null;
        for (String candidate : IMAGE_MIME_TYPES) {
            if (info.getDescription().hasMimeType(candidate)) {
                mimeType = candidate;
                break;
            }
        }
        if (mimeType == null) return false;
        if (mimeType.endsWith("/*")) mimeType = info.getDescription().getMimeTypeCount() > 0
            ? info.getDescription().getMimeType(0) : "image/png";

        boolean needsPermission = Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1
            && (flags & InputConnectionCompat.INPUT_CONTENT_GRANT_READ_URI_PERMISSION) != 0;
        if (needsPermission) {
            try {
                info.requestPermission();
            } catch (Exception error) {
                Log.w(TAG, "Keyboard content permission denied", error);
                return false;
            }
        }

        final String resolvedMime = mimeType;
        final Uri contentUri = info.getContentUri();
        new Thread(() -> {
            try {
                byte[] bytes = readAll(contentUri);
                if (bytes == null || bytes.length == 0) return;
                String base64 = Base64.encodeToString(bytes, Base64.NO_WRAP);
                dispatchToWeb(resolvedMime, base64);
            } catch (Exception error) {
                Log.e(TAG, "Failed to read keyboard image", error);
            } finally {
                if (needsPermission) {
                    try { info.releasePermission(); } catch (Exception ignored) {}
                }
            }
        }, "pwaninet-keyboard-image").start();
        return true;
    }

    private byte[] readAll(Uri uri) throws Exception {
        try (InputStream input = getContext().getContentResolver().openInputStream(uri);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) return null;
            byte[] buffer = new byte[16384];
            long total = 0;
            int count;
            while ((count = input.read(buffer)) != -1) {
                total += count;
                if (total > MAX_IMAGE_BYTES) throw new IllegalStateException("Image too large");
                output.write(buffer, 0, count);
            }
            return output.toByteArray();
        }
    }

    private void dispatchToWeb(String mimeType, String base64) {
        JSONObject detail = new JSONObject();
        try {
            detail.put("mimeType", mimeType);
            detail.put("data", base64);
        } catch (Exception ignored) {}
        final String js = "window.dispatchEvent(new CustomEvent('pwaninet:native-image-paste', {detail:" + detail + "}));";
        new Handler(Looper.getMainLooper()).post(() -> evaluateJavascript(js, null));
    }
}

package com.pwaninet.app;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "Haptics")
public class HapticsPlugin extends Plugin {

    @PluginMethod
    public void impact(final PluginCall call) {
        String style = call.getString("style", "LIGHT");
        getBridge().executeOnMainThread(() -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).performNativeHapticImpact(style);
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void notification(final PluginCall call) {
        String type = call.getString("type", "SUCCESS");
        getBridge().executeOnMainThread(() -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).performNativeHapticNotification(type);
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void selectionStart(final PluginCall call) {
        getBridge().executeOnMainThread(() -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).performNativeHapticSelection();
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void selectionChanged(final PluginCall call) {
        getBridge().executeOnMainThread(() -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).performNativeHapticSelection();
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void selectionEnd(final PluginCall call) {
        call.resolve();
    }

    @PluginMethod
    public void vibrate(final PluginCall call) {
        int duration = call.getInt("duration", 300);
        getBridge().executeOnMainThread(() -> {
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).performNativeVibrate(duration);
            }
            call.resolve();
        });
    }
}

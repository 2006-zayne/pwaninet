package com.pwaninet.app;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "NavigationBar")
public class NavigationBarPlugin extends Plugin {

    @PluginMethod
    public void setStyle(final PluginCall call) {
        String style = call.getString("style");
        if (style == null) {
            style = call.getString("theme");
        }
        final String finalStyle = style != null ? style : "LIGHT";
        getBridge().executeOnMainThread(() -> {
            boolean isLight = !"DARK".equalsIgnoreCase(finalStyle);
            if (getActivity() instanceof MainActivity) {
                ((MainActivity) getActivity()).applySystemBarTheme(isLight);
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void setNavigationBarTheme(final PluginCall call) {
        setStyle(call);
    }
}

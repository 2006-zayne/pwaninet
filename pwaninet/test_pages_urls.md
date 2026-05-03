# PwaniNet Test Pages URLs

## PWA Test Pages

| Test Page | URL | Purpose |
|-----------|-----|---------|
| **Splash Screen Test** | `/test/splash/` | Basic splash screen testing and status checking |
| **Splash Debug Test** | `/test/splash-debug/` | Debugging splash screen issues in desktop PWA mode |
| **Splash Offline Test** | `/test/splash-offline/` | Testing splash screen to offline page fallback flow |
| **Splash Always Test** | `/test/splash-always/` | Testing always-on splash screen behavior |
| **Native PWA Test** | `/test/native-pwa/` | Testing native browser install prompts |
| **PWA General Test** | `/test/pwa/` | General PWA functionality testing |
| **PWA Install Test** | `/test/pwa-install/` | Testing PWA installation process |
| **Static JS Test** | `/test/static-js/` | Testing static JavaScript loading and functionality |

## Messaging Test Pages

| Test Page | URL | Purpose |
|-----------|-----|---------|
| **Messaging Architecture Test** | `/test/messaging/` | Testing messaging system functionality and architecture |
| **Messaging Debug Test** | `/test/messaging-debug/` | Debugging messaging system issues |
| **Messaging Debug Fixed** | `/test/messaging-debug-fixed/` | Fixed version of messaging debug tests |
| **Messaging Offline Test** | `/test/messaging-offline/` | Testing messaging offline functionality |

## System Pages

| Page | URL | Purpose |
|------|-----|---------|
| **Offline Page** | `/offline/` | Offline fallback page with cached content access |
| **API Documentation** | `/api/docs/` | Swagger API documentation |
| **API Schema** | `/api/schema/` | OpenAPI schema for API endpoints |
| **API ReDoc** | `/api/redoc/` | ReDoc API documentation |

## Usage Instructions

### Accessing Test Pages

1. **In Browser**: Navigate to `http://localhost:8000{URL}`
2. **In PWA**: If PwaniNet is installed as PWA, navigate to `{URL}` within the PWA
3. **From Other Pages**: Add the URL path to your current location

### Test Page Categories

**PWA Testing:**
- Use splash test pages to verify PWA launch behavior
- Test offline functionality and network fallbacks
- Verify install prompts and native PWA features

**Messaging Testing:**
- Test message creation, sending, and receiving
- Verify conversation list functionality
- Test offline message caching and sync

**System Testing:**
- Verify offline page functionality
- Test API endpoints and documentation
- Check service worker behavior

### Development Workflow

1. **Start with**: `/test/splash/` for basic PWA functionality
2. **Then test**: `/test/messaging/` for messaging features
3. **Debug issues**: Use specific debug pages as needed
4. **Verify offline**: Test `/offline/` page functionality

### Notes

- All test pages require Django development server to be running
- Some features require PWA installation for full testing
- Offline testing requires network disconnection
- API documentation requires proper API endpoint implementation

---

*Last updated: May 2, 2026*

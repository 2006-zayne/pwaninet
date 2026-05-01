/**
 * Constants - Application-wide constants
 * Shared across all modules
 */

export const EVENTS = {
  // WebSocket events
  WEBSOCKET_CONNECTED: 'websocket:connected',
  WEBSOCKET_DISCONNECTED: 'websocket:disconnected',
  WEBSOCKET_ERROR: 'websocket:error',
  WEBSOCKET_RECONNECTING: 'websocket:reconnecting',

  // Message events
  MESSAGE_SEND: 'message:send',
  MESSAGE_SENT: 'message:sent',
  MESSAGE_QUEUED: 'message:queued',
  MESSAGE_NEW: 'message:new',
  MESSAGE_READ_RECEIPT: 'message:read_receipt',
  MESSAGES_LOADED: 'messages:loaded',
  MESSAGES_UPDATED: 'messages:updated',

  // Typing events
  TYPING_START: 'typing:start',
  TYPING_STOP: 'typing:stop',
  TYPING_INDICATOR: 'typing:indicator',

  // Store events
  STATE_CHANGED: 'state:changed',
  MESSAGES_CHANGED: 'state:messages_changed',
  CONNECTION_CHANGED: 'state:connection_changed',

  // UI events
  UI_SHOW_TYPING: 'ui:show_typing',
  UI_HIDE_TYPING: 'ui:hide_typing',
  UI_RENDER: 'ui:render',

  // Feature events
  EMOJI_INSERT: 'emoji:insert',
  EMOJI_PICKER_TOGGLE: 'emoji:picker_toggle',
  CAMERA_OPEN: 'camera:open',
  CAMERA_CLOSE: 'camera:close',
  CAMERA_CAPTURE: 'camera:capture',
  CAMERA_ERROR: 'camera:error',
  VOICE_START: 'voice:start',
  VOICE_STOP: 'voice:stop',
  VOICE_SEND: 'voice:send',
  VOICE_ERROR: 'voice:error',
  VOICE_TIMER_UPDATE: 'voice:timer_update',
  VOICE_DISCARD: 'voice:discard',
  ATTACHMENT_SELECTED: 'attachment:selected',
  ATTACHMENT_UPLOAD: 'attachment:upload',
  ATTACHMENT_UPLOAD_START: 'attachment:upload_start',
  ATTACHMENT_UPLOAD_SUCCESS: 'attachment:upload_success',
  ATTACHMENT_ERROR: 'attachment:error',
  ATTACHMENT_MODAL_TOGGLE: 'attachment:modal_toggle',

  // Theme events
  THEME_TOGGLE: 'theme:toggle',
  THEME_APPLY: 'theme:apply',
  THEME_RESET: 'theme:reset',
  THEME_SELECTOR_SHOW: 'theme:selector_show',
  THEME_LOADED: 'theme:loaded',
  THEME_SAVED: 'theme:saved',
  THEME_ERROR: 'theme:error',
  THEME_TAB_SWITCH: 'theme:tab_switch',
  THEME_SAVE: 'theme:save',

  // Search events
  SEARCH_TOGGLE: 'search:toggle',
  SEARCH_QUERY: 'search:query',

  // Header events
  HEADER_UPDATE_STATUS: 'header:update_status',
};

export const CONNECTION_STATE = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error',
};

export const MESSAGE_STATUS = {
  SENT: 'sent',
  DELIVERED: 'delivered',
  READ: 'read',
  FAILED: 'failed',
};

export const UI_STATE = {
  IDLE: 'idle',
  TYPING: 'typing',
  SENDING: 'sending',
  LOADING: 'loading',
};

export const RECONNECT_CONFIG = {
  MAX_ATTEMPTS: 5,
  BASE_DELAY: 3000,
  MAX_DELAY: 30000,
  BACKOFF_MULTIPLIER: 2,
};

export const MESSAGE_DEDUP_WINDOW = 5000; // 5 seconds

export const DEFAULT_THEME = {
  light: {
    '--chat-bg': '#f8fafc',
    '--chat-bg-type': 'solid',
    '--chat-overlay-color': '#ffffff',
    '--chat-overlay-opacity': '0.3',
  },
  dark: {
    '--chat-bg': '#18191f',
    '--chat-bg-type': 'solid',
    '--chat-overlay-color': '#000000',
    '--chat-overlay-opacity': '0.3',
  },
};

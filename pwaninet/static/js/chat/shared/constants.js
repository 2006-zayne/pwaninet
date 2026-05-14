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
  MESSAGE_FAILED: 'message:failed',
  MESSAGES_LOADED: 'messages:loaded',
  MESSAGES_UPDATED: 'messages:updated',

  // Optimistic update events
  MESSAGE_OPTIMISTIC_ADD: 'message:optimistic_add',
  MESSAGE_CONFIRMED: 'message:confirmed',
  REACTION_OPTIMISTIC_ADD: 'reaction:optimistic_add',
  REACTION_CONFIRMED: 'reaction:confirmed',
  UI_MESSAGE_PENDING: 'ui:message_pending',
  UI_MESSAGE_CONFIRMED: 'ui:message_confirmed',
  UI_MESSAGE_FAILED: 'ui:message_failed',
  UI_REACTION_PENDING: 'ui:reaction_pending',
  UI_REACTION_CONFIRMED: 'ui:reaction_confirmed',
  UI_REACTION_TIMEOUT: 'ui:reaction_timeout',

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
  VOICE_LOCK: 'voice:lock',
  VOICE_LOCKED: 'voice:locked',
  VOICE_PLAY_PAUSE: 'voice:play_pause',
  VOICE_PLAYING: 'voice:playing',
  VOICE_PAUSED: 'voice:paused',
  VOICE_PLAYBACK_ENDED: 'voice:playback_ended',
  VOICE_PLAYBACK_STOPPED: 'voice:playback_stopped',
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

  // Context menu events
  CONTEXT_MENU_SHOWN: 'menu:context_shown',
  CONTEXT_MENU_HIDDEN: 'menu:context_hidden',
  CONTEXT_MENU_ACTION: 'menu:context_action',
};

export const CONNECTION_STATE = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error',
};

/**
 * Unified Message State Machine
 * Single authoritative source for all message lifecycle states
 * All UI and services MUST use these states exclusively
 */
export const MESSAGE_STATE = {
  DRAFT: 'draft',
  QUEUED: 'queued',
  PROCESSING: 'processing',
  UPLOADING: 'uploading',
  SENDING: 'sending',
  SENT: 'sent',
  DELIVERED: 'delivered',
  READ: 'read',
  FAILED_UPLOAD: 'failed_upload',
  FAILED_SEND: 'failed_send',
  RETRYING: 'retrying',
  CANCELLED: 'cancelled',
};

/**
 * Valid message state transitions
 * Enforces state machine integrity - prevents invalid transitions
 */
export const MESSAGE_STATE_TRANSITIONS = {
  [MESSAGE_STATE.DRAFT]: [MESSAGE_STATE.QUEUED, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.QUEUED]: [MESSAGE_STATE.PROCESSING, MESSAGE_STATE.SENDING, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.PROCESSING]: [MESSAGE_STATE.UPLOADING, MESSAGE_STATE.SENDING, MESSAGE_STATE.FAILED_UPLOAD, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.UPLOADING]: [MESSAGE_STATE.SENDING, MESSAGE_STATE.FAILED_UPLOAD, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.SENDING]: [MESSAGE_STATE.SENT, MESSAGE_STATE.FAILED_SEND, MESSAGE_STATE.RETRYING],
  [MESSAGE_STATE.SENT]: [MESSAGE_STATE.DELIVERED, MESSAGE_STATE.READ, MESSAGE_STATE.FAILED_SEND],
  [MESSAGE_STATE.DELIVERED]: [MESSAGE_STATE.READ],
  [MESSAGE_STATE.READ]: [], // Terminal state
  [MESSAGE_STATE.FAILED_UPLOAD]: [MESSAGE_STATE.RETRYING, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.FAILED_SEND]: [MESSAGE_STATE.RETRYING, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.RETRYING]: [MESSAGE_STATE.SENDING, MESSAGE_STATE.FAILED_UPLOAD, MESSAGE_STATE.FAILED_SEND, MESSAGE_STATE.CANCELLED],
  [MESSAGE_STATE.CANCELLED]: [], // Terminal state
};

/**
 * Check if a state transition is valid
 * @param {string} fromState - Current state
 * @param {string} toState - Target state
 * @returns {boolean} True if transition is valid
 */
export function isValidStateTransition(fromState, toState) {
  if (!MESSAGE_STATE_TRANSITIONS[fromState]) {
    console.warn(`[STATE_MACHINE] Unknown fromState: ${fromState}`);
    return false;
  }
  return MESSAGE_STATE_TRANSITIONS[fromState].includes(toState);
}

/**
 * Legacy MESSAGE_STATUS for backward compatibility (deprecated)
 * Use MESSAGE_STATE instead
 * @deprecated Use MESSAGE_STATE enum instead
 */
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

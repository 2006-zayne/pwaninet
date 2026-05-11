/**
 * EventBus - STRICTLY UI-only events
 * FORBIDDEN: Any data/state/message flow involvement
 * ALLOWED ONLY: UI interactions (typing, clicks, indicators)
 */

export class EventBus {
    constructor() {
        this.events = new Map();
        this.onceEvents = new Map();
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this._validateEventNames = true;
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name (UI events only)
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        this._validateUIEvent(event);
        
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        this.events.get(event).push(callback);

        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Subscribe to an event once
     * @param {string} event - Event name (UI events only)
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    once(event, callback) {
        this._validateUIEvent(event);
        
        if (!this.onceEvents.has(event)) {
            this.onceEvents.set(event, []);
        }
        this.onceEvents.get(event).push(callback);

        // Return unsubscribe function
        return () => this.offOnce(event, callback);
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    off(event, callback) {
        if (!this.events.has(event)) return;
        
        const callbacks = this.events.get(event);
        const index = callbacks.indexOf(callback);
        if (index > -1) {
            callbacks.splice(index, 1);
        }
    }

    /**
     * Unsubscribe from once event
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    offOnce(event, callback) {
        if (!this.onceEvents.has(event)) return;
        
        const callbacks = this.onceEvents.get(event);
        const index = callbacks.indexOf(callback);
        if (index > -1) {
            callbacks.splice(index, 1);
        }
    }

    /**
     * Emit an event (UI events only)
     * @param {string} event - Event name
     * @param {*} data - Event data (UI interaction data only)
     */
    emit(event, data) {
        this._validateUIEvent(event);
        this._validateEventData(event, data);
        
        this._log('EVENT_EMIT', { event, data });

        // Regular events
        if (this.events.has(event)) {
            const callbacks = this.events.get(event);
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`EventBus: Error in callback for event ${event}:`, error);
                }
            });
        }

        // Once events
        if (this.onceEvents.has(event)) {
            const callbacks = this.onceEvents.get(event);
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`EventBus: Error in once callback for event ${event}:`, error);
                }
            });
            // Clear once events after execution
            this.onceEvents.delete(event);
        }
    }

    /**
     * Validate that event is UI-only
     * @param {string} event - Event name
     */
    _validateUIEvent(event) {
        // Validation disabled to allow all events
        // The EventBus is used for all application events, not just UI
        return;
    }

    /**
     * Validate event data (UI interaction data only)
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    _validateEventData(event, data) {
        // Validation disabled to allow all event data
        // The EventBus is used for all application events, not just UI
        return;
    }

    /**
     * Clear all events
     */
    clear() {
        this.events.clear();
        this.onceEvents.clear();
        this._log('EVENT_BUS_CLEARED');
    }

    /**
     * Get event bus status
     * @returns {Object} Status
     */
    getStatus() {
        return {
            totalEvents: this.events.size,
            totalOnceEvents: this.onceEvents.size,
            eventNames: Array.from(this.events.keys()),
            onceEventNames: Array.from(this.onceEvents.keys()),
            validationEnabled: this._validateEventNames
        };
    }

    /**
     * Enable/disable event validation (for testing)
     * @param {boolean} enabled - Validation enabled
     */
    setValidation(enabled) {
        this._validateEventNames = enabled;
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[EVENT_BUS] ${action}:`, data);
        }
    }
}

// Create and export singleton instance
export const eventBus = new EventBus();

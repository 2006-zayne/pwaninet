/**
 * Compatibility facade for static/js/upload/downloads_manager.js
 * Delegates to the unified Download Manager in static/js/downloads/
 */

import { downloadManager } from '../downloads/download_manager.js';
import { downloadStorage } from '../downloads/download_storage.js';
import { downloadQueue } from '../downloads/download_queue.js';

export { downloadManager, downloadStorage, downloadQueue };
export const downloadsManager = downloadManager;
export default downloadManager;

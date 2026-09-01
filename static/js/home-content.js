// Prevent script from running multiple times during HTMX swaps
if (!window.homeContentScriptLoaded) {
    window.homeContentScriptLoaded = true;

// Scroll-aware auto-play/pause for videos and audio
(function() {
    let currentPlayingMedia = null;
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.5 // Play when 50% of the element is visible
    };

    const mediaObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const mediaElement = entry.target;
            const mediaType = mediaElement.closest('[data-media-type]')?.dataset.mediaType;
            
            if (entry.isIntersecting) {
                // Element is in view - play it
                if (mediaType === 'video' && mediaElement.tagName === 'VIDEO') {
                    playMedia(mediaElement);
                } else if (mediaType === 'audio' && mediaElement.tagName === 'AUDIO') {
                    playMedia(mediaElement);
                }
            } else {
                // Element is out of view - pause it
                if (mediaElement.tagName === 'VIDEO' || mediaElement.tagName === 'AUDIO') {
                    pauseMedia(mediaElement);
                }
            }
        });
    }, observerOptions);

    function playMedia(media) {
        // Pause currently playing media if different
        if (currentPlayingMedia && currentPlayingMedia !== media) {
            pauseMedia(currentPlayingMedia);
        }
        
        // Play the new media
        media.play().catch(err => {
            console.log('Autoplay prevented:', err);
        });
        currentPlayingMedia = media;
    }

    function pauseMedia(media) {
        media.pause();
        if (currentPlayingMedia === media) {
            currentPlayingMedia = null;
        }
    }

    // Observe all videos and audio elements
    function observeMedia() {
        const videos = document.querySelectorAll('video[id^="video-"]');
        const audios = document.querySelectorAll('audio[id^="audio-"]');
        
        videos.forEach(video => {
            if (!video.dataset.observed) {
                mediaObserver.observe(video);
                video.dataset.observed = 'true';
            }
        });
        
        audios.forEach(audio => {
            if (!audio.dataset.observed) {
                mediaObserver.observe(audio);
                audio.dataset.observed = 'true';
            }
        });
    }

    // Initial observation
    observeMedia();

    // Re-observe when new posts are loaded (HTMX)
    document.body.addEventListener('htmx:afterSwap', function(event) {
        if (event.target.id === 'feed-sector' || event.target.closest('#feed-sector')) {
            observeMedia();
        }
    });

    // Pause all media when user leaves the page
    document.addEventListener('visibilitychange', function() {
        if (document.hidden && currentPlayingMedia) {
            pauseMedia(currentPlayingMedia);
        }
    });
})();
}

// Prevent script from running multiple times during HTMX swaps
if (!window.homeContentScriptLoaded) {
    window.homeContentScriptLoaded = true;

    // Scroll-aware auto-pause for standalone audio elements
    // All video playback is unified and handled exclusively by PwaniNetVideoManager (static/js/video-manager.js)
    (function() {
        let currentPlayingAudio = null;
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.5
        };

        const audioObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const mediaElement = entry.target;
                if (!entry.isIntersecting && mediaElement.tagName === 'AUDIO') {
                    if (currentPlayingAudio === mediaElement) {
                        mediaElement.pause();
                        currentPlayingAudio = null;
                    }
                }
            });
        }, observerOptions);

        function observeAudio() {
            const audios = document.querySelectorAll('audio[id^="audio-"]');
            audios.forEach(audio => {
                if (!audio.dataset.observedAudio) {
                    audioObserver.observe(audio);
                    audio.dataset.observedAudio = 'true';
                }
            });
        }

        observeAudio();

        document.body.addEventListener('htmx:afterSwap', function(event) {
            if (event.target && (event.target.id === 'feed-sector' || event.target.closest('#feed-sector') || (event.target.querySelector && event.target.querySelector('audio')))) {
                observeAudio();
            }
        });

        document.addEventListener('visibilitychange', function() {
            if (document.hidden && currentPlayingAudio) {
                currentPlayingAudio.pause();
                currentPlayingAudio = null;
            }
        });
    })();
}

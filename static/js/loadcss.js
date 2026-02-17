/**
 * Helper script to load CSS stylesheets without inline event handlers.
 * Replaces onload="this.onload=null;this.rel='stylesheet'" pattern.
 */
(function() {
    'use strict';

    // Find all preload links and load them properly
    document.addEventListener('DOMContentLoaded', function() {
        const preloadLinks = document.querySelectorAll('link[rel="preload"][as="style"], link.preload-style');

        preloadLinks.forEach(function(link) {
            // Set rel to stylesheet to trigger loading
            link.setAttribute('rel', 'stylesheet');
        });
    });
})();

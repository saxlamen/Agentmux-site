(function () {
    'use strict';

    var keyMeta = document.querySelector('meta[name="posthog-key"]');
    var key = keyMeta ? (keyMeta.getAttribute('content') || '').trim() : '';
    if (!key) return;

    var hostMeta = document.querySelector('meta[name="posthog-host"]');
    var host = (hostMeta ? (hostMeta.getAttribute('content') || '').trim() : '') || 'https://us.i.posthog.com';
    host = host.replace(/\/+$/, '');

    var distinctId = '';
    try {
        distinctId = sessionStorage.getItem('amx_sid') || '';
        if (!distinctId) {
            distinctId = 'anon_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            sessionStorage.setItem('amx_sid', distinctId);
        }
    } catch (e) {
        distinctId = 'anon_' + Math.random().toString(36).slice(2);
    }

    function detectAiReferrer(ref) {
        if (!ref) return '';
        var lower = ref.toLowerCase();
        var sources = ['chatgpt.com', 'perplexity.ai', 'perplexity.org', 'copilot.microsoft.com', 'claude.ai', 'gemini.google.com'];
        for (var i = 0; i < sources.length; i++) {
            if (lower.indexOf(sources[i]) !== -1) return sources[i];
        }
        return '';
    }

    function capture(event, props) {
        var payload = JSON.stringify({
            api_key: key,
            event: event,
            distinct_id: distinctId,
            properties: Object.assign({
                $current_url: window.location.href,
                $pathname: window.location.pathname,
                $referrer: document.referrer || '',
                lang: document.documentElement.lang || '',
                ai_referrer: detectAiReferrer(document.referrer || '')
            }, props || {})
        });
        var url = host + '/capture/';
        if (navigator.sendBeacon) {
            try {
                var blob = new Blob([payload], { type: 'application/json' });
                if (navigator.sendBeacon(url, blob)) return;
            } catch (e) { /* fall through to fetch */ }
        }
        if (window.fetch) {
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true
            }).catch(function () {});
        }
    }

    capture('$pageview');

    // Track scroll-depth milestones to see where readers stop scrolling.
    var reached = {};
    var milestones = [25, 50, 75, 100];
    function onScroll() {
        var doc = document.documentElement;
        var max = doc.scrollHeight - window.innerHeight;
        if (max <= 0) return;
        var pct = Math.min(100, Math.round((window.scrollY / max) * 100));
        for (var i = 0; i < milestones.length; i++) {
            var m = milestones[i];
            if (pct >= m && !reached[m]) {
                reached[m] = true;
                capture('guide_scroll_depth', { depth_pct: m });
            }
        }
    }
    window.addEventListener('scroll', onScroll, { passive: true });

    // Track outbound App Store / Google Play CTA clicks and their placement.
    document.addEventListener('click', function (ev) {
        var link = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
        if (!link) return;
        var href = link.getAttribute('href') || '';
        var store = '';
        if (href.indexOf('apps.apple.com') !== -1) store = 'app_store';
        else if (href.indexOf('play.google.com') !== -1) store = 'play_store';
        if (!store) return;
        var container = link.closest('[data-cta-placement]');
        var placement = container ? container.getAttribute('data-cta-placement') : 'unknown';
        capture('cta_click', { store: store, placement: placement, href: href });
    });
})();

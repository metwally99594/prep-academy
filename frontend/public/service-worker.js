/* PrepAcademy Service Worker — stale-while-revalidate for static, network-first for API */
const STATIC_CACHE = 'pa-static-v4';
const DYNAMIC_CACHE = 'pa-dynamic-v4';

const PRECACHE = ['/', '/offline.html', '/logo-elite.png', '/favicon.ico'];

// Paths that must bypass the SW entirely so Authorization headers reach the server intact.
const SW_BYPASS = ['/api/export/'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(c => c.addAll(PRECACHE).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  const current = [STATIC_CACHE, DYNAMIC_CACHE];
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => !current.includes(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.protocol === 'chrome-extension:') return;

  // Bypass SW for download/streaming endpoints and auth endpoints
  if (SW_BYPASS.some(p => url.pathname.startsWith(p))) return;
  if (url.pathname.startsWith('/api/auth/')) return;

  // Skip SW for authenticated requests to preserve Authorization headers
  if (request.headers.get('Authorization')) return;

  // Network-first for API calls (matched by path prefix, works with any backend URL)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    return;
  }

  // Stale-while-revalidate for everything else
  event.respondWith(
    caches.open(DYNAMIC_CACHE).then(async cache => {
      const cached = await cache.match(request);
      const fetchPromise = fetch(request)
        .then(response => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        })
        .catch(() => null);
      return cached || fetchPromise || caches.match('/offline.html');
    })
  );
});

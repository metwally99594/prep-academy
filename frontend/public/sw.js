// Self-destruct service worker. Any browser that still has a cached SW will
// fetch this file, run it, and immediately unregister itself + wipe all caches.
// This guarantees users get fresh JS/CSS on every visit.

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      const regs = await self.registration ? [self.registration] : [];
      for (const r of regs) { try { await r.unregister(); } catch (e) {} }
    } catch (e) {}
  })());
  self.clients.claim();
});

// No fetch handler: the browser falls back to network for all requests.

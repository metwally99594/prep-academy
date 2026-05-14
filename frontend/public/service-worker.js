// Self-destruct SW — replaces old stale-while-revalidate SW.
// Any browser that still has the old SW cached will detect this file changed,
// reinstall it, wipe all caches, and unregister. Subsequent loads are SW-free
// and fresh content is served directly.

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
});

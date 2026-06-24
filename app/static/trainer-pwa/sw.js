const CACHE_NAME = 'fitintel-trainer-v1';
const urlsToCache = [
  '/static/trainer-pwa/index.html',
  '/static/trainer-pwa/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      if (response) return response;
      return fetch(event.request);
    })
  );
});

self.addEventListener('push', event => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/trainer-pwa/icon-192.png',
      badge: '/static/trainer-pwa/icon-192.png'
    })
  );
});

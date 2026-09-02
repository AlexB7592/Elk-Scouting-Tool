// GMU 44 Field Mode - service worker
// Strategy: cache-first for tile images and vendor JS (they never change once
// generated), network-first-falling-back-to-cache for index.html itself (so
// you get updates when online, but it still works with zero signal).

var CACHE_NAME = 'gmu44-field-v1';

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME; })
             .map(function(n) { return caches.delete(n); })
      );
    })
  );
  self.clients.claim();
});

function isTileOrAsset(url) {
  return /\.(jpg|jpeg|png|dzi)(\?.*)?$/i.test(url) || url.indexOf('/vendor/') !== -1;
}

self.addEventListener('fetch', function(event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  var url = req.url;

  // don't try to cache Firebase / external API calls - those need to be live
  if (url.indexOf('firebaseio.com') !== -1 || url.indexOf('googleapis.com') !== -1 ||
      url.indexOf('open-meteo.com') !== -1 || url.indexOf('gstatic.com') !== -1) {
    return;
  }

  if (isTileOrAsset(url)) {
    // cache-first: tiles never change once generated, so serve from cache
    // instantly if we have it, and only hit the network (then cache the
    // result) the first time a tile is actually needed.
    event.respondWith(
      caches.match(req).then(function(cached) {
        if (cached) return cached;
        return fetch(req).then(function(resp) {
          if (resp && resp.status === 200) {
            var copy = resp.clone();
            caches.open(CACHE_NAME).then(function(cache) { cache.put(req, copy); });
          }
          return resp;
        }).catch(function() {
          return cached; // undefined -> browser shows its normal offline error for this tile
        });
      })
    );
    return;
  }

  // HTML shell and everything else: try the network first so you get
  // updates, fall back to whatever's cached if you're offline.
  event.respondWith(
    fetch(req).then(function(resp) {
      if (resp && resp.status === 200) {
        var copy = resp.clone();
        caches.open(CACHE_NAME).then(function(cache) { cache.put(req, copy); });
      }
      return resp;
    }).catch(function() {
      return caches.match(req);
    })
  );
});

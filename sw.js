// Service worker for the GMU 44 app.
//
// Two caching strategies, because the assets behave very differently:
//   CORE  -- the app shell, routing grids and access data. Small, changes often.
//            Network first, so a new build is picked up as soon as there is
//            signal, falling back to cache when there is not.
//   BULK  -- the PMTiles archives. Large, effectively immutable. Cache first,
//            and only ever fetched when the user explicitly asks to download
//            the unit for offline use.
//
// Bump CACHE_VERSION whenever the shell changes, or phones will keep serving
// the old app from cache -- the same stale-copy problem as the browser cache,
// but stickier.
var CACHE_VERSION = 'gmu44-v1';
var CORE_CACHE = CACHE_VERSION + '-core';
var BULK_CACHE = CACHE_VERSION + '-bulk';

var CORE = [
  'app.html',
  'grids/cost_grid.png',
  'grids/elev_grid.png',
  'grids/stealth_risk_grid.png',
  'data/access_points.json',
  'data/trails_topology.json',
  'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js',
  'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css',
  'https://unpkg.com/pmtiles@4.3.0/dist/pmtiles.js'
];

self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(CORE_CACHE).then(function(c){
      // addAll fails the whole install if any single request fails, which would
      // leave no cache at all; add individually and tolerate misses.
      return Promise.all(CORE.map(function(u){
        return c.add(u).catch(function(){ /* keep going */ });
      }));
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){
        return k.indexOf(CACHE_VERSION) !== 0;
      }).map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e){
  var url = e.request.url;

  // PMTiles archives: served from cache when present. These are fetched with
  // range requests, so only respond from cache on a full-file match; otherwise
  // let the network handle the range.
  if (url.indexOf('.pmtiles') !== -1) {
    e.respondWith(
      caches.open(BULK_CACHE).then(function(c){
        return c.match(e.request, {ignoreVary:true, ignoreSearch:true}).then(function(hit){
          return hit || fetch(e.request);
        });
      }).catch(function(){ return fetch(e.request); })
    );
    return;
  }

  // Everything else: network first, cache as a fallback.
  e.respondWith(
    fetch(e.request).then(function(res){
      if (res && res.ok && e.request.method === 'GET') {
        var copy = res.clone();
        caches.open(CORE_CACHE).then(function(c){ c.put(e.request, copy); });
      }
      return res;
    }).catch(function(){
      return caches.match(e.request).then(function(hit){
        return hit || Response.error();
      });
    })
  );
});

// The app asks for the archives to be pulled down in full.
self.addEventListener('message', function(e){
  if (!e.data || e.data.type !== 'CACHE_ARCHIVES') return;
  var urls = e.data.urls || [];
  e.waitUntil(
    caches.open(BULK_CACHE).then(function(c){
      var done = 0;
      return Promise.all(urls.map(function(u){
        return fetch(u).then(function(r){
          if (!r.ok) throw new Error(u + ' -> ' + r.status);
          return c.put(u, r);
        }).then(function(){
          done++;
          self.clients.matchAll().then(function(cs){
            cs.forEach(function(cl){
              cl.postMessage({type:'CACHE_PROGRESS', done:done, total:urls.length});
            });
          });
        });
      })).then(function(){
        self.clients.matchAll().then(function(cs){
          cs.forEach(function(cl){ cl.postMessage({type:'CACHE_DONE'}); });
        });
      }).catch(function(err){
        self.clients.matchAll().then(function(cs){
          cs.forEach(function(cl){ cl.postMessage({type:'CACHE_ERROR', message:err.message}); });
        });
      });
    })
  );
});

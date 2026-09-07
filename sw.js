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
var CACHE_VERSION = 'gmu44-v5';
var CORE_CACHE = CACHE_VERSION + '-core';
var BULK_CACHE = CACHE_VERSION + '-bulk';

var CORE = [
  'app.html',
  'grids/cost_grid.png',
  'grids/elev_grid.png',
  'grids/stealth_risk_grid.png',
  'data/access_points.json',
  'data/trails_topology.json',
  'data/vectors/roads.geojson',
  'data/vectors/trails.geojson',
  'data/vectors/streams.geojson',
  'data/vectors/water.geojson',
  'data/vectors/ntd_4wd.geojson',
  'data/vectors/ntd_local.geojson',
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


function parseRange(header) {
  // Only the simple "bytes=start-end" form the PMTiles library emits.
  var m = /^bytes=(\d*)-(\d*)$/.exec((header || '').trim());
  if (!m) return null;
  var start = m[1] === '' ? null : parseInt(m[1], 10);
  var end   = m[2] === '' ? null : parseInt(m[2], 10);
  if (start === null && end === null) return null;
  return { start: start, end: end };
}

function serveArchive(request) {
  var range = parseRange(request.headers.get('range'));
  // Strip the Range header for the cache lookup: one full copy is stored per URL.
  var keyReq = new Request(request.url, { method: 'GET' });
  return caches.open(BULK_CACHE).then(function(c){
    return c.match(keyReq).then(function(hit){
      if (!hit) return fetch(request);                 // not downloaded: go to network
      if (!range) return hit;                          // whole file wanted
      return hit.arrayBuffer().then(function(buf){
        var total = buf.byteLength;
        var start, end;
        if (range.start === null) {                    // "bytes=-N" -> last N bytes
          start = Math.max(0, total - range.end);
          end = total - 1;
        } else {
          start = range.start;
          end = (range.end === null) ? total - 1 : Math.min(range.end, total - 1);
        }
        if (start >= total || start > end) {
          return new Response(null, { status: 416,
            headers: { 'Content-Range': 'bytes */' + total } });
        }
        var slice = buf.slice(start, end + 1);
        return new Response(slice, {
          status: 206,
          statusText: 'Partial Content',
          headers: {
            'Content-Type': hit.headers.get('Content-Type') || 'application/octet-stream',
            'Content-Length': String(slice.byteLength),
            'Content-Range': 'bytes ' + start + '-' + end + '/' + total,
            'Accept-Ranges': 'bytes'
          }
        });
      });
    });
  }).catch(function(){ return fetch(request); });
}

self.addEventListener('fetch', function(e){
  var url = e.request.url;

  // PMTiles archives. These are read with HTTP range requests -- the library asks
  // for a few hundred bytes at a known offset, never the whole file. The cache
  // holds one complete copy, so a range request has to be answered by slicing
  // that copy and returning a proper 206 with a Content-Range header. Handing
  // back the entire 52 MB body for a 200-byte request would leave the library
  // reading an archive header where it expected tile data, and the tiles would
  // decode into garbage.
  if (url.indexOf('.pmtiles') !== -1) {
    e.respondWith(serveArchive(e.request));
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
        // Explicitly request the whole file, and store it under a Range-free key
        // so serveArchive can slice it for every subsequent range request.
        return fetch(u, { cache: 'reload' }).then(function(r){
          if (!r.ok) throw new Error(u + ' -> ' + r.status);
          return c.put(new Request(u, { method:'GET' }), r);
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

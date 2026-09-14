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
var CACHE_VERSION = 'gmu44-v68';
var CORE_CACHE = CACHE_VERSION + '-core';
// The downloaded map archives must SURVIVE shell updates. BULK used to be named
// CACHE_VERSION + '-bulk', and activate deletes every cache whose name does not
// start with the current CACHE_VERSION -- so every build bump silently deleted
// the ~140 MB offline download. Download the unit, open the app once with signal
// after a new build, and you reach the trailhead with no map. Its name is now
// independent of the shell. Bump BULK_VERSION ONLY when the .pmtiles archives
// themselves are regenerated, or phones will keep serving the old tiles.
var BULK_VERSION = 1;
var BULK_CACHE = 'gmu44-bulk-' + BULK_VERSION;

var CORE = [
  'app.html',
  'grids/cost_grid.png',
  'grids/terrain_mult_grid.png',
  'grids/elev_grid.png',
  'grids/stealth_risk_grid.png',
  // Every grid the app actually loads. The habitat and Auto-Scout grids were
  // missing from this list, so those layers went blank offline -- in a unit with
  // no service, which is the only place it matters.
  'grids/canopy_grid.png',
  'grids/forage_grid.png',
  'grids/roaddist_grid.png',
  'grids/ownership_grid.png',
  'grids/autoscout_grid.png',
  'data/access_points.json',
  'data/access_road_names.json',
  'data/trails_topology.json',
  'data/vectors/roads_all.geojson',
  'data/vectors/trails.geojson',
  'data/vectors/streams.geojson',
  'data/vectors/water.geojson',
  'data/vectors/places.geojson',
  'data/vectors/scout_areas.geojson',
  'data/vectors/rec_sites.geojson',
  'data/vectors/trail_links.geojson',
  'data/vectors/isolated_water.geojson',
  'data/trail_stats.json',
  'fonts/Noto Sans Regular/0-255.pbf',
  'fonts/Noto Sans Regular/8192-8447.pbf',
  'fonts/Open Sans Semibold/0-255.pbf',
  'fonts/Open Sans Semibold/8192-8447.pbf',
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
        // old shells go; the current map download stays. Bulk caches from older
        // builds (named after their CACHE_VERSION) are not BULK_CACHE and go too.
        return k.indexOf(CACHE_VERSION) !== 0 && k !== BULK_CACHE;
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

// Downloaded archives are stored in 4 MB pieces plus a small manifest, not as one
// whole file (C79). The whole-file copy had to be read into memory IN FULL -- 85 MB
// for the terrain -- to answer every range request, and the map asks for dozens at
// once whenever it moves. Measured in the same storage (desktop Chrome): 43 ms per
// request and 1.8 s for a burst of 40, against 1 ms and 0.05 s from pieces, bytes
// identical. The phone's memory cost could not be measured here, and a service
// worker that runs out of memory is killed -- blank map, no signal to recover with.
// Pieces keep every read to 4 MB whatever the engine does.
// Keys use a query string: the Cache API ignores #fragments, so '#chunk=N' keys
// all collapse into one entry (found testing this).
var CHUNK = 4 * 1024 * 1024;
function baseUrl(u) { return String(u).split('#')[0].split('?')[0]; }
function chunkKey(u, n) { return new Request(baseUrl(u) + '?gmu44chunk=' + n); }
function manifestKey(u) { return new Request(baseUrl(u) + '?gmu44manifest'); }

function resolveRange(range, total) {
  if (!range) return { start: 0, end: total - 1, whole: true };
  if (range.start === null) return { start: Math.max(0, total - range.end), end: total - 1 };
  return { start: range.start, end: range.end === null ? total - 1 : Math.min(range.end, total - 1) };
}
function rangeResponse(r, total, body, type) {
  if (r.start >= total || r.start > r.end) {
    return new Response(null, { status: 416, headers: { 'Content-Range': 'bytes */' + total } });
  }
  type = type || 'application/octet-stream';
  if (r.whole) {
    return new Response(body, { status: 200, headers: {
      'Content-Type': type, 'Content-Length': String(total), 'Accept-Ranges': 'bytes' } });
  }
  return new Response(body, {
    status: 206,
    statusText: 'Partial Content',
    headers: {
      'Content-Type': type,
      'Content-Length': String(r.end - r.start + 1),
      'Content-Range': 'bytes ' + r.start + '-' + r.end + '/' + total,
      'Accept-Ranges': 'bytes'
    }
  });
}
function fromPieces(c, url, man, range) {
  var r = resolveRange(range, man.total);
  if (r.start >= man.total || r.start > r.end) return rangeResponse(r, man.total, null, man.type);
  var first = Math.floor(r.start / man.chunk), last = Math.floor(r.end / man.chunk), jobs = [];
  for (var k = first; k <= last; k++) {
    jobs.push(c.match(chunkKey(url, k)).then(function (res) {
      if (!res) throw new Error('missing piece');
      return res.blob();
    }));
  }
  return Promise.all(jobs).then(function (blobs) {
    var parts = blobs.map(function (bl, i) {
      var base = (first + i) * man.chunk;
      return bl.slice(Math.max(0, r.start - base), Math.min(bl.size, r.end + 1 - base));
    });
    return rangeResponse(r, man.total, new Blob(parts), man.type);
  });
}

function serveArchive(request) {
  var range = parseRange(request.headers.get('range'));
  return caches.open(BULK_CACHE).then(function (c) {
    return c.match(manifestKey(request.url)).then(function (m) {
      if (m) return m.json().then(function (man) { return fromPieces(c, request.url, man, range); });
      // A whole-file copy from a C78 download. Cut it as a Blob rather than reading
      // it all; whether that avoids the full read depends on the engine.
      return c.match(new Request(request.url, { method: 'GET' })).then(function (hit) {
        if (!hit) return fetch(request);               // not downloaded: go to network
        return hit.blob().then(function (bl) {
          var r = resolveRange(range, bl.size);
          return rangeResponse(r, bl.size, r.whole ? bl : bl.slice(r.start, r.end + 1),
                               hit.headers.get('Content-Type'));
        });
      });
    });
  }).catch(function () { return fetch(request); });
}

// Stream an archive down into pieces. The manifest is written LAST, so a download
// cut off halfway is never mistaken for a complete one -- it just is not there.
function storePieces(c, u) {
  return fetch(u, { cache: 'reload' }).then(function (res) {
    if (!res.ok) throw new Error(u + ' -> ' + res.status);
    var type = res.headers.get('Content-Type') || 'application/octet-stream';
    var reader = res.body.getReader();
    var n = 0, total = 0, fill = 0, buf = new Uint8Array(CHUNK);
    function put(piece, idx) { return c.put(chunkKey(u, idx), new Response(piece)); }
    return c.delete(manifestKey(u))
      .then(function () { return c.delete(new Request(u, { method: 'GET' })); })   // old whole copy
      .then(function pump() {
        return reader.read().then(function (step) {
          if (step.done) {
            var tail = fill ? put(buf.slice(0, fill), n++) : Promise.resolve();
            return tail.then(function () {
              return c.put(manifestKey(u), new Response(JSON.stringify(
                { total: total, chunk: CHUNK, pieces: n, type: type }),
                { headers: { 'Content-Type': 'application/json' } }));
            });
          }
          var v = step.value, off = 0, p = Promise.resolve();
          total += v.byteLength;
          while (off < v.byteLength) {
            var take = Math.min(CHUNK - fill, v.byteLength - off);
            buf.set(v.subarray(off, off + take), fill);
            fill += take; off += take;
            if (fill === CHUNK) {
              p = (function (piece, idx, prev) {
                return prev.then(function () { return put(piece, idx); });
              })(buf, n++, p);
              buf = new Uint8Array(CHUNK); fill = 0;
            }
          }
          return p.then(pump);
        });
      });
  });
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
        var job = u.indexOf('.pmtiles') !== -1 ? storePieces(c, u)
          : fetch(u, { cache: 'reload' }).then(function(r){
              if (!r.ok) throw new Error(u + ' -> ' + r.status);
              return c.put(new Request(u, { method:'GET' }), r);
            });
        return job.then(function(){
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

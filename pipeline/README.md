# Data pipeline

**This pipeline does not regenerate everything the app loads.** It used to
claim it did. See "Not regenerated" at the bottom before trying another unit.
What it does cover uses national data sources that take a bounding box, so
nothing in those scripts is Colorado-specific.

## Order

| # | script | makes | notes |
|---|---|---|---|
| 1 | `fetch_naip.py` | NAIP mosaic | 6 requests, ~6 MB |
| 2 | `fetch_nlcd.py` | land cover + tree canopy | MRLC WMS |
| 3 | `make_grids.py` | canopy, forage, road-distance grids | needs 2 and roads |
| 4 | `fetch_water.py` | streams with **fcode**, waterbodies | see the warning below |
| 5 | `fetch_roads.py` | roads, buffered by `road_buffer_m` | see the warning below |
| 6 | `fetch_contours.py` | contour vectors | USGS carto |
| 7 | `build_basemap.py` | terrain basemap master | landcover + canopy + hillshade |
| 8 | `tile.py` | PMTiles from a master image | z8–15, 512 px, JPEG |
| 9 | `autoscout_hotspot_tier.py` | old hotspot layer as tiers | comparison only, never an input |
| 10 | `autoscout_access.py` | trail distance, walk-in hours, reachability | ~30 s including 11–12 |
| 11 | `autoscout_surface.py` | Auto-Scout score per cell | needs 10 |
| 12 | `autoscout_areas.py` | `grids/autoscout_grid.png`, `data/vectors/scout_areas.geojson` | needs 9–11 |

Steps 9–12 write intermediates to `~/gmu44-scratch/work/autoscout`, outside the
repo. Restored 2026-09-14 after the originals were lost; regenerating reproduced
the committed outputs byte for byte.

**This table is incomplete.** Row 6 names `fetch_contours.py`, which does not
exist — contours are `smooth_contours.py` then `tile_contours.py`. Also present
and not ordered here: `build_cost.py`, `fetch_mvum.py`, `fetch_rec_sites.py`,
`fetch_tcc.py`, `roaddist.py`, `trail_stats.py`. Their order has not been
verified, so it is not guessed at.

## Warnings that cost real time to learn

- **NHD flowlines: request `fcode`, not just `ftype`.** FTYPE 460 only means
  "StreamRiver". Whether it holds water in September is FCODE — 46006 perennial,
  46003 intermittent, 46007 ephemeral. In GMU 44 only **21.7%** are perennial,
  and drawing them alike understated distance-to-water twenty-fold. (HANDOFF 5i)
- **Road distance must be computed on a buffered extent.** Roads just outside the
  boundary are still roads. Without the buffer the farthest cell landed exactly
  ON the map edge. (HANDOFF 5g)
- **Contours need one Chaikin pass, no simplification.** USGS traces them across
  DEM cells and the staircase shows past z15. Any simplify step moves the line
  5–14 m. (HANDOFF 5e)
- **USGS 1 m DEM overviews are all nodata.** Read full resolution. (HANDOFF 6)
- **LANDFIRE EVT is 52–61% accurate** in Rocky Mountain conifer, and its
  understory layer is a lookup from overstory type, not a measurement. Use it to
  stratify, never as a forage predictor.

## Not regenerated

Checked 2026-09-14 by asking which script writes each grid the app loads. The
finished files are committed; the code that made these lived in scratch folders
that were wiped.

| grid | status |
|---|---|
| `elev_grid.png` | no generator — three scripts read it, none write it |
| `terrain_mult_grid.png` | `build_cost.py` saves `cost_terrain_mult.npy` to its working folder; the step that encodes the app's PNG is lost |
| `water_dist_grid.png` | no generator |
| `ownership_grid.png` | no generator |
| `cost_grid.png` | no generator — still read by Guide routing and navigation's off-route reroute |
| `stealth_risk_grid.png` | no generator, and nothing reads it |
| `gmu44_elk_probability.pmtiles` | no generator; GMU 44 only |

A second unit needs generators for all of these first.

**Rule: nothing that produces a committed file stays in scratch.** Put it here the
day it is written. This is the second time generators have been lost.

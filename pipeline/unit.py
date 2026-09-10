"""Unit configuration. Every script reads bounds and grid size from here so
that building another unit means editing unit.json, not editing code."""
import json, os, math
_HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(_HERE, 'unit.json')))
b = CFG['bounds']
LON0, LAT0 = b['lon0'], b['lat0']          # upper-left
LON1, LAT1 = b['lon1'], b['lat1']          # lower-right
EW, EH = CFG['grid']['w'], CFG['grid']['h']
SLUG = CFG['slug']
ROAD_BUFFER_M = CFG['road_buffer_m']
TREELINE_FT = CFG['treeline_ft']
DENSE_CANOPY_PCT = CFG['dense_canopy_pct']
MINZOOM, MAXZOOM = CFG['tiles']['minzoom'], CFG['tiles']['maxzoom']
TILESIZE = CFG['tiles']['tilesize']
REPO = os.path.dirname(_HERE)
MID_LAT = (LAT0 + LAT1) / 2.0
CELL_X_M = (LON1 - LON0) / EW * 111320 * math.cos(math.radians(MID_LAT))
CELL_Y_M = abs((LAT1 - LAT0) / EH * 110574)
EXTENT_STR = "%.6f,%.6f,%.6f,%.6f" % (LON0, LAT1, LON1, LAT0)
def buffered_extent(metres=None):
    m = ROAD_BUFFER_M if metres is None else metres
    dlat = m / 110574.0
    dlon = m / (111320.0 * math.cos(math.radians(MID_LAT)))
    return "%.6f,%.6f,%.6f,%.6f" % (LON0-dlon, LAT1-dlat, LON1+dlon, LAT0+dlat)

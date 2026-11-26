from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from room_limits import measure,NORTH,EAST_LOW
from shapely.geometry import box
assert measure("north",box(0,0,3.15+.18,2.30+.18)) is None
assert measure("east_low",box(0,0,3.50+.18,2.0+.18)) is None
assert measure("north",box(0,0,NORTH[0]+.181,NORTH[1]+.181))
assert measure("east_low",box(0,0,EAST_LOW[0]+.181,EAST_LOW[1]+.181))
assert measure("left",box(0,0,5,4).union(box(5,1,8,1.6))) is None
print("5 dimensional regression cases passed")

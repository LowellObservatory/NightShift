import numpy as np
import pyresample as pr

print(pr.version.get_versions())

area_def = pr.geometry.AreaDefinition('areaD',
                                      'Europe (3km, HRV, VTC)',
                                      'areaD',
                                      {'a': '6378144.0',
                                       'b': '6356759.0',
                                       'lat_0': '50.00',
                                       'lat_ts': '50.00',
                                       'lon_0': '8.00',
                                       'proj': 'stere'},
                                      800, 800,
                                      [-1370912.72, -909968.64,
                                       1029087.28, 1490031.36])

data = np.fromfunction(lambda y, x: y*x, (50, 10))
lons = np.fromfunction(lambda y, x: 3 + x, (50, 10))
lats = np.fromfunction(lambda y, x: 75 - y, (50, 10))
swath_def = pr.geometry.SwathDefinition(lons=lons, lats=lats)

mapcenter = [-111.4223, 34.7443]
clon = mapcenter[0]
clat = mapcenter[1]

latMin = clat - 5
latMax = clat + 5

lonMin = clon - 5
lonMax = clon + 5
gridRes = 1

lats = np.arange(latMin, latMax, gridRes)
lons = np.arange(lonMin, lonMax, gridRes)

# mglons, mglats = np.meshgrid(lons, lats)

mglons = np.fromfunction(lambda y, x: 3 + x, (50, 10))
mglats = np.fromfunction(lambda y, x: 75 - y, (50, 10))

swath_def = pr.geometry.SwathDefinition(lons=mglons, lats=mglats)
area_def = swath_def.compute_optimal_bb_area({'proj': 'lcc',
                                              'lon_0': clon,
                                              'lat_0': clat,
                                              'lat_1': clat,
                                              'lat_2': clat})

import os
import math
import gdal
import numpy as np
from read_headers import variable_names, metadata, read_header
from coords import xy_coords, distance, points_within_distance
from config import DATA_PATHS, ul, lr, find_data


loaded_datasets = {}

def get_dataset(file):
    '''Returns an open GDAL dataset object for the given BIOCLIM data file.
    
    >>> data = get_dataset('bio1')
    >>> import os
    >>> os.path.basename(data.GetDescription())
    'bio1.bil'
    >>> data2 = get_dataset('src/data/bio1.bil')
    >>> os.path.basename(data.GetDescription()) == os.path.basename(data2.GetDescription())
    True
    '''
    if not file.endswith('.bil'): file += '.bil'
    if not file in loaded_datasets:
        # check the current working directory as well sa the package data path
        path = find_data(file)
        if path is None:
            raise Exception("Couldn't find %s in working directory or package data." % file)
        loaded_datasets[file] = gdal.Open(path)
            
    if not file in metadata:
        read_header(file[:-len('.bil')])
    
    return loaded_datasets[file]


def extract_attributes(file):
    '''Get information about a .bil file.'''
    data = get_dataset(file)
    raster = data.ReadAsArray()
    try:
        no_value = metadata[file]['nodata']
    except KeyError:
        no_value = -9999
    
    ul = (float(metadata[file]['ulymap']), float(metadata[file]['ulxmap']))
    dims = (float(metadata[file]['ydim']), float(metadata[file]['xdim']))
    
    size = data.RasterYSize, data.RasterXSize

    return data, raster, no_value, ul, dims, size


def get_values(file, points):
    '''Given a .bil file (or other file readable by GDAL) and a set of (lat,lon) 
    points, return a list of values for those points. -9999 will be converted to 
    None.
    
    >>> lat_lons = [(10,10), (20,20), (0,0)]
    >>> get_values('bio1', lat_lons)
    [257.0, 249.0, None]
    '''

    data, raster, no_value, ul, dims, size = extract_attributes(file)

    result = [float(raster[xy_coords((lat, lon), ul, dims, size)]) for (lat, lon) in points]
    result = [None if value == no_value else value for value in result]

    return result


def get_average(file, points, radius=40):
    '''Like get_values, but computes the average value within a circle of the 
    specified radius (in km).
    
    Missing values are ignored. Returns None if there were no values within the 
    circle.
    
    >>> lat_lons = [(10,10), (20,20), (0,0)]
    >>> get_average('bio1', lat_lons, 0)
    [257.0, 249.0, None]
    >>> get_average('bio1', lat_lons, 100) != get_average('bio1', lat_lons, 50) != get_average('bio1', lat_lons, 0)
    True
    '''

    data, raster, no_value, ul, dims, size = extract_attributes(file)
    
    result = []
    for point in points:
        within = points_within_distance(point, radius, ul, dims)
        raster_positions = [xy_coords((lat, lon), ul, dims, size) for (lat, lon) in within]
        values = [raster[pos] for pos in raster_positions if raster[pos] != no_value]
        if len(values) == 0: result.append(None)
        else:
            result.append(sum(values)/float(len(values)))

    return result


def get_spatial_variance(file, points, radius=40):
    '''Like get_values, but computes the spatial variance within a circle of the
    specified radius (in km).
    
    Missing values are ignored. Returns None if there were no values within the 
    circle.
    
    >>> lat_lons = [(10,10), (20,20), (0,0)]
    >>> get_spatial_variance('bio1', lat_lons, 0)
    [0.0, 0.0, None]
    >>> (get_spatial_variance('bio1', lat_lons[0:1], 100) >= 
    ... get_spatial_variance('bio1', lat_lons[0:1], 50) >= 
    ... get_spatial_variance('bio1', lat_lons[0:1], 0))
    True
    '''

    data, raster, no_value, ul, dims, size = extract_attributes(file)
    
    result = []
    for point in points:
        # because the distance between longitude points approaches 0 at the 
        # poles, only compute variance between 60 N and 60 S
        if abs(point[0]) > 60:
            result.append(None)
            continue

        within = points_within_distance(point, radius, ul, dims)
        raster_positions = [xy_coords((lat, lon), ul, dims, size) for (lat, lon) in within]
        values = [raster[pos] for pos in raster_positions if raster[pos] != no_value]
        if len(values) == 0: result.append(None)
        else:
            result.append(float(np.var(values)))

    return result

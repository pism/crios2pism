from netCDF4 import Dataset as NC
from cdo import Cdo
cdo = Cdo()
from datetime import datetime, timedelta
from osgeo import gdal
from glob import glob
import os.path
import time
import collections,re,sys
import gc
import netCDF4
import numpy as np
import csv

reftime = "2008-01-01"
components = ["vx", "vy", "vv"]
download_dir = "data"

# These are files for which domain_checksum2() == 0
blacklist_raw = (
    'TSX_W69.10N_02Jun18_13Jun18_09-48-58_{parameter}_v02.0{ext}',
    'TSX_W69.10N_29May15_20Jun15_09-48-37_{parameter}_v02.0{ext}',
    'TSX_W69.10N_31May14_11Jun14_09-48-32_{parameter}_v02.0{ext}',
    'TSX_W69.10N_03Jul09_14Jul09_09-48-07_{parameter}_v02.0{ext}',
    'TSX_W69.10N_13Jun18_05Jul18_09-48-58_{parameter}_v02.0{ext}',
    'TSX_W69.10N_05Jul18_27Jul18_09-49-00_{parameter}_v02.0{ext}',
    'TSX_W69.10N_26May16_17Jun16_09-48-43_{parameter}_v02.0{ext}',
    'TSX_W69.10N_18Jul17_09Aug17_09-48-53_{parameter}_v02.0{ext}',
    'TSX_W69.10N_16Jul13_18Aug13_09-48-29_{parameter}_v02.0{ext}',
    'TSX_W69.10N_30Apr18_02Jun18_09-48-57_{parameter}_v02.0{ext}',
    'TSX_W69.10N_10Nov15_21Nov15_09-48-42_{parameter}_v02.0{ext}',
    'TSX_W69.10N_23Aug11_14Sep11_09-48-21_{parameter}_v02.0{ext}',
    'TSX_W69.10N_18Sep09_29Sep09_09-48-11_{parameter}_v02.0{ext}',
    'TSX_W69.10N_28Apr09_09May09_09-48-04_{parameter}_v02.0{ext}',
    'TSX_W69.10N_09Sep18_20Sep18_09-49-03_{parameter}_v02.0{ext}',
    'TSX_W69.10N_30Jan09_10Feb09_09-48-02_{parameter}_v02.0{ext}',
    'TSX_W69.10N_06Feb11_28Feb11_09-48-12_{parameter}_v02.0{ext}',
    'TSX_W69.10N_21Apr12_02May12_09-48-19_{parameter}_v02.0{ext}',
    'TSX_W69.10N_10Feb14_21Feb14_09-48-29_{parameter}_v02.0{ext}',
    'TSX_W69.10N_23Nov14_04Dec14_09-48-46_{parameter}_v02.0{ext}',
    'TSX_W69.10N_25Aug10_05Sep10_09-48-16_{parameter}_v02.0{ext}',
    'TSX_W69.10N_21Nov10_02Dec10_09-48-17_{parameter}_v02.0{ext}',
    'TSX_W69.10N_14Feb17_25Feb17_09-48-47_{parameter}_v02.0{ext}',
    'TSX_W69.10N_18May15_29May15_09-48-36_{parameter}_v02.0{ext}',
    'TSX_W69.10N_04Feb12_15Feb12_09-48-17_{parameter}_v02.0{ext}',
    'TSX_W69.10N_19Apr18_30Apr18_09-48-57_{parameter}_v02.0{ext}',
    'TSX_W69.10N_21Jul11_01Aug11_09-48-19_{parameter}_v02.0{ext}',
    'TSX_W69.10N_12Feb13_23Feb13_09-48-22_{parameter}_v02.0{ext}',
    'TSX_W69.10N_24Apr11_05May11_09-48-14_{parameter}_v02.0{ext}',
    'TSX_W69.10N_26Apr10_07May10_09-48-11_{parameter}_v02.0{ext}')

def get_blackset(**kwargs):
    return set(x.format(**kwargs) for x in blacklist_raw)

def remove_blacklist(pfiles, **kwargs):
    blackset = get_blackset(**kwargs)
    ret = []
    for pf in pfiles:
        if pf['fname'] in blackset:
            print('Blacklisting {fname}'.format(**pf))
        else:
            ret.append(pf)
    return ret
# ----------------------------------------------------

def up_to_date(ifnames, ofnames):
    """Returns True if the files in ofnames exist, and are all newer than
    the files in ifnames"""
    
    # Get oldest time of ofnames (ms since the epoch)
    now = datetime.now().timestamp() * 1000.
    oldest_otime = now
    for ofname in ofnames:
        if not os.path.exists(ofname):
            return False    # Automatically regenerate if it doesn't exist
        oldest_otime = min(oldest_otime, os.path.getmtime(ofname))

    # Get newest itime
    newest_itime = os.path.getmtime(ifnames[0])
    for ifname in ifnames[1:]:
        newest_itime = max(newest_itime, os.path.getmtime(ifname))

    return oldest_otime > newest_itime

# ----------------------------------------------------------------
def merge_dicts(*dicts):
    dict = type(dicts[0])(dicts[0].items())
    for xdict in dicts[1:]:
        dict.update(xdict.items())
    return dict

class NSIDC_0418(dict):

    def format(self, **overrides):
        # Override self with overrides
        pfile = merge_dicts(self, overrides)

        pfile['sstartdate'] = datetime.strftime(pfile['startdate'], '%d%b%y')
        pfile['senddate'] = datetime.strftime(pfile['enddate'], '%d%b%y')
        pfile['snominal_time'] = '{:02d}-{:02d}-{:02d}'.format(*pfile['nominal_time'])
        # Override ext with user-given value
        if pfile['parameter'] == '':
            fmt = '{source}_{grid}_{sstartdate}_{senddate}_{snominal_time}_v{version}{ext}'
        else:
            fmt = '{source}_{grid}_{sstartdate}_{senddate}_{snominal_time}_{parameter}_v{version}{ext}'

        return fmt.format(**pfile)

imonth = { 'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7,
    'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}


reNSIDC_0418 = re.compile(r'(TSX|TDX)_([EWS][0-9.]+[NS])_(\d\d(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d\d)_(\d\d(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d\d)_(\d\d)-(\d\d)-(\d\d)(_(vv|vx|vy|ex|ey)?)_v([0-9.]+)(\..+)')

def parse_nsidc_0418(leaf):
    """
    See: https://nsidc.org/data/nsidc-0481"""

    match = reNSIDC_0418.match(leaf)
    if match is None:
        return None

    sstartdate = match.group(3)
    senddate = match.group(5)
    ret = NSIDC_0418(
        fname=leaf,
        source=match.group(1),
        grid=match.group(2),
        startdate=datetime.strptime(sstartdate, "%d%b%y"),
        enddate=datetime.strptime(senddate, "%d%b%y"),
        nominal_time=(int(match.group(7)), int(match.group(8)), int(match.group(9))),
        parameter=match.group(11),   # Could be None
        version=match.group(12),
        ext=match.group(13))

    if ret['parameter'] is None:
        ret['parameter'] = ''    # Don't like None for sorting

    return ret

# --------------------------------------------------------------
def list_pfiles(dir, parser_fn, attrs):
    """Lists files in a directory, that match the attributes
    Yields parsed dict output"""

    pfiles = list()
    for file in os.listdir(dir):
        pfile = parser_fn(file)
        if pfile is None:
            continue
        pfile['dir'] = dir
        pfile['path'] = os.path.join(pfile['dir'], pfile['fname'])

        # See if it matches attrs
        match = True
        for (k,v) in attrs.items():
            if pfile[k] != v:
                match = False
                break

        if not match:
            continue

        pfiles.append(pfile)

    pfiles.sort(key = lambda x: (x['source'], x['grid'], x['startdate'], x['enddate'], x['parameter'], x['nominal_time'], x['version'], x['ext']))

    return pfiles
# --------------------------------------------------------------
def tiff_to_netcdf(pfile, odir, oext='.nc'):
    """Converts single GeoTIFF to NetCDF
    ifname:
        The input GeoTIFF file
    oext:
        Extension to use on the output file
    Returns:
        Name of the output NetCDF file (as a pfile parsed file)"""

    os.makedirs(odir, exist_ok=True)

    # Generate ofname
    ifname = os.path.join(pfile['dir'], pfile['fname'])
    opfile = type(pfile)(pfile.items())
    opfile['dir'] = odir
    opfile['ext'] = oext
    opfile['fname'] = opfile.format()
    ofname = os.path.join(odir, opfile['fname'])
    tmp0 = os.path.join(odir, opfile.format(ext='.tiff_to_netcdf_0.nc'))

    # Don't regenerate files already built
    if up_to_date((ifname,), (ofname,)):
        return opfile

    try:
        print(f"Converting {ifname} to {ofname}")
        # use gdal's python binging to convert GeoTiff to netCDF
        # advantage of GDAL: it gets the projection information right
        # disadvantage: the variable is named "Band1", lacks metadata
        ds = gdal.Open(ifname)
        ds = gdal.Translate(tmp0, ds)
        ds = None

        # This deduces the mid-point (nominal) date from the filename
        nominal_date = pfile['startdate'] + (pfile['enddate'] - pfile['startdate']) / 2

        # Set the time axis
        var = pfile['parameter']
        inputs = [
            f'-setreftime,{reftime}',
            f'-setattribute,{var}@units="m year-1"',
            f'-chname,Band1,{var}',
            f'{tmp0}']
        cdo.settaxis(
            nominal_date.isoformat(),
            input=' '.join(inputs),
            output=ofname,
            options="-f nc4 -z zip_2")

        return opfile
    finally:
        try:
            os.remove(tmp0)
        except FileNotFoundError:
            pass

# --------------------------------------------------------------
# https://stackoverflow.com/questions/11144513/cartesian-product-of-x-and-y-array-points-into-single-array-of-2d-points
def np_cartesian_product(x,y):
#    return np.transpose([np.tile(x, len(y)), np.repeat(y, len(x))])
    xx = np.transpose(np.tile(x, (len(y),1)))
    yy = np.tile(y, (len(x),1))
    ret = xx+yy
    return ret

def domain_checksum1(time_ncfile, parameter):
    with netCDF4.Dataset(time_ncfile) as nc:
        ncvar = nc.variables[parameter]
        var = ncvar[0,:,:]
        FillValue = ncvar._FillValue

    weights = np_cartesian_product(
        np.array([float(j) for j in range(0,var.shape[0])]),
        np.array([float(i) for i in range(0,var.shape[1])]))
    mask = np.not_equal(var, FillValue)

    return np.sum(np.sum(weights*mask))

def domain_checksum2(time_ncfile, parameter):
    """Count used pixels near the glacier terminus."""

    with netCDF4.Dataset(time_ncfile) as nc:
        ncvar = nc.variables[parameter]
        var = ncvar[0,:,:]
        FillValue = ncvar._FillValue

    mask = np.zeros(var.shape)
    mask[373:413,387:439] = 1   # Close to glacier terminus

    exist = np.not_equal(var, FillValue)

    return np.sum(np.sum(exist*mask))

# --------------------------------------------------------------
def cdo_merge(inputs, output, options):
    for input in inputs:
        cdo.merge(
            input=(input,),
            output=output,
            options=options)
# --------------------------------------------------------------
def merge_glacier(idir, odir, ofpattern, parameters, **attrs):
    """attrs should contain soure, grid
    ofpattern:
        Eg: '{source}_{grid}_2008_2020.nc'
    """
    os.makedirs(odir, exist_ok=True)

    # for parameter in ('vx', 'vy', 'vv'):
    ofnames = []
    for parameter in parameters:
        # Convert GeoTIFF to NetCDF
        atrs = dict(attrs.items())
        atrs['parameter'] = parameter
        atrs['ext'] = '.tif'

        pfiles_tif = list_pfiles(idir, parse_nsidc_0418, atrs)
        pfiles_tif = remove_blacklist(pfiles_tif, parameter=parameter, ext='.tif')
        pfiles_nc = list()
        for ix,pfile in enumerate(pfiles_tif):
#            if ix >= 10:
#                break
            pfiles_nc.append(tiff_to_netcdf(pfile, odir))

#        for pf in pfiles_nc:
#            cs1 = domain_checksum1(os.path.join(pf['dir'],pf['fname']), pf['parameter'])
#            cs2 = domain_checksum2(os.path.join(pf['dir'],pf['fname']), pf['parameter'])
#            pf['domain_checksum1'] = cs1
#            pf['domain_checksum2'] = cs2
#            print(pf['fname'], cs1,cs2)

#        with open(f'checkums_{parameter}.csv', 'w') as fout:
#            writer = csv.writer(fout)
#            for pf in pfiles_nc:
#                writer.writerow([pf['fname'], pf['domain_checksum1'], pf['domain_checksum2']])

        # Merge this individual component and sort by time using "mergetime"
        ofname = os.path.join(
            odir,
            '{source}_{grid}_{parameter}_merged.nc'.format(**atrs))

        inputs = [os.path.join(pf['dir'], pf['fname']) for pf in pfiles_nc]
        cdo.mergetime(input=inputs,
            output=ofname, options="-f nc4 -z zip_2")

    ofnames.append(ofname)

    for pf in pfiles_nc:
        # Create the final merged file
        cdo.merge(
            input=ofnames,
            output=ofpattern.format(*attrs),
            options="-f nc4 -z zip_2")

#print(domain_checksum('outputs/TSX_W69.10N_03Mar09_14Mar09_10-05-12_vx_v02.0.nc', 'vx'))

#sys.exit(0)

merge_glacier('data', 'outputs', '{source}_{grid}_2008_2020.nc',
    ('vx',), source='TSX', grid='W69.10N')
#    ('vx', 'vy', 'vv'), source='TSX', grid='W69.10N')

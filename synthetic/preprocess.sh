#!/bin/bash

for grid in 250 500 1000 2000; do
    python create_geometry.py -s -g $grid pism_outletglacier_g${grid}m.nc
    ncatted  -a _FillValue,topg,d,,  -a _FillValue,usurf,d,, -a _FillValue,thk,d,,  pism_synth_ellps_g${grid}m.nc
    python create_jib.py -s -g $grid pism_synth_jib_g${grid}m.nc
done

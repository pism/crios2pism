odir=2019_05_vc
grid=900
n=560

for d in gris; do     python historical.py -b no_bath -d ${d} --o_dir ${odir} --end 2015-1-1 -q long -s pleiades_broadwell -w 48:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/historical_routing.csv ../../pism-gris/calibration/2017_06_vc/state/gris_g${grid}m_flux_v3a_no_bath_sia_e_1.25_sia_n_3_ssa_n_3.25_ppq_0.6_tefo_0.02_calving_vonmises_calving_0_100.nc; done

odir=2019_05_hc
grid=900
n=560

for d in gris; do     python historical.py --calving hayhurst_calving -b no_bath -d ${d} --o_dir ${odir} --end 2015-1-1 -q long -s pleiades_broadwell -w 48:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/historical_routing.csv ../../pism-gris/calibration/2017_06_vc/state/gris_g${grid}m_flux_v3a_no_bath_sia_e_1.25_sia_n_3_ssa_n_3.25_ppq_0.6_tefo_0.02_calving_vonmises_calving_0_100.nc; done

grid=900
n=360

for d in gris; do     python historical.py --calving hayhurst_calving -b no_bath -d ${d} --o_dir ${odir} --end 2015-1-1 -q t2standard -s chinook -w 28:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/historical_routing.csv ../../pism-gris/calibration/2017_06_vc/state/gris_g${grid}m_flux_v3a_no_bath_sia_e_1.25_sia_n_3_ssa_n_3.25_ppq_0.6_tefo_0.02_calving_vonmises_calving_0_100.nc; done


# ISMIP 6 Runs

odir=2019_07_ismip6
n=120

grid=1000
for d in ismip6; do     python prognostic_core.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q t2standard -s chinook -w 48:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_core.csv ../historical/2019_06_calib/state/ismip6_g1000m_v3a_id_VCM-CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

odir=2019_06_dg_test
n=140

grid=1000
for d in ismip6; do     python prognostic.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q long -s pleiades_broadwell -w 30:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_discharge_given.csv ../historical/2019_06_calib/state/ismip6_g1000m_v3a_id_VCM-CALIB-G1000M_2008-1-1_2015-1-1_us.nc ; done

# ISMIP 6 Runs

odir=2019_08_ismip6
n=120
grid=1000

for d in ismip6; do     python prognostic_core.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q t2standard -s chinook -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_core.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

for d in ismip6; do     python prognostic_open.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q t2standard -s chinook -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_open.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

n=140
grid=1000

odir=2019_09_open

for d in ismip6; do     python prognostic_open.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q long -s pleiades_broadwell -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_open.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

odir=2019_09_core

for d in ismip6; do     python prognostic_core.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q long -s pleiades_broadwell -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_core.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done


n=140
grid=1000

odir=2019_11_open

for d in ismip6; do     python prognostic_open.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q long -s pleiades_broadwell -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_open.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

odir=2019_11_core

for d in ismip6; do     python prognostic_core.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q long -s pleiades_broadwell -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_core.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done


d=ismip6
grid=1000
n=96

odir=2021_02_hybrid
for d in ismip6; do     python prognostic_open.py --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q t2standard -s chinook -w 24:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_open.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

odir=2021_02_blatter
for d in ismip6; do     python prognostic_open.py --stress_balance blatter --spatial_ts ismip6 -b wc -d ${d} --o_dir ${odir} -q t2standard -s chinook -w 96:00:00 -n ${n} -g ${grid} -e ../uncertainty_qunatification/prognostic_open.csv ../historical/2019_08_calib/state/ismip6_g1000m_v3a_id_CALIB-G1000M_2008-1-1_2015-1-1.nc ; done

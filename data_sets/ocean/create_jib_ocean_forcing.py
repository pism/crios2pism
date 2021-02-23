#!/usr/bin/env python
# Copyright (C) 2020-21 Andy Aschwanden

from cftime import utime
from dateutil import rrule
from datetime import datetime
from netCDF4 import Dataset as NC
import gpytorch
import torch
import numpy as np
import pandas as pd
import pylab as plt
from pyproj import Proj


def to_decimal_year(date):
    year = date.year
    start_of_this_year = datetime(year=year, month=1, day=1)
    start_of_next_year = datetime(year=year + 1, month=1, day=1)
    year_elapsed = (date - start_of_this_year).total_seconds()
    year_duration = (start_of_next_year - start_of_this_year).total_seconds()
    fraction = year_elapsed / year_duration

    return date.year + fraction


def melting_point_temperature(depth, salinity):
    a = [-0.0575, 0.0901, -7.61e-4]
    return a[0] * salinity + a[1] + a[2] * depth


def create_nc(nc_outfile, theta_ocean, grid_spacing, time_dict):
    """
    Generate netCDF file
    """

    time = time_dict["time"]
    time_units = time_dict["units"]
    time_calendar = time_dict["calendar"]
    time_bnds = time_dict["time_bnds"]

    nt = len(theta_ocean)
    xdim = "x"
    ydim = "y"

    # define output grid, these are the extents of Mathieu's domain (cell
    # corners)
    e0 = -638000
    n0 = -3349600
    e1 = 864700
    n1 = -657600

    # Add a buffer on each side such that we get nice grids up to a grid spacing
    # of 36 km.

    buffer_e = 148650
    buffer_n = 130000
    e0 -= buffer_e + 468000
    n0 -= buffer_n
    e1 += buffer_e
    n1 += buffer_n

    # Shift to cell centers
    e0 += grid_spacing / 2
    n0 += grid_spacing / 2
    e1 -= grid_spacing / 2
    n1 -= grid_spacing / 2

    de = dn = grid_spacing  # m
    m = int((e1 - e0) / de) + 1
    n = int((n1 - n0) / dn) + 1

    easting = np.linspace(e0, e1, m)
    northing = np.linspace(n0, n1, n)
    ee, nn = np.meshgrid(easting, northing)

    # Set up EPSG 3413 (NSIDC north polar stereo) projection
    projection = "epsg:3413"
    proj = Proj(projection)

    lon, lat = proj(ee, nn, inverse=True)

    # number of grid corners
    grid_corners = 4
    # grid corner dimension name
    grid_corner_dim_name = "nv4"

    # array holding x-component of grid corners
    gc_easting = np.zeros((m, grid_corners))
    # array holding y-component of grid corners
    gc_northing = np.zeros((n, grid_corners))
    # array holding the offsets from the cell centers
    # in x-direction (counter-clockwise)
    de_vec = np.array([-de / 2, de / 2, de / 2, -de / 2])
    # array holding the offsets from the cell centers
    # in y-direction (counter-clockwise)
    dn_vec = np.array([-dn / 2, -dn / 2, dn / 2, dn / 2])
    # array holding lat-component of grid corners
    gc_lat = np.zeros((n, m, grid_corners))
    # array holding lon-component of grid corners
    gc_lon = np.zeros((n, m, grid_corners))

    for corner in range(0, grid_corners):
        # grid_corners in x-direction
        gc_easting[:, corner] = easting + de_vec[corner]
        # grid corners in y-direction
        gc_northing[:, corner] = northing + dn_vec[corner]
        # meshgrid of grid corners in x-y space
        gc_ee, gc_nn = np.meshgrid(gc_easting[:, corner], gc_northing[:, corner])
        # project grid corners from x-y to lat-lon space
        gc_lon[:, :, corner], gc_lat[:, :, corner] = proj(gc_ee, gc_nn, inverse=True)

    nc = NC(nc_outfile, "w", format="NETCDF4", compression_level=2)

    nc.createDimension(xdim, size=easting.shape[0])
    nc.createDimension(ydim, size=northing.shape[0])

    time_dim = "time"
    if time_dim not in list(nc.dimensions.keys()):
        nc.createDimension(time_dim)

    # create a new dimension for bounds only if it does not yet exist
    bnds_dim = "nb2"
    if bnds_dim not in list(nc.dimensions.keys()):
        nc.createDimension(bnds_dim, 2)

    # variable names consistent with PISM
    time_var_name = "time"
    bnds_var_name = "time_bnds"

    # create time variable
    time_var = nc.createVariable(time_var_name, "d", dimensions=(time_dim))
    time_var[:] = time
    time_var.bounds = bnds_var_name
    time_var.units = time_units
    time_var.calendar = time_calendar
    time_var.standard_name = time_var_name
    time_var.axis = "T"

    # create time bounds variable
    time_bnds_var = nc.createVariable(bnds_var_name, "d", dimensions=(time_dim, bnds_dim))
    time_bnds_var[:, 0] = time_bnds[0:-1]
    time_bnds_var[:, 1] = time_bnds[1::]

    var = xdim
    var_out = nc.createVariable(var, "d", dimensions=(xdim))
    var_out.axis = xdim
    var_out.long_name = "X-coordinate in Cartesian system"
    var_out.standard_name = "projection_x_coordinate"
    var_out.units = "meters"
    var_out[:] = easting

    var = ydim
    var_out = nc.createVariable(var, "d", dimensions=(ydim))
    var_out.axis = ydim
    var_out.long_name = "Y-coordinate in Cartesian system"
    var_out.standard_name = "projection_y_coordinate"
    var_out.units = "meters"
    var_out[:] = northing

    var = "lon"
    var_out = nc.createVariable(var, "d", dimensions=(ydim, xdim))
    var_out.units = "degrees_east"
    var_out.valid_range = -180.0, 180.0
    var_out.standard_name = "longitude"
    var_out.bounds = "lon_bnds"
    var_out[:] = lon

    var = "lat"
    var_out = nc.createVariable(var, "d", dimensions=(ydim, xdim))
    var_out.units = "degrees_north"
    var_out.valid_range = -90.0, 90.0
    var_out.standard_name = "latitude"
    var_out.bounds = "lat_bnds"
    var_out[:] = lat

    nc.createDimension(grid_corner_dim_name, size=grid_corners)

    var = "lon_bnds"
    # Create variable 'lon_bnds'
    var_out = nc.createVariable(var, "f", dimensions=(ydim, xdim, grid_corner_dim_name))
    # Assign units to variable 'lon_bnds'
    var_out.units = "degreesE"
    # Assign values to variable 'lon_nds'
    var_out[:] = gc_lon

    var = "lat_bnds"
    # Create variable 'lat_bnds'
    var_out = nc.createVariable(var, "f", dimensions=(ydim, xdim, grid_corner_dim_name))
    # Assign units to variable 'lat_bnds'
    var_out.units = "degreesN"
    # Assign values to variable 'lat_bnds'
    var_out[:] = gc_lat

    var = "theta_ocean"
    var_out = nc.createVariable(var, "f", dimensions=("time", "y", "x"), fill_value=-2e9, zlib=True, complevel=2)
    var_out.units = "Celsius"
    var_out.long_name = "theta_ocean"
    var_out.grid_mapping = "mapping"
    var_out.coordinates = "lon lat"
    var_out[:] = np.repeat(theta_ocean, m * n).reshape(nt, n, m)

    mapping = nc.createVariable("mapping", "c")
    mapping.ellipsoid = "WGS84"
    mapping.false_easting = 0.0
    mapping.false_northing = 0.0
    mapping.grid_mapping_name = "polar_stereographic"
    mapping.latitude_of_projection_origin = 90.0
    mapping.standard_parallel = 70.0
    mapping.straight_vertical_longitude_from_pole = -45.0

    # writing global attributes
    nc.Conventions = "CF 1.5"
    nc.close()


if __name__ == "__main__":

    # depths to average over
    depth_min = 225
    depth_max = 275
    # depth for freezing point calculation
    depth = 250
    salinity = 34
    grid_spacing = 18000

    freq = "1D"
    calendar = "standard"
    units = "days since 1980-1-1"
    cdftime_days = utime(units, calendar)

    start_date = datetime(1980, 1, 1)
    end_date = datetime(2021, 1, 1)
    end_date_yearly = datetime(2021, 1, 2)

    # create list with dates from start_date until end_date with
    # periodicity prule.
    bnds_datelist = list(rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date_yearly))
    bnds_datelist_yearly = list(rrule.rrule(rrule.YEARLY, dtstart=start_date, until=end_date_yearly))

    # calculate the days since refdate, including refdate, with time being the
    bnds_interval_since_refdate = cdftime_days.date2num(bnds_datelist)
    bnds_interval_since_refdate_yearly = cdftime_days.date2num(bnds_datelist_yearly)
    time_interval_since_refdate = bnds_interval_since_refdate[0:-1] + np.diff(bnds_interval_since_refdate) / 2

    time_dict = {
        "calendar": calendar,
        "units": units,
        "time": time_interval_since_refdate,
        "time_bnds": bnds_interval_since_refdate,
    }

    step = 1.0 / 12
    decimal_time = np.arange(start_date.year, end_date.year, step)

    ginr = pd.read_csv("ginr/ginr_disko_bay_250m.csv", parse_dates=["Date"])
    ginr = ginr.set_index("Date").drop(columns=["Unnamed: 0"])
    ginr = ginr.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])

    ginr_ctd26 = pd.read_csv("ginr/ginr_ctd_station_26.csv").dropna()

    omg_fjord = pd.read_csv("omg/omg_axctd_ilulissat_fjord_10s_mean_250m.csv", parse_dates=["Date"])
    omg_fjord = omg_fjord.set_index("Date").drop(columns=["Unnamed: 0"])
    omg_fjord = (
        omg_fjord.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])
    )

    omg_bay = pd.read_csv("omg/omg_axctd_disko_bay_10s_mean_250m.csv", parse_dates=["Date"])
    omg_bay = omg_bay.set_index("Date").drop(columns=["Unnamed: 0"])
    omg_bay = omg_bay.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])

    ices = pd.read_csv("ices/ices_disko_bay_250m.csv", parse_dates=["Date"])
    ices = ices.set_index("Date")
    ices = ices.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])

    xctd_fjord = pd.read_csv("xctd_fjord/xctd_ilulissat_fjord.csv", parse_dates=["Date"])
    xctd_fjord = xctd_fjord.set_index("Date")
    xctd_fjord = (
        xctd_fjord.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])
    )

    xctd_bay = pd.read_csv("moorings/xctd_mooring_disko_bay.csv", parse_dates=["Date"])
    xctd_bay = xctd_bay.set_index("Date")
    xctd_bay = (
        xctd_bay.groupby(pd.Grouper(freq=freq)).mean().dropna(subset=["Temperature [Celsius]", "Salinity [g/kg]"])
    )

    X_ginr = ginr["Year"].values.reshape(-1, 1)
    X_ginr_ctd26 = ginr_ctd26["Year"].values.reshape(-1, 1)
    X_ices = ices["Year"].values.reshape(-1, 1)
    X_omg_bay = omg_bay["Year"].values.reshape(-1, 1)
    X_omg_fjord = omg_fjord["Year"].values.reshape(-1, 1)
    X_xctd_bay = xctd_bay["Year"].values.reshape(-1, 1)
    X_xctd_fjord = xctd_fjord["Year"].values.reshape(-1, 1)

    T_ginr = ginr["Temperature [Celsius]"].values
    T_ginr_ctd26 = ginr_ctd26["Temperature [Celsius]"].values
    T_ices = ices["Temperature [Celsius]"].values
    T_omg_bay = omg_bay["Temperature [Celsius]"].values
    T_omg_fjord = omg_fjord["Temperature [Celsius]"].values
    T_xctd_bay = xctd_bay["Temperature [Celsius]"].values
    T_xctd_fjord = xctd_fjord["Temperature [Celsius]"].values

    # Here we can select which observations are being used for the GP
    # Only use Disko Bay obs, exluding the moorings at 340m which gives
    # us an idea of seasonality
    merged = pd.concat([ginr, ginr_ctd26, ices, omg_bay])
    merged = merged.sort_values(by="Year")

    X = merged["Year"].values.reshape(-1, 1)
    y = merged["Temperature [Celsius]"].values
    X_new = decimal_time[:, None]

    # # We will use the simplest form of GP model, exact inference
    # class ExactGPModel(gpytorch.models.ExactGP):
    #     def __init__(self, train_x, train_y, likelihood, cov):
    #         super(ExactGPModel, self).__init__(train_x, train_y, likelihood)
    #         self.mean_module = gpytorch.means.ConstantMean()
    #         self.covar_module = gpytorch.kernels.ScaleKernel(cov)

    #     def forward(self, x):
    #         mean_x = self.mean_module(x)
    #         covar_x = self.covar_module(x)
    #         return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)

    X_train = torch.tensor(X).to(torch.float)
    y_train = torch.tensor(np.squeeze(y)).to(torch.float)
    X_test = torch.tensor(X_new).to(torch.float)

    # # initialize likelihood and model
    # noise_prior = gpytorch.priors.NormalPrior(0.2, 0.2)
    # likelihood = gpytorch.likelihoods.GaussianLikelihood(noise_prior=noise_prior)

    # cov = gpytorch.kernels.RBFKernel
    # model = ExactGPModel(X_train, y_train, likelihood, cov())

    # # Find optimal model hyperparameters
    # model.train()
    # likelihood.train()

    # # Use the adam optimizer
    # optimizer = torch.optim.Adam(model.parameters(), lr=0.1)  # Includes GaussianLikelihood parameters

    # # "Loss" for GPs - the marginal log likelihood
    # mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    # for i in range(500):
    #     # Zero gradients from previous iteration
    #     optimizer.zero_grad()
    #     # Output from model
    #     output = model(X_train)
    #     # Calc loss and backprop gradients
    #     loss = -mll(output, y_train)
    #     loss.backward()
    #     if i % 20 == 0:
    #         print(i, loss.item(), model.likelihood.noise.item())
    #     optimizer.step()

    # # Get into evaluation (predictive posterior) mode
    # model.eval()
    # likelihood.eval()
    # with torch.no_grad():  # , gpytorch.settings.fast_pred_var():
    #     # Draw n_samples
    #     n_samples = 10
    #     f_pred = model(X_test)
    #     samples = f_pred.sample(
    #         sample_shape=torch.Size(
    #             [
    #                 n_samples,
    #             ]
    #         )
    #     )

    # omg_bay_col = "#08519c"
    # ices_bay_col = "#6baed6"
    # ginr_bay_col = "#c6dbef"
    # ginr_ctd26_col = "#74c476"

    # omg_fjord_col = "#54278f"
    # xctd_fjord_col = "#9e9ac8"
    # ms = 5
    # mew = 0.25

    # # Initialize plot
    # fig, ax = plt.subplots(1, 1)

    # ax.plot(X_test.numpy(), samples.numpy().T, color="k", linewidth=0.5)

    # # plot the data and the true latent function
    # ax.plot(X_omg_bay, T_omg_bay, "o", color=omg_bay_col, ms=ms, mec="k", mew=mew, label="OMG (Disko Bay)")
    # ax.plot(X_ices, T_ices, "o", color=ices_bay_col, ms=ms, mec="k", mew=mew, label="ICES (Disko Bay)")
    # ax.plot(X_ginr, T_ginr, "o", color=ginr_bay_col, ms=ms, mec="k", mew=mew, label="GINR (Disko Bay)")
    # ax.plot(X_ginr_ctd26, T_ginr_ctd26, "o", color=ginr_ctd26_col, ms=ms, mec="k", mew=mew, label="GINR (Station 26)")
    # # ax.plot(X_xctd_bay, T_xctd_bay, "o", color="#006d2c", mec="k", mew=mew, ms=ms, label="Mooring (Disko Bay)")
    # ax.plot(
    #     X_xctd_fjord, T_xctd_fjord, "o", color=xctd_fjord_col, ms=ms, mec="k", mew=mew, label="XCTD (Ilulissat Fjord)"
    # )
    # ax.plot(X_omg_fjord, T_omg_fjord, "o", color=omg_fjord_col, ms=ms, mec="k", mew=mew, label="OMG (Ilulissat Fjord)")

    # ax.set_xlabel("Time")
    # ax.set_ylabel("Temperature (Celsius)")
    # ax.set_xlim(1980, 2021)
    # ax.set_ylim(0, 5)
    # plt.legend()
    # fig.savefig("ilulissat_fjord_temps_mod.pdf")

    # for s, temperate in enumerate(samples.numpy()):
    #     theta_ocean = temperate - melting_point_temperature(depth, salinity)
    #     ofile = f"ilulissat_fjord_theta_ocean_{s}_1980_2020.nc"
    #     create_nc(ofile, theta_ocean, grid_spacing, time_dict)

    class MultitaskGPModel(gpytorch.models.ExactGP):
        def __init__(self, train_x, train_y, likelihood, num_tasks):
            super(MultitaskGPModel, self).__init__(train_x, train_y, likelihood)
            self.mean_modules = [gpytorch.means.ConstantMean() for i in range(num_tasks)]
            self.covar_module = gpytorch.kernels.RBFKernel()

            # Surprisingly the Gram matrix of a rank-1 outer product appears to be sufficient
            # for parameterizing the inter-task covariance matrix, as increasing the rank
            # does not improved the fit.
            self.task_covar_module = gpytorch.kernels.IndexKernel(num_tasks=num_tasks, rank=1)

        def forward(self, x, i):
            # This is a hack that allows for different means to be queried when there are different task indices
            mean_x = torch.cat([self.mean_modules[ii](xx) for ii, xx in zip(i, x)])

            # Get input-input covariance
            covar_x = self.covar_module(x)
            # Get task-task covariance
            covar_i = self.task_covar_module(i)
            # Multiply the two together to get the covariance we want
            covar = covar_x.mul(covar_i)

            return gpytorch.distributions.MultivariateNormal(mean_x, covar)

    # Noise is just inferred from the data.  This is possible because there are multiple simultaneous
    # entries for some of the observations, and also because the different tasks are correlated.
    likelihood = gpytorch.likelihoods.GaussianLikelihood()

    data = {
        "GINR": {"X": X_ginr, "Y": T_ginr},
        "ICES": {"X": X_ices, "Y": T_ices},
        "OMG Bay": {"X": X_omg_bay, "Y": T_omg_bay},
        "OMG Fjord": {"X": X_omg_fjord, "Y": T_omg_fjord},
        "XCTD Fjord": {"X": X_xctd_fjord, "Y": T_xctd_fjord},
    }

    # Put them all together
    full_train_i = torch.cat(
        [torch.full_like(torch.tensor(data[d]["X"]), dtype=torch.long, fill_value=i) for i, d in enumerate(data)]
    )
    full_train_x = torch.cat([torch.tensor(data[d]["X"]).to(torch.float) for d in data])
    full_train_y = torch.cat([torch.tensor(data[d]["Y"]).to(torch.float) for d in data])

    # Here we have two iterms that we're passing in as train_inputs
    num_tasks = len(data)
    model = MultitaskGPModel((full_train_x, full_train_i), full_train_y, likelihood, num_tasks)

    training_iterations = 100

    # Find optimal model hyperparameters
    model.train()
    likelihood.train()

    # Use the adam optimizer
    optimizer = torch.optim.Adam(
        [
            {"params": model.parameters()},  # Includes GaussianLikelihood parameters
        ],
        lr=0.1,
    )

    # "Loss" for GPs - the marginal log likelihood
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    for i in range(training_iterations):
        optimizer.zero_grad()
        output = model(full_train_x, full_train_i)
        loss = -mll(output, full_train_y)
        loss.backward()
        print("Iter %d/50 - Loss: %.3f" % (i + 1, loss.item()))
        optimizer.step()

    # Set into eval mode
    model.eval()
    likelihood.eval()

    test_i = {d: torch.full_like(X_test, dtype=torch.long, fill_value=i) for (i, d) in enumerate(data)}

    # Make predictions - one task at a time
    # We control the task we cae about using the indices

    # The gpytorch.settings.fast_pred_var flag activates LOVE (for fast variances)
    # See https://arxiv.org/abs/1803.06058
    with torch.no_grad(), gpytorch.settings.fast_pred_var():
        Y_pred = {d: likelihood(model(X_test, test_i[d])) for d in test_i}
    omg_bay_col = "#08519c"
    ices_bay_col = "#6baed6"
    ginr_bay_col = "#c6dbef"
    ginr_ctd26_col = "#74c476"

    omg_fjord_col = "#54278f"
    xctd_fjord_col = "#9e9ac8"

    col_dict = {
        "OMG Bay": "#08519c",
        "ICES": "#6baed6",
        "GINR": "#c6dbef",
        "OMG Fjord": "#54278f",
        "OMG Bay": "#9e9ac8",
        "XCTD Fjord": "#9e9ac8",
    }
    ms = 5
    mew = 0.25

    # Initialize plot
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(12, 12)

    for k, v in Y_pred.items():
        ax.plot(X_test.numpy(), v.mean.numpy().T, color=col_dict[k], linewidth=0.75)

        lower, upper = v.confidence_region()
        ax.fill_between(X_test.numpy().squeeze(), lower.numpy(), upper.numpy(), color=col_dict[k], alpha=0.15)

        # plot the data and the true latent function
        ax.plot(data[k]["X"], data[k]["Y"], "o", color=col_dict[k], ms=ms, mec="k", mew=mew, label=k)
    # ax.plot(X_ices, T_ices, "o", color=ices_bay_col, ms=ms, mec="k", mew=mew, label="ICES (Disko Bay)")
    # ax.plot(X_ginr, T_ginr, "o", color=ginr_bay_col, ms=ms, mec="k", mew=mew, label="GINR (Disko Bay)")
    # ax.plot(X_ginr_ctd26, T_ginr_ctd26, "o", color=ginr_ctd26_col, ms=ms, mec="k", mew=mew, label="GINR (Station 26)")
    # # ax[0].plot(X_xctd_bay, T_xctd_bay, "o", color="#006d2c", mec="k", mew=mew, ms=ms, label="Mooring (Disko Bay)")
    # ax.plot(
    #     X_xctd_fjord, T_xctd_fjord, "o", color=xctd_fjord_col, ms=ms, mec="k", mew=mew, label="XCTD (Ilulissat Fjord)"
    # )
    # ax.plot(X_omg_fjord, T_omg_fjord, "o", color=omg_fjord_col, ms=ms, mec="k", mew=mew, label="OMG (Ilulissat Fjord)")

    # # ax.plot(X_test.numpy(), samples.numpy().T, color="k", linewidth=0.5)

    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (Celsius)")
    ax.set_xlim(1980, 2021)
    # ax.set_ylim(0, 5)
    plt.legend()
    fig.savefig("ilulissat_fjord_temps.pdf")

#!/usr/bin/env python3

"""run_filter.py

Run a flight data set through a filter and output a few simple plots
Author: Curtis L. Olson, University of Minnesota
"""

import argparse
import math
from matplotlib import pyplot as plt
import numpy as np
import os
import pandas as pd
from tqdm import tqdm

from flightdata import flight_loader, flight_interp

from insgnss_tools import nav_wrapper

# command line arguments
parser = argparse.ArgumentParser(description="nav filter")
parser.add_argument("flight", help="flight data log")
parser.add_argument("--gps-lag-sec", type=float, default=0.2,
                    help="gps lag (sec)")
args = parser.parse_args()

# constants
r2d = 180.0 / math.pi
d2r = math.pi / 180.0
gps_settle_secs = 10.0

# load the flight data
path = args.flight
data, flight_format = flight_loader.load(path)

print("imu records:", len(data["imu"]))
imu_dt = (data["imu"][-1]["timestamp"] - data["imu"][0]["timestamp"]) \
    / float(len(data["imu"]))
print("imu dt: %.3f" % imu_dt)
print("gps records:", len(data["gps"]))
if "air" in data:
    print("airdata records:", len(data["air"]))
if len(data["imu"]) == 0 and len(data["gps"]) == 0:
    print("not enough data loaded to continue.")
    quit()

# Default config
config_fixed_wing = {
    "sig_w_ax": 0.05,
    "sig_w_ay": 0.05,
    "sig_w_az": 0.05,
    "sig_w_gx": 0.00175,
    "sig_w_gy": 0.00175,
    "sig_w_gz": 0.00175,
    "sig_a_d": 0.01,
    "tau_a": 100.0,
    "sig_g_d": 0.00025,
    "tau_g": 50.0,
    "sig_gps_p_ne": 3.0,
    "sig_gps_p_d": 6.0,
    "sig_gps_v_ne": 0.5,
    "sig_gps_v_d": 1.0,
    "sig_mag": 1.0
}
config_quad = {
    # more trust in mags, higher vibration in accels
    "sig_w_ax": 0.2,
    "sig_w_ay": 0.2,
    "sig_w_az": 0.2,
    "sig_w_gx": 0.005,
    "sig_w_gy": 0.005,
    "sig_w_gz": 0.005,
    "sig_a_d": 0.01,
    "tau_a": 100.0,
    "sig_g_d": 0.00025,
    "tau_g": 50.0,
    "sig_gps_p_ne": 3.0,
    "sig_gps_p_d": 6.0,
    "sig_gps_v_ne": 0.5,
    "sig_gps_v_d": 1.0,
    "sig_mag": 0.2
}
config_sr22 = {
    "sig_w_ax": 0.5,
    "sig_w_ay": 0.5,
    "sig_w_az": 0.5,
    "sig_w_gx": 0.01,
    "sig_w_gy": 0.01,
    "sig_w_gz": 0.01,
    "sig_a_d": 0.01,
    "tau_a": 100.0,
    "sig_g_d": 0.00025,
    "tau_g": 50.0,
    "sig_gps_p_ne": 3.0,
    "sig_gps_p_d": 3.0,
    "sig_gps_v_ne": 0.3,
    "sig_gps_v_d": 0.3,
    "sig_mag": 1.0
}

# uNavINS default config
# config = {
#     "sig_w_ax": 0.05,
#     "sig_w_ay": 0.05,
#     "sig_w_az": 0.05,
#     "sig_w_gx": 0.00175,
#     "sig_w_gy": 0.00175,
#     "sig_w_gz": 0.00175,
#     "sig_a_d": 0.01,
#     "tau_a": 100.0,
#     "sig_g_d": 0.00025,
#     "tau_g": 50.0,
#     "sig_gps_p_ne": 3.0,
#     "sig_gps_p_d": 6.0,
#     "sig_gps_v_ne": 0.5,
#     "sig_gps_v_d": 1.0,
#     "sig_mag": 1.0
# }

# config = config_quad
# config = config_fixed_wing
config = config_sr22

# select filter
filter_name = "EKF15"
# filter_name = "EKF15_mag"
# filter_name = "uNavINS"
# filter_name = "uNavINS_BFS"
# filter_name = "pyNavEKF15"

filter = nav_wrapper.filter(nav=filter_name,
                            gps_lag_sec=args.gps_lag_sec,
                            imu_dt=imu_dt)
filter.set_config(config)

print("Running nav filter:")
results = []

gps_init_sec = None
gpspt = None
iter = flight_interp.IterateGroup(data)
for i in tqdm(range(iter.size())):
    record = iter.next()
    imupt = record["imu"]
    imupt["time_sec"] = imupt["timestamp"]
    if "gps" in record:
        gpspt = record["gps"]
        gpspt["time_sec"] = gpspt["timestamp"]
        if gps_init_sec is None:
            gps_init_sec = gpspt["timestamp"]

    # if not inited or gps not yet reached it's settle time
    if gps_init_sec is None or gpspt["time_sec"] < gps_init_sec + gps_settle_secs:
        continue

    navpt = filter.update(imupt, gpspt)

    # Store the desired results obtained from the compiled test
    # navigation filter and the baseline filter
    results.append(navpt)

# Plotting Section

plotname = os.path.basename(args.flight)

df0_gps = pd.DataFrame(data["gps"])
df0_gps.set_index("time_sec", inplace=True, drop=False)
df0_nav = pd.DataFrame(data["nav"])
df0_nav.set_index("timestamp", inplace=True, drop=False)

df1_nav = pd.DataFrame(results)
df1_nav.set_index("time_sec", inplace=True, drop=False)

r2d = np.rad2deg

# Attitude
att_fig, att_ax = plt.subplots(3, 1, sharex=True)

att_ax[0].set_title("Attitude Angles")
att_ax[0].set_ylabel("Roll (deg)", weight="bold")
att_ax[0].plot(df0_nav["phi_deg"], color="b", label="On Board")
att_ax[0].plot(df1_nav["phi_deg"], color="orange", label=filter.name)
att_ax[0].grid()

att_ax[1].set_ylabel("Pitch (deg)", weight="bold")
att_ax[1].plot(df0_nav["theta_deg"], color="b", label="On Board")
att_ax[1].plot(df1_nav["theta_deg"], color="orange", label=filter.name)
att_ax[1].grid()

att_ax[2].set_ylabel("Yaw (deg)", weight="bold")
att_ax[2].plot(df0_nav["psi_deg"], color="b", label="On Board")
att_ax[2].plot(df1_nav["psi_deg"], color="orange", label=filter.name)
att_ax[2].set_xlabel("Time (sec)", weight="bold")
att_ax[2].grid()
att_ax[2].legend(loc=1)

# Velocities
fig, [ax1, ax2, ax3] = plt.subplots(3,1, sharex=True)

# vn Plot
ax1.set_title("NED Velocities")
ax1.set_ylabel("vn (mps)", weight="bold")
ax1.plot(df0_gps["vn_mps"], "-*", label="GPS Sensor", c="g", alpha=.5)
ax1.plot(df0_nav["vn_mps"], color="b", label="On Board")
ax1.plot(df1_nav["vn_mps"], color="orange", label=filter.name)
ax1.grid()

# ve Plot
ax2.set_ylabel("ve (mps)", weight="bold")
ax2.plot(df0_gps["ve_mps"], "-*", label="GPS Sensor", c="g", alpha=.5)
ax2.plot(df0_nav["ve_mps"], color="b", label="On Board")
ax2.plot(df1_nav["ve_mps"], color="orange", label=filter.name)
ax2.grid()

# vd Plot
ax3.set_ylabel("vd (mps)", weight="bold")
ax3.plot(df0_gps["vd_mps"], "-*", label="GPS Sensor", c="g", alpha=.5)
ax3.plot(df0_nav["vd_mps"], color="b", label="On Board")
ax3.plot(df1_nav["vd_mps"], color="orange", label=filter.name)
ax3.set_xlabel("TIME (SECONDS)", weight="bold")
ax3.grid()
ax3.legend(loc=0)

# Altitude
plt.figure()
plt.title("Altitude")
plt.plot(df0_gps["altitude_m"], "-*", label="GPS Sensor", c="g", alpha=.5)
plt.plot(df0_nav["altitude_m"], color="b", label="On Board")
plt.plot(df1_nav["altitude_m"], color="orange", label=filter.name)
plt.ylabel("Altitude (m)", weight="bold")
plt.legend(loc=0)
plt.grid()

# Top down flight track plot
plt.figure()
plt.title("Ground track")
plt.ylabel("Latitude (degrees)", weight="bold")
plt.xlabel("Longitude (degrees)", weight="bold")
plt.plot(df0_gps["longitude_deg"], df0_gps["latitude_deg"], "*", label="GPS Sensor", c="g", alpha=.5)
plt.plot(df0_nav["longitude_deg"], df0_nav["latitude_deg"], color="b", label="On Board")
plt.plot(df1_nav["longitude_deg"], df1_nav["latitude_deg"], color="orange", label=filter.name)
plt.grid()
plt.legend(loc=0)
ax = plt.gca()
ax.axis("equal")

# Biases
bias_fig, bias_ax = plt.subplots(3,2, sharex=True)

# Gyro Biases
bias_ax[0,0].set_title("IMU Biases")
bias_ax[0,0].set_ylabel("p (deg/s)", weight="bold")
if "p_bias" in df0_nav:
    bias_ax[0,0].plot(r2d(df0_nav["p_bias"]), c="b", label="On Board")
bias_ax[0,0].plot(r2d(df1_nav["gbx"]), color="orange", label=filter.name)
bias_ax[0,0].set_xlabel("Time (secs)", weight="bold")
bias_ax[0,0].grid()

bias_ax[1,0].set_ylabel("q (deg/s)", weight="bold")
if "q_bias" in df0_nav:
    bias_ax[1,0].plot(r2d(df0_nav["q_bias"]), c="b", label="On Board")
bias_ax[1,0].plot(r2d(df1_nav["gby"]), color="orange", label=filter.name)
bias_ax[1,0].set_xlabel("Time (secs)", weight="bold")
bias_ax[1,0].grid()

bias_ax[2,0].set_ylabel("r (deg/s)", weight="bold")
if "r_bias" in df0_nav:
    bias_ax[2,0].plot(r2d(df0_nav["r_bias"]), c="b", label="On Board")
bias_ax[2,0].plot(r2d(df1_nav["gbz"]), color="orange", label=filter.name)
bias_ax[2,0].set_xlabel("Time (secs)", weight="bold")
bias_ax[2,0].grid()

# Accel Biases
bias_ax[0,1].set_title("Accel Biases")
bias_ax[0,1].set_ylabel("ax (m/s^2)", weight="bold")
if "ax_bias" in df0_nav:
    bias_ax[0,1].plot(df0_nav["ax_bias"], c="b", label="On Board")
bias_ax[0,1].plot(df1_nav["abx"], color="orange", label=filter.name)
bias_ax[0,1].set_xlabel("Time (secs)", weight="bold")
bias_ax[0,1].grid()

bias_ax[1,1].set_ylabel("ay (m/s^2)", weight="bold")
if "ay_bias" in df0_nav:
    bias_ax[1,1].plot(df0_nav["ay_bias"], c="b", label="On Board")
bias_ax[1,1].plot(df1_nav["aby"], color="orange", label=filter.name)
bias_ax[1,1].set_xlabel("Time (secs)", weight="bold")
bias_ax[1,1].grid()

bias_ax[2,1].set_ylabel("az (m/s^2)", weight="bold")
if "az_bias" in df0_nav:
    bias_ax[2,1].plot(df0_nav["az_bias"], c="b", label="On Board")
bias_ax[2,1].plot(df1_nav["abz"], color="orange", label=filter.name)
bias_ax[2,1].set_xlabel("Time (secs)", weight="bold")
bias_ax[2,1].grid()
bias_ax[2,1].legend(loc=1)

plt.show()

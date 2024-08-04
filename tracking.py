import requests
from sgp4.api import Satrec
from datetime import datetime, timezone, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from pytz import timezone as pytz_timezone
from timezonefinder import TimezoneFinder
from math import degrees, atan2, asin, sqrt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


# Function to get TLE data
def get_tle_data(norad_id):
    url = f"https://celestrak.com/NORAD/elements/gp.php?CATNR={norad_id}"
    response = requests.get(url)
    tle = response.text.strip().splitlines()
    print(f"TLE Data: {tle}")  # Debug: Print the TLE data
    return tle


# Function to validate TLE data
def validate_tle_data(tle_data):
    if len(tle_data) != 3:
        print("Invalid TLE format: Must have exactly 3 lines.")
        return False
    if len(tle_data[1]) != 69 or len(tle_data[2]) != 69:
        print("Invalid TLE format: Lines 2 and 3 must each be 69 characters long.")
        return False
    return True


# Function to calculate satellite position
def get_satellite_position(tle_data, observation_time):
    if not validate_tle_data(tle_data):
        print("TLE validation failed.")
        return None, None

    try:
        sat = Satrec.twoline2rv(tle_data[1], tle_data[2])
    except ValueError as e:
        print(f"Error creating satellite record: {e}")
        return None, None

    jd, fr = divmod(observation_time.timestamp() / 86400.0, 1)
    print(f"Julian Date: {jd + 2451545.0}, Fraction: {fr}")  # Debug: Print Julian date and fraction

    try:
        e, r, v = sat.sgp4(jd + 2451545.0, fr)
        print(f"SGP4 Error Code: {e}")  # Debug: Print the error code
        if e != 0:
            print("Error calculating position with SGP4.")
        print(f"Position Vector: {r}")  # Debug: Print the position vector
        print(f"Velocity Vector: {v}")  # Debug: Print the velocity vector

        if any(np.isnan(r)):
            print("Error: Position vector contains NaN values.")
        if any(np.isnan(v)):
            print("Error: Velocity vector contains NaN values.")

        return r, e
    except Exception as e:
        print(f"Exception during SGP4 calculation: {e}")
        return None, None


# Function to calculate ground track
def calculate_ground_track(tle_data, start_time, duration_minutes=90, step_seconds=60):
    ground_track = []
    sat = Satrec.twoline2rv(tle_data[1], tle_data[2])
    for minutes in range(0, duration_minutes, step_seconds // 60):
        observation_time = start_time + timedelta(seconds=minutes * 60)
        jd, fr = divmod(observation_time.timestamp() / 86400.0, 1)
        e, r, _ = sat.sgp4(jd + 2451545.0, fr)
        if e == 0:  # No error
            x, y, z = r
            lat = degrees(asin(z / sqrt(x ** 2 + y ** 2 + z ** 2)))
            lon = degrees(atan2(y, x))
            ground_track.append((lat, lon))
        else:
            print(f"SGP4 Error at {observation_time}")
            ground_track.append((None, None))
    return ground_track


# Function to plot satellite ground track and position using Cartopy
def plot_satellite(ground_track, current_position, observation_time):
    fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_title(f'Satellite Ground Track and Position on {observation_time} UTC')

    # Draw coastlines and countries
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS)

    # Plot the ground track
    lats, lons = zip(*ground_track)
    ax.plot(lons, lats, 'b-', label='Ground Track', transform=ccrs.Geodetic())  # Ground track in blue

    # Plot the satellite's current position
    lat, lon = current_position
    if lat is not None and lon is not None:
        ax.plot(lon, lat, 'ro', label='Current Position', transform=ccrs.Geodetic())  # Satellite position in red

    ax.legend()
    plt.show()


# Function to get the local timezone based on coordinates
def get_local_timezone(latitude, longitude):
    tf = TimezoneFinder()
    tz_str = tf.timezone_at(lat=latitude, lng=longitude)
    if tz_str:
        return pytz_timezone(tz_str)
    return timezone.utc


# Main function to track a satellite
def track_satellite(norad_id, observation_time=None, latitude=0, longitude=0):
    tle_data = get_tle_data(norad_id)
    if observation_time is None:
        observation_time = datetime.now(timezone.utc)
    else:
        local_tz = get_local_timezone(latitude, longitude)
        observation_time = local_tz.localize(observation_time).astimezone(timezone.utc)

    position, error = get_satellite_position(tle_data, observation_time)
    if error == 0:
        ground_track = calculate_ground_track(tle_data, observation_time)
        plot_satellite(ground_track,
                       (degrees(asin(position[2] / sqrt(position[0] ** 2 + position[1] ** 2 + position[2] ** 2))),
                        degrees(atan2(position[1], position[0]))), observation_time)
    else:
        print("Failed to calculate satellite position.")


# Example usage:
if __name__ == "__main__":
    norad_id = 25338  # NOAA 15 (or use 25544 for ISS)
    observation_time = datetime(2024, 8, 4, 12, 0, 0)  # Specify in local time if needed
    latitude = 37.7749  # Example: San Francisco
    longitude = -122.4194
    track_satellite(norad_id, observation_time, latitude, longitude)

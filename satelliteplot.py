#!/usr/bin/env python3
# coding: utf-8

"""Plot satellite pass"""

from datetime import datetime, timedelta

import astropy.units as u
import ephem
import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from argparse import ArgumentParser
import json
import requests


NUM_STEPS = 237

dwl = ephem.Observer()
dwl.lat = np.deg2rad(52.8122)

url = "https://www.camras.nl/pointing.php"
pointing_info = json.loads(requests.get(url).text)

dwl.lon = np.deg2rad(6.3964)
dwl.elevation = 80
dwl_pointing = ((180 + pointing_info['az']) * u.deg, pointing_info['el'] * u.deg)


def get_sat(norad_id):
    if int(norad_id) ==  99489:
        tle = """Delfi-PQ
1 99489U          22013.68438100  .00000000  00000-0  57534-2 0    06
2 99489  97.5121  83.3548 0000001  54.9139 307.6602 15.14117915    08"""
    elif int(norad_id) == 99488:
        tle = """Grizu-263A
1 70303C 22002C   22013.68476757  .00096032  00000-0  54126-2 0    00
2 70303  97.5255  83.3610 0014130 234.0040 130.5308 15.13159474    12"""
    else:
        url = f"https://celestrak.com/satcat/tle.php?CATNR={norad_id}"
        response = requests.get(url)
        tle = response.text
    sat = ephem.readtle(*tle.splitlines())
    return sat

def get_sat(norad_id):
    url = f"https://db.satnogs.org/api/tle/?norad_cat_id={norad_id}"
    response = requests.get(url, verify=False)
    response.raise_for_status()
    if response.text == "[]":
        raise RuntimeError(f"Satnogs has no tle for {norad_id} at {url}")
    data = json.loads(response.text)[0]
    sat = ephem.readtle(data['tle0'], data['tle1'], data['tle2'])
    return sat

def make_figure(
    az_list,
    alt_list,
    rise_azimuth,
    set_azimuth,
    closest_time,
    closest_separation,
    closest_index,
    dwl_pointing=dwl_pointing,
):
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(az_list, np.pi / 2 - np.array(alt_list), "k")
    ax.scatter(
        np.deg2rad(dwl_pointing[0].to(u.deg).value),
        np.deg2rad(90 - dwl_pointing[1].to(u.deg).value),
        edgecolors="k",
        facecolors="w",
        label="Telescope pointing",
    )
    ax.plot([rise_azimuth], [np.pi / 2], "o", color="lime", clip_on=False)
    ax.plot([set_azimuth], [np.pi / 2], "o", color="red", clip_on=False)
    if az_list[closest_index] < np.pi:
        textalignment = 'right'
    else:
        textalignment = 'left'
    ax.text(-0.03, 1, f"{closest_separation.deg:.1f}˚ from pointing\nat {closest_time:%H:%M:%S}", transform=ax.transAxes)
    #ax.text(
    #    az_list[closest_index],
    #    np.pi / 2 - alt_list[closest_index],
    #    f"{closest_separation.deg:.0f}˚ from pointing\nat {closest_time:%H:%M:%S}",
    #    ha=textalignment,
    #    bbox=dict(facecolor="white", edgecolor="none", alpha=0.8)
    #)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rmax(np.pi / 2)
    ax.set_rticks(np.pi / 2 * np.array([0.33, 0.66, 1]))
    ax.set_yticklabels([])  # ["90˚","60˚","30˚"])
    ax.set_xticks(2 * np.pi * np.array([0, 1 / 4, 1 / 2, 3 / 4]))
    ax.set_xticklabels(["N", "E", "S", "W"])
    ax.set_rlabel_position(0)
    ax.set_axisbelow(True)
    return fig, ax



def main(norad_id, filename, time=None, do_make_figure=True):
    if time is None:
        time = datetime.utcnow() - timedelta(hours=1)
    else:
        time = time - timedelta(minutes=15) # The exact rise time is probably too strict
    sat = get_sat(norad_id)
    dwl.date = time
    (
        rise_time,
        rise_azimuth,
        max_alt_time,
        max_alt,
        set_time,
        set_azimuth,
    ) = dwl.next_pass(sat)
    az_list = []
    alt_list = []
    times = np.linspace(rise_time, set_time, NUM_STEPS)
    for t in times:
        dwl.date = t
        sat.compute(dwl)
        az_list.append(sat.az)
        alt_list.append(sat.alt)

    sat_astropy = SkyCoord(ra=np.array(az_list) * u.rad, dec=np.array(alt_list) * u.rad)
    pointing_astropy = SkyCoord(ra=dwl_pointing[0], dec=dwl_pointing[1])
    separations = sat_astropy.separation(pointing_astropy)
    closest_index = np.argmin(separations)
    closest_time = ephem.date(times[closest_index]).datetime()
    closest_separation = separations[closest_index]
    if do_make_figure:
        fig, ax = make_figure(
            az_list,
            alt_list,
            rise_azimuth,
            set_azimuth,
            closest_time,
            closest_separation,
            closest_index,
        )
        fig.savefig(filename, facecolor="white", bbox_inches="tight")
    return closest_time, closest_separation.deg

if __name__ == "__main__":
    parser = ArgumentParser(description="Create satellite plot (of satellite starting an hour ago)")
    parser.add_argument("norad_id", help="Norad ID of satellite to plot")
    parser.add_argument("--filename", "-f", help="Location where to save plot (default /tmp/sat.png)", default="/tmp/sat.png")
    args = parser.parse_args()
    main(args.norad_id, args.filename)

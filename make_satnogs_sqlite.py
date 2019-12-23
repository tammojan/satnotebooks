#!/usr/bin/env python

import sqlite3
import requests


DB_BASE_URL = "https://db.satnogs.org"
NETWORK_BASE_URL = "https://network.satnogs.org"

def create_connection(db_file):
    """ Create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
        raise
    return conn
 
def create_tables(conn):
    cur = conn.cursor()
    cur.execute("""
CREATE TABLE IF NOT EXISTS 'transmitters' (
        "uuid" TEXT PRIMARY KEY,
        "description" TEXT,
        "alive" TEXT,
        "type" TEXT,
        "uplink_low" INTEGER,
        "uplink_high" INTEGER,
        "uplink_drift" INTEGER,
        "downlink_low" INTEGER,
        "downlink_high" INTEGER,
        "downlink_drift" INTEGER,
        "mode" TEXT,
        "mode_id" INTEGER,
        "uplink_mode" TEXT,
        "invert" TEXT,
        "baud" REAL,
        "norad_cat_id" INTEGER,
        "status" TEXT,
        "updated" TEXT,
        "citation" TEXT,
        "service" TEXT);
""")
    cur.execute("""
CREATE TABLE IF NOT EXISTS 'satellites' (
        "norad_cat_id" INTEGER NOT NULL PRIMARY KEY,
        "name" TEXT,
        "names" TEXT,
        "image" TEXT,
        "status" TEXT,
        "decayed" TEXT,
        "telemetries" TEXT);
""")
    cur.execute("""
CREATE TABLE IF NOT EXISTS 'transmitter_stats' (
        "uuid" TEXT NOT NULL PRIMARY KEY,
        "sync_to_db" TEXT,
        "bad_count" INTEGER,
        "unvetted_rate" INTEGER,
        "good_count" INTEGER,
        "future_count" INTEGER,
        "total_count" INTEGER,
        "bad_rate" INTEGER,
        "unvetted_count" INTEGER,
        "future_rate" INTEGER,
        "success_rate" INTEGER);
""")

def get_paginated_endpoint(url, max_entries=None):
    r = requests.get(url=url)
    r.raise_for_status()

    data = r.json()

    while 'next' in r.links and (not max_entries or len(data) < max_entries):
        next_page_url = r.links['next']['url']

        r = requests.get(url=next_page_url)
        r.raise_for_status()

        data.extend(r.json())

    return data

def add_quotes(inp):
    if type(inp) in (bool,str):
        return '"' + str(inp) + '"'
    elif inp is None:
        return "NULL"
    elif type(inp) is list:
        if len(inp) == 0:
            return "NULL"
        else:
            return '"' + ", ".join([inp[0][key] for key in inp[0]]) + '"'
    else:
        return inp

def fill_transmitters(conn):
    r = requests.get(f'{DB_BASE_URL}/api/transmitters')
    cur = conn.cursor()
    for o in r.json():
        columns = ", ".join([key for key in o])
        values = ", ".join([f"{add_quotes(o[key])}" for key in o])
        query = f"INSERT INTO transmitters ({columns}) VALUES ({values});"
        cur.execute(query)

def fill_satellites(conn):
    r = requests.get(f'{DB_BASE_URL}/api/satellites')
    cur = conn.cursor()
    for o in r.json():
        columns = ", ".join([key for key in o])
        values = ", ".join([f"{add_quotes(o[key])}" for key in o])
        query = f"INSERT INTO satellites ({columns}) VALUES ({values});"
        cur.execute(query)

def fill_transmitter_stats(conn):
    data = get_paginated_endpoint(f'{NETWORK_BASE_URL}/api/transmitters')
    cur = conn.cursor()
    for o in data:
        columns = ", ".join([key for key in o if key != "stats"])
        columns += ", " + ", ".join([key for key in o['stats']])
        values = ", ".join([f"{add_quotes(o[key])}" for key in o if key != "stats"])
        values += ", " + ", ".join([f"{add_quotes(o['stats'][key])}" for key in o['stats']])
        query = f"INSERT INTO transmitter_stats ({columns}) VALUES ({values});"
        cur.execute(query)

if __name__ == '__main__':
    conn = create_connection("mysatnogs.sqlite")
    with conn:
        create_tables(conn)
        #fill_transmitters(conn)
        #fill_satellites(conn)
        fill_transmitter_stats(conn)

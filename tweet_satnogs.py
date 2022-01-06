#!/usr/bin/env python3
"""Post waterfall observed through SatNOGS to Twitter

usage: tweet_satnogs.py OBS_ID [SLEEP_TIME] [DRY_RUN]

E.g. 'tweet_satnogs.py 1414012 0 -d' for dry run
E.g. 'tweet_satnogs.py 1414012' for the real thing
"""

import time
from os import path
from glob import glob
import sys
from typing import Dict, Any
from satelliteplot import main as satelliteplot
from argparse import ArgumentParser
from typing import List

import tweepy
import requests



CONSUMER_KEY = None
CONSUMER_SECRET = None
ACCESS_TOKEN = None
ACCESS_TOKEN_SECRET = None
WATERFALL_PATH = "/home/user/satnogs/uhf/data/complete/"


def post_tweet(tweet_text: str, image_paths: List[str]) -> None:
    """Post tweet with image using tweepy"""
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    media_ids = []
    for image_path in image_paths:
        res = api.media_upload(image_path)
        media_ids.append(res.media_id)

    ret = api.update_status(status=tweet_text, media_ids=media_ids)


def get_observation(obsid: str) -> Dict[str, Any]:
    """Get observation dict from SatNOGS observations API"""
    client = requests.session()
    url = f"https://network.satnogs.org/api/observations/?id={obsid}"
    res = client.get(url)

    obs = res.json()[0]
    return obs


def get_satellite(norad_cat_id: str) -> Dict[str, Any]:
    """Get satellite dict from SatNOGS satellites API"""
    client = requests.session()
    url = f"https://db.satnogs.org/api/satellites/?norad_cat_id={norad_cat_id}"
    res = client.get(url)

    sat = res.json()[0]
    return sat


def main(obsid: str, sleeptime: int = 180, dry_run: bool = False):
    """
    Post waterfall observed through SatNOGS to Twitter

    Args:
        obsid: SatNOGS observation ID (e.g. 1414012)
        sleeptime: Time to sleep before looking for waterfall (necessary
                   when used as post observation hook in SatNOGS)
    """
    tracking = True
    try:
        from telescope import Telescope
        dt = Telescope(consoleHost="console")
        time.sleep(5)
        if not dt.is_connected():
            tracking = False
    except:
        tracking = False
    
    time.sleep(sleeptime)

    attempts = 0
    while attempts < 3: # Waterfall takes a while to get generated
        try:
            waterfall_glob = path.join(WATERFALL_PATH, f"waterfall_{obsid}_*.png")
            waterfall_path = glob(waterfall_glob)[0]
            break
        except IndexError:
            attempts += 1
            time.sleep(60)
            if attempts == 3:
                raise RuntimeError(f"Could not find waterfall path at {waterfall_glob}")

    obs = get_observation(obsid)
    sat = get_satellite(obs['norad_cat_id'])

    tweet_text = f"The Dwingeloo @radiotelescoop just observed the satellite {sat['name']} "
    tweet_text += "as a @SatNOGS ground station"
    
    if tracking:
        tweet_text += ". "
    else:
        tweet_text += ", without tracking the satellite. "

    if len(obs['demoddata']) > 0:
        tweet_text += f"The software demodulated {len(obs['demoddata'])} "
        tweet_text += f"{obs['transmitter_description']} packets. "

    tweet_text += f"View the results at https://network.satnogs.org/observations/{obsid}."

    print(tweet_text)

    if len(tweet_text) > 279:
        raise RuntimeError(f"Tweet became too long, it would have been {tweet_text}")

    if not dry_run:
        filenames = [waterfall_path]
        if not tracking:
            satelliteplot(int(obs['norad_cat_id']), f"/tmp/satplot_{obsid}.png")
            filenames.append(f"/tmp/satplot_{obsid}.png")
        post_tweet(tweet_text, filenames) 


if __name__ == "__main__":
    parser = ArgumentParser(description="Tweet SatNOGS observation")
    parser.add_argument("obsid", help="Observation ID")
    parser.add_argument("-s", "--sleeptime", help="Sleep time in seconds (default 180)", default=180, type=int)
    parser.add_argument("-d", "--dry_run", help="Dry run", action="store_true", default=False)
    args = parser.parse_args()
    main(args.obsid, sleeptime=args.sleeptime, dry_run=args.dry_run)

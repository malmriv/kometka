"""kometka [--once | --restore]

Without options: one pass on start (unless RUN_ON_START=false), then one every day at SCHEDULE.
"""
import argparse
import datetime
import logging
import os
import sys
import time

from . import __version__
from .config import Config, ConfigError
from .jellyfin import Jellyfin
from .mdblist import MDBList
from .runner import State, restore, run_pass

log = logging.getLogger("kometka")


def seconds_until(hhmm):
    hour, minute = map(int, hhmm.split(":"))
    now = datetime.datetime.now()
    nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if nxt <= now:
        nxt += datetime.timedelta(days=1)
    return (nxt - now).total_seconds()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kometka", description=__doc__.splitlines()[2])
    parser.add_argument("--once", action="store_true", help="run a single pass and exit")
    parser.add_argument("--restore", action="store_true", help="put the original posters back and exit")
    parser.add_argument("--version", action="version", version="kometka " + __version__)
    args = parser.parse_args(argv)

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    try:
        cfg = Config.from_env()
    except (ConfigError, OSError) as e:
        log.error("%s", e)
        return 2

    os.makedirs(cfg.data_dir, exist_ok=True)
    jf, mdb = Jellyfin(cfg.jellyfin_url, cfg.jellyfin_api_key), MDBList(cfg.mdblist_api_key)
    state = State(os.path.join(cfg.data_dir, "state.json"))
    log.info("kometka %s, Jellyfin at %s, sources: %s", __version__, cfg.jellyfin_url, ", ".join(cfg.sources))

    if args.restore:
        restore(cfg, jf, state)
        return 0

    first = True
    while True:
        if not first or cfg.run_on_start or args.once:
            try:
                run_pass(cfg, jf, mdb, state)
            except Exception as e:
                log.error("Pass failed: %s", e)
        if args.once:
            return 0
        first = False
        wait = seconds_until(cfg.schedule)
        log.info("Next pass at %s (in %.1f h)", cfg.schedule, wait / 3600)
        time.sleep(wait)


if __name__ == "__main__":
    sys.exit(main())

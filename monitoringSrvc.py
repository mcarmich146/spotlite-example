# Copyright (c) 2023 Satellogic USA Inc. All Rights Reserved.
#
# This file is part of Spotlite.
#
# This file is subject to the terms and conditions defined in the file 'LICENSE',
# which is part of this source code package.

"""Monitors subscriptions and loops over subscription AOIs to find new images."""

import time
import schedule
import config
import logging
from datetime import datetime

from subscriptionUtils import check_and_notify  # Assuming check_and_notify is in subscManager.py

def monitor_subscriptions():
    """This function will be called periodically."""
    check_and_notify()
    print(f"\nSearch Will Run Again In {config.SUBC_MON_FREQUENCY} Minutes.")

def main():
    """Runs a recurring search of the subscription areas."""
    # Setup Logging
    now = datetime.now().strftime("%d-%m-%YT%H%M%S")
    logging.basicConfig(filename=f"log/UserApp-{now}.txt", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # Add StreamHandler to log to console as well
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)

    # Run the search right away to help with debugging.
    monitor_subscriptions()

    # Set up the period for the monitor.
    schedule.every(config.SUBC_MON_FREQUENCY).minutes.do(monitor_subscriptions)

    # Keep running the schedule in a loop
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

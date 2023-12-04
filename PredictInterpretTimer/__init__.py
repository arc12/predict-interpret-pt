import logging
import requests
from os import environ

import azure.functions as func

from predict_interpret import PLAYTHING_NAME, core

def main(mytimer: func.TimerRequest) -> None:
    if core.keep_warm:
        if mytimer.past_due:
            logging.info('The timer is past due!')
        
        url_base = environ.get("PLAYGROUND_PING_URL_BASE", None)  # e.g. = "https://dlpg-test1.azurewebsites.net"

        if url_base is None:
            logging.warn(f"Environ PLAYGROUND_PING_URL_BASE is not set; abort pinging {PLAYTHING_NAME}.")
        else:
            url = f"{url_base}/{PLAYTHING_NAME}/ping"
            try:
                req = requests.get(url, timeout=10)
                logging.info(f"Ping {url} from timerTrigger => HTTP {req.status_code}, Content: {req.text}")
            except requests.exceptions.ConnectTimeout:
                logging.warn("Request to {url} from timerTrigger timed out.")
                exit(1)


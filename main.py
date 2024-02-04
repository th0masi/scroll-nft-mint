import random
import time

from core.mint import Mint
from core.utils import write_to_failed_wallets, load_from_file
from data.config import DELAY_BETWEEN_ACCOUNT

if __name__ == '__main__':
    key_list = load_from_file("data/private_keys.txt")
    proxy_list = load_from_file("data/proxies.txt")

    for key, proxy in zip(key_list, proxy_list):
        action = Mint(
            key=key,
            proxy=proxy,
        )

        status, is_sleep = action.mint()

        if not status:
            write_to_failed_wallets("data/failed_wallets.txt", key)

        if is_sleep:
            time.sleep(random.uniform(*DELAY_BETWEEN_ACCOUNT))

import functools
import os
import re
import time

from data.config import MAX_GWEI
from eth_account import Account
from loguru import logger
import json
from pathlib import Path

from web3 import Web3


def load_json(filepath: Path | str):
    with open(filepath, "r") as file:
        return json.load(file)


def load_from_file(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.error(f"Ошибка: файл не найден – {file_path}")
        exit()


def get_address_wallet(private_key: str):
    """Получает адрес кошелька из приватного ключа"""
    if private_key.startswith("0x"):
        private_key = private_key[2:]

    if not re.match(r"^[0-9a-fA-F]{64}$", private_key):
        raise ValueError("Неверный формат приватных ключей")
    account = Account.from_key(private_key)
    return account.address


def write_to_failed_wallets(file_path, wallet_key):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "a") as file:
        file.write(wallet_key + "\n")


def gas_control(func):
    @functools.wraps(func)
    def wrapper_retry(*args, **kwargs):
        while True:
            _, current_gas = get_gas_price()

            if current_gas > MAX_GWEI:
                logger.warning(f"Текущий газ в сети {round(current_gas, 2)} GWEI")
                time.sleep(300)
            else:
                logger.info(f"Текущий газ в сети {round(current_gas, 2)} GWEI")
                break

        return func(*args, **kwargs)

    return wrapper_retry


def get_gas_price():
    w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth'))
    price_wei = w3.eth.gas_price
    price = w3.from_wei(price_wei, "gwei")
    return price_wei, price

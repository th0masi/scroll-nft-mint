import json
import random

from core.utils import get_address_wallet, load_json, gas_control
from loguru import logger
from pyuseragents import random as random_useragent
import time
from web3 import Web3, exceptions
import requests


class Mint:
    def __init__(self, key, proxy):
        self.key = key
        self.address = get_address_wallet(self.key)
        self.w3 = Web3(Web3.HTTPProvider('https://1rpc.io/scroll'))
        self.contract_address = self.w3.to_checksum_address(
            '0x74670a3998d9d6622e32d0847ff5977c37e0ec91'
        )
        self.timestamp = int(time.time() * 1000)
        self.proxy = {
                    "http":  f"http://{proxy}",
                    "https": f"http://{proxy}"
                }
        self.ABI = load_json("core/abi/mint.json")
        self.multiplier = 1.1
        self.nonce = self.w3.eth.get_transaction_count(self.address)

    @gas_control
    def mint(self, status=False, is_sleep=True):
        if self.nonce < 1:
            logger.warning(f'{self.address} | На кошельке нет транзакций!')
            return is_sleep, status

        nft_balance = self.get_balance_nft()

        if nft_balance > 0:
            logger.success(f'{self.address} | На балансе уже есть сминченная NFT')
            return is_sleep, status

        balance, balance_wei = self.get_balance()

        if balance < 0.0006:
            logger.error(f'{self.address} | Недостаточный баланс нативок.'
                         f' Баланс: {round(balance, 5)} $ETH')
            return status, is_sleep

        try:
            response = self.send_request()

            if response.status_code != 200:
                logger.info(f'{self.address} | Неккоректный ответ от сервера: {response.text}')
                return status, is_sleep

            data = json.loads(response.text)
            status = self.send_tx(data)

        except Exception as e:
            logger.info(f'{self.address} | Возникла ошибка: {e}')

        finally:
            return status, is_sleep

    def send_request(self):
        headers = self.get_headers()
        url_ = (f'https://nft.scroll.io/p/{self.address}.json?'
                f'timestamp={self.timestamp}')

        response = requests.get(
            url=url_,
            headers=headers,
            proxies=self.proxy
        )

        return response

    @staticmethod
    def get_headers():
        base_headers = {
            "Content-Type"  : 'application/json',
            "User-Agent"    : random_useragent(),
            "origin"    : 'https://scroll.io',
            "referer"   : 'https://scroll.io/',
            }

        return base_headers

    def get_balance(self):
        balance_wei = self.w3.eth.get_balance(self.w3.to_checksum_address(self.address))
        balance = balance_wei / 10 ** 18

        return balance, balance_wei

    def get_balance_nft(self):
        try:
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=self.ABI
            )

            balance = contract.functions.balanceOf(
                self.address
            ).call()

            return balance
        except Exception as e:
            logger.error(f'{self.address} | Ошибка {e}')
            return 0

    def send_tx(self, data):
        try:
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=self.ABI
            )

            metadata = data.get('metadata', {})
            proof = data.get('proof', [])

            tuple_argument = (
                self.address,
                metadata.get('firstDeployedContract'),
                metadata.get('bestDeployedContract'),
                int(metadata.get('rarityData'), 16)
            )

            mint_txn = contract.functions.mint(
                self.address,
                tuple_argument,
                proof
            )

            params = {
                'from': self.address,
                'gasPrice': int(self.w3.eth.gas_price * 1.1),
                'nonce': self.w3.eth.get_transaction_count(self.address)
            }

            mint_txn = mint_txn.build_transaction(params)

            status, hash_ = self.sign_message(mint_txn)

            if status:
                logger.success(f'{self.address} | Успешно заминтил NFT\n'
                               f'>>> https://scrollscan.com/tx/{hash_}')

            return status
        except Exception as e:
            logger.error(f'{self.address} | Ошибка {e}')

    def sign_message(
            self,
            mint_txn
    ):
        gas_estimate = int(
            self.w3.eth.estimate_gas(mint_txn) * random.uniform(1.07, 1.08)
        )

        mint_txn["gas"] = gas_estimate

        signed_msg = self.w3.eth.account.sign_transaction(mint_txn, self.key)
        hash_ = self.w3.eth.send_raw_transaction(signed_msg.rawTransaction)
        hex_hash = self.w3.to_hex(hash_)
        status = self.check_transaction_status(hex_hash)

        return status, hex_hash

    def check_transaction_status(
            self,
            hash_: hash,
            timeout: int = 720,
            interval_: int = 60
    ):
        total_wait_time = 0

        while total_wait_time < timeout:
            try:
                tx_receipt = self.w3.eth.get_transaction_receipt(hash_)

                if tx_receipt is None:
                    time.sleep(interval_)
                    total_wait_time += interval_
                else:
                    if tx_receipt["status"] == 1:
                        return True
                    elif tx_receipt["status"] == 0:
                        return False
                    else:
                        time.sleep(interval_)
                        total_wait_time += interval_

            except exceptions.TransactionNotFound:
                time.sleep(interval_)
                total_wait_time += interval_

            except Exception as e:
                raise Exception(f'при проверки статуса транзакции: {e}')

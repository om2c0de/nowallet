#! /usr/bin/env python3

import sys, io, asyncio, random, decimal, collections, getpass

from connectrum.client import StratumClient
from pycoin.key.BIP32Node import BIP32Node
from pycoin.ui import standard_tx_out_script
from pycoin.tx.Tx import Tx
from pycoin.tx.TxOut import TxOut
from pycoin.tx.tx_utils import distribute_from_split_pool, sign_tx

from subclasses import MyServerInfo, LexSpendable, LexTxOut
from keys import derive_key
from scrape import scrape_onion_servers

class Connection:
    def __init__(self, loop, server, port):
        """
        Connection object constructor. Connects to an Electrum server.

        :param loop: an asyncio event loop
        :param server: a string containing a hostname
        :param port: port number that the server listens on
        :returns: A new Connection object
        """
        print("Connecting...")

        self.server_info = MyServerInfo(server, hostname=server, ports=port)
        print(self.server_info.get_port("t"))
        self.client = StratumClient()
        self.connection = self.client.connect(
                            self.server_info,
                            proto_code="t",
                            use_tor=self.server_info.is_onion,
                            disable_cert_verify=True)

        loop.run_until_complete(self._do_connect())
        self.queue = None

    async def _do_connect(self):
        """
        Coroutine. Establishes a persistent connection to an Electrum server.
        Awaits the connection because AFAIK an init method can't be async.
        """
        try:
            await self.connection
        except Exception as e:
            print("Unable to connect to server:", e)
            sys.exit(1)

        print("\nConnected to server")

    async def listen_RPC(self, method, args):
        """
        Coroutine. Sends a normal RPC message to the server and awaits response.

        :param method: The Electrum API method to use
        :param args: Params associated with current method
        :returns: Future. Response from server for this method(args)
        """
        return await self.client.RPC(method, *args)

    def listen_subscribe(self, method, args):
        """
        Coroutine. Sends a "subscribe" message to the server and 
        adds to the queue

        :param method: The Electrum API method to use
        :param args: Params associated with current method
        :returns: Future. Immediate response from server,
                    Queue, new queue that will listen for more 
                    responses associated with this method(args)
        """
        future, self.queue = self.client.subscribe(method, *args)

    async def consume_queue(self, queue_func):
        """
        Coroutine. Infinite loop that consumes the current subscription queue.

        :param queue_func: A function to call when new responses arrive
        """
        while True:
            result = await self.queue.get()
            await queue_func(result)

Chain = collections.namedtuple("Chain", ["netcode", "chain_1209k", "bip44"])
BTC = Chain(netcode="BTC",
            chain_1209k="btc",
            bip44=0)
TBTC = Chain(netcode="XTN",
            chain_1209k="tbtc",
            bip44=1)

class Wallet:
    """
    Provides all functionality required for a fully functional and secure
    HD brainwallet based on the Warpwallet technique.
    """
    _COIN = 100000000
    _GAP_LIMIT = 20

    def __init__(self, salt, passphrase, connection, loop, chain, account=0):
        """
        Wallet object constructor. Use discover_keys() and listen_to_addresses()
        coroutine method to construct wallet data, and listen for new data from
        the server.

        :param salt: a string to use as a salt for key derivation
        :param passphrase: a string containing a secure passphrase
        :param connection: a Connection object
        :param loop: an asyncio event loop
        :param chain: a namedtuple containing chain-specific info
        :param account: account number, defaults to 0
        :returns: A new, empty Wallet object
        """
        self.connection = connection
        self.loop = loop
        self.chain = chain

        (se, cc) = derive_key(salt, passphrase)
        self.mpk = BIP32Node(netcode=self.chain.netcode,
                                chain_code=cc, secret_exponent=se)
        path = "44H/{}H/{}H/".format(chain.bip44, account)
        self.root_spend_key = self.mpk.subkey_for_path("{}0".format(path))
        self.root_change_key = self.mpk.subkey_for_path("{}1".format(path))
        self.balance = decimal.Decimal("0")

        # Boolean lists, True = used / False = unused
        self.spend_indicies = list()
        self.change_indicies = list()

        # All wallet TX info. (Does not persist!)
        self.utxos = list()
        self.history = dict()
        self.result_cache = dict()

    def get_xpub(self):
        """
        Returns the wallet's extended public key.

        :returns: a string containing the wallet's XPUB.
        """
        return self.mpk.hwif()

    def get_key(self, index, change=False):
        """
        Returns a specified pycoin.key object.

        :param index: The index of the desired key
        :param change: a boolean indicating which key root to use
        :returns: a key object associated with the given index
        """
        if change:
            return self.root_change_key.subkey(index)
        else:
            return self.root_spend_key.subkey(index)

    def get_next_unused_key(self, change=False):
        """
        Returns the next unused key object in the sequence.

        :param change: a boolean indicating which key root to use
        :returns: a key object associated with the next unused index
        """
        indicies = self.change_indicies if change else self.spend_indicies
        for i, is_used in enumerate(indicies):
            if not is_used:
                return self.get_key(i, change)

    def get_all_known_addresses(self, change=False):
        """
        Returns a list of all addresses currently known to us.

        :param change: a boolean indicating which key root to use
        :returns: a list of address strings containing all addresses known
                    for the given root
        """
        indicies = self.change_indicies if change else self.spend_indicies
        addrs = [self.get_key(i, change).address()
                for i in range(len(indicies))]
        return addrs

    def get_all_used_addresses(self):
        return list(self.history.keys())

    async def _get_history(self, txids):
        method = "blockchain.transaction.get"
        results = list()
        for txid in txids:
            results.append(await self.connection.listen_RPC(method, [txid]))
        txs = [Tx.from_hex(tx_hex) for tx_hex in results]
        return txs

    async def _get_balance(self, address):
        method = "blockchain.address.get_balance"
        result = await self.connection.listen_RPC(method, [address])
        return decimal.Decimal(str(result["confirmed"])) / Wallet._COIN

    async def _get_utxos(self, address):
        method = "blockchain.address.listunspent"
        result = await self.connection.listen_RPC(method, [address])
        utxos = list()
        for unspent in result:
            method = "blockchain.transaction.get"
            txid = unspent["tx_hash"]
            vout = unspent["tx_pos"]
            result = await self.connection.listen_RPC(method, [txid])
            spendables = Tx.from_hex(result).tx_outs_as_spendable()
            utxos.append(spendables[vout])
        return utxos

    def _interpret_history(self, histories, change=False):
        indicies = self.change_indicies if change else self.spend_indicies
        is_empty = True
        for history in histories:
            if history:
                address = self.get_key(len(indicies), change).address()
                txids = [history[i]["tx_hash"] for i in range(len(history))]

                self.history[address] = self.loop.run_until_complete(
                                            self._get_history(txids))
                self.balance += self.loop.run_until_complete(
                                            self._get_balance(address))
                self.utxos.extend(self.loop.run_until_complete(
                                            self._get_utxos(address)))

                indicies.append(True)
                is_empty = False
            else:
                indicies.append(False)
        return is_empty

    async def _interpret_new_history(self, address, history, change=False):
        indicies = self.change_indicies if change else self.spend_indicies
        is_empty = True
        if history:
            txid = history["tx_hash"]

            new_history = await self._get_history([txid])
            if address in self.history:
                self.history[address].extend(new_history)
            else:
                self.history[address] = new_history
            self.balance += await self._get_balance(address)
            self.utxos.extend(await self._get_utxos(address))

            for i, used in enumerate(indicies):
                if self.get_key(i, change).address() == address:
                    indicies[i] = True
                    break
            else:
                indicies.append(True)
            is_empty = False
        return is_empty

    def discover_keys(self, change=False):
        method = "blockchain.address.get_history"
        current_index = 0
        quit_flag = False
        while not quit_flag:
            futures = list()
            for i in range(current_index, current_index + Wallet._GAP_LIMIT):
                addr = self.get_key(i, change).address()
                futures.append(self.connection.listen_RPC(method, [addr]))

            result = self.loop.run_until_complete(asyncio.gather(*futures))
            quit_flag = self._interpret_history(result, change)
            current_index += Wallet._GAP_LIMIT
        self.new_history = True

    async def listen_to_addresses(self):
        method = "blockchain.address.subscribe"
        addrs = self.get_all_known_addresses()
        for addr in addrs:
            self.connection.listen_subscribe(method, [addr])

        await self.connection.consume_queue(self.dispatch_result)

    async def dispatch_result(self, result):
        addr = result[0]
        method = "blockchain.address.get_history"
        history = await self.connection.listen_RPC(method, [addr])
        empty_flag = await self._interpret_new_history(addr, history[0])
        if not empty_flag:
            self.new_history = True

    def get_fee(self, tx):
        s = io.BytesIO()
        tx.stream(s)
        tx_kb_count = len(s.getvalue()) / 1024
        method = "blockchain.estimatefee"
        coin_per_kb = self.loop.run_until_complete(
                            self.connection.listen_RPC(method, [6]))
        return int((tx_kb_count * coin_per_kb) * self._COIN)

    def mktx(self, out_addr, amount, fee="standard", version=1):
        spendables = list()
        payables = list()
        in_addrs = list()
        amount *= self._COIN
        total_out = decimal.Decimal("0")

        for utxo in self.utxos:
            if total_out < amount:
                spendables.append(LexSpendable.promote(utxo))
                in_addrs.append(utxo.address(self.chain.netcode))
                total_out += utxo.coin_value

        change_addr = self.get_next_unused_key(change=True).address()
        payables.append((out_addr, amount))
        payables.append((change_addr, 0))

        wifs = list()
        for change in (True, False):
            indicies = self.change_indicies if change else self.spend_indicies
            for i, used in enumerate(indicies):
                key = self.get_key(i, change)
                if key.address() in in_addrs:
                    wifs.append(key.wif())

        spendables.sort()
        txs_in = [spendable.tx_in() for spendable in spendables]
        txs_out = list()
        for payable in payables:
            bitcoin_address, coin_value = payable
            script = standard_tx_out_script(bitcoin_address)
            txs_out.append(LexTxOut.promote(TxOut(coin_value, script)))
        txs_out.sort()
        txs_out = [LexTxOut.demote(txout) for txout in txs_out]

        tx = Tx(version=version, txs_in=txs_in, txs_out=txs_out)
        tx.set_unspents(spendables)

        fee = self.get_fee(tx)
        distribute_from_split_pool(tx, fee)
        sign_tx(tx, wifs=wifs, netcode=self.chain.netcode)
        return tx

    def spend(self, address, amount):
        tx = self.mktx(address, amount)
        method = "blockchain.transaction.broadcast"
        txid = self.loop.run_until_complete(
                    self.connection.listen_RPC(method, [tx.as_hex()]))
        if address in self.history:
            self.history[address].append(tx)
        else:
            self.history[address] = [tx]
        self.balance -= amount
        self.utxos.append(tx.tx_outs_as_spendable()[-1])
        self.new_history = True
        return txid

    def __str__(self):
        str_ = list()
        str_.append("\nXPUB: {}".format(self.get_xpub()))
        str_.append("\nHistory:\n{}".format(self.history))
        str_.append("\nUTXOS:\n{}".format(self.utxos))
        str_.append("\nBalance: {} {}".format(
                        self.balance, self.chain.chain_1209k.upper()))
        str_.append("\nYour current address: {}".format(
                    self.get_next_unused_key().address()))
        return "".join(str_)

def get_random_onion(chain):
    servers = scrape_onion_servers(chain_1209k=chain.chain_1209k)
    assert servers, "No electrum servers found!"
    random.shuffle(servers)
    return servers.pop()

async def print_loop(wallet):
    while True:
        await asyncio.sleep(1)
        if wallet.new_history:
            print(wallet)
            wallet.new_history = False

def main():
    chain = TBTC
    loop = asyncio.get_event_loop()

    server, port = get_random_onion(chain)
    connection = Connection(loop, server, port)
#    connection = Connection(loop, "192.168.1.200", 50001)

    email = input("Enter email: ")
    passphrase = getpass.getpass("Enter passphrase: ")
    assert email and passphrase, "Email and/or passphrase were blank"
    wallet = Wallet(email, passphrase, connection, loop, chain)

    wallet.discover_keys()
    wallet.discover_keys(change=True)

    if len(sys.argv) > 1 and sys.argv[1] == "spend":
        print("\nBalance: {} {}".format(
                wallet.balance, chain.chain_1209k.upper()))
        print("Enter a destination address:")
        spend_addr = input("> ")
        print("Enter an amount to spend:")
        spend_amount = decimal.Decimal(input("> "))
        assert spend_addr and spend_amount, \
                "Spend address and/or amount were blank"
        assert spend_amount <= wallet.balance, "Insufficient funds"

        txid = wallet.spend(spend_addr, spend_amount)
        print("Transaction sent!\nID: {}".format(txid))

    asyncio.ensure_future(wallet.listen_to_addresses()),
    asyncio.ensure_future(print_loop(wallet))

    loop.run_forever()
    loop.close()

if __name__ == '__main__':
    main()

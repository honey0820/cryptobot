"""Live or test trading account"""

import re
from datetime import datetime
import time

import numpy as np
import pandas as pd

from utils.PyCryptoBot import truncate
from models.exchange.ExchangesEnum import Exchange
from models.exchange.binance import AuthAPI as BAuthAPI
from models.exchange.coinbase_pro import AuthAPI as CBAuthAPI
from models.exchange.kucoin import AuthAPI as KAuthAPI


class TradingAccount:
    def __init__(self, app=None):
        """Trading account object model

        Parameters
        ----------
        app : object
            PyCryptoBot object
        """

        # config needs to be a dictionary, empty or otherwise
        if app is None:
            raise TypeError("App is not a PyCryptoBot object.")

        # if trading account is for testing it will be instantiated with a balance of 1000
        self.balance = pd.DataFrame(
            [[app.quote_currency, 0, 0, 0], [app.base_currency, 0, 0, 0]],
            columns=["currency", "balance", "hold", "available"],
        )

        self.app = app

        if app.is_live:
            self.mode = "live"
        else:
            self.mode = "test"

        self.quotebalance = self.get_balance(app.quote_currency)
        self.basebalance = self.get_balance(app.base_currency)

        self.base_balance_before = 0.0
        self.quote_balance_before = 0.0

        self.orders = pd.DataFrame()

    def _convert_status(self, val):
        if val == "filled":
            return "done"
        else:
            return val

    def _check_market_syntax(self, market):
        """Check that the market is syntactically correct

        Parameters
        ----------
        market : str
            market to check
        """
        if self.app.exchange == Exchange.COINBASEPRO and market != "":
            p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
            if not p.match(market):
                raise TypeError("Coinbase Pro market is invalid.")
        elif self.app.exchange == Exchange.BINANCE:
            p = re.compile(r"^[0-9A-Z]{4,25}$")
            if not p.match(market):
                raise TypeError("Binance market is invalid.")
        elif self.app.exchange == Exchange.KUCOIN:
            p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
            if not p.match(market):
                raise TypeError("Kucoin market is invalid.")

    def get_orders(self, market="", action="", status="all"):
        """Retrieves orders either live or simulation

        Parameters
        ----------
        market : str, optional
            Filters orders by market
        action : str, optional
            Filters orders by action
        status : str
            Filters orders by status, defaults to 'all'
        """

        # validate market is syntactically correct
        self._check_market_syntax(market)

        if action != "":
            # validate action is either a buy or sell
            if action not in ["buy", "sell"]:
                raise ValueError("Invalid order action.")

        # validate status is open, pending, done, active or all
        if status not in ["open", "pending", "done", "active", "all", "filled"]:
            raise ValueError("Invalid order status.")

        if self.app.exchange == Exchange.BINANCE:
            if self.mode == "live":
                # if config is provided and live connect to Binance account portfolio
                model = BAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_url,
                    recv_window=self.app.recv_window,
                    app=self.app
                )
                # retrieve orders from live Binance account portfolio
                self.orders = model.get_orders(market, action, status)
                return self.orders
            else:
                # return dummy orders
                if market == "" or len(self.orders) == 0:
                    return self.orders
                else:
                    return self.orders[self.orders["market"] == market]

        if self.app.exchange == Exchange.KUCOIN:
            if self.mode == "live":
                # if config is provided and live connect to Kucoin account portfolio
                model = KAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_passphrase,
                    self.app.api_url,
                    use_cache=self.app.usekucoincache,
                    app=self.app
                )
                # retrieve orders from live Kucoin account portfolio
                self.orders = model.get_orders(market, action, status)
                return self.orders
            else:
                if market == "":
                    return self.orders
                else:
                    return self.orders[self.orders["market"] == market]

        if self.app.exchange == Exchange.COINBASEPRO:
            if self.mode == "live":
                # if config is provided and live connect to Coinbase Pro account portfolio
                model = CBAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_passphrase,
                    self.app.api_url,
                    app=self.app
                )
                # retrieve orders from live Coinbase Pro account portfolio
                self.orders = model.get_orders(market, action, status)
                return self.orders
            else:
                # return dummy orders
                if market == "":
                    return self.orders
                else:
                    if "market" in self.orders:
                        return self.orders[self.orders["market"] == market]
                    else:
                        return pd.DataFrame()
        if self.app.exchange == Exchange.DUMMY:
            return self.orders[
                [
                    "created_at",
                    "market",
                    "action",
                    "type",
                    "size",
                    "filled",
                    "fees",
                    "price",
                    "status",
                ]
            ]

    def get_balance(self, currency=""):
        """Retrieves balance either live or simulation

        Parameters
        ----------
        currency: str, optional
            Filters orders by currency
        """

        if self.app.exchange == Exchange.KUCOIN:
            if self.mode == "live":
                model = KAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_passphrase,
                    self.app.api_url,
                    use_cache=self.app.usekucoincache,
                    app=self.app
                )
                trycnt, maxretry = (0, 5)
                while trycnt <= maxretry:
                    df = model.get_accounts()

                    if isinstance(df, pd.DataFrame) and len(df) > 0:
                        if currency == "":
                            # retrieve all balances
                            return df
                        else:
                            # retrieve balance of specified currency
                            df_filtered = df[df["currency"] == currency]["available"]
                            if len(df_filtered) == 0:
                                # return nil balance if no positive balance was found
                                return 0.0
                            else:
                                # return balance of specified currency (if positive)
                                if currency in ["EUR", "GBP", "USD"]:
                                    return float(
                                        truncate(
                                            float(
                                                df[df["currency"] == currency][
                                                    "available"
                                                ].values[0]
                                            ),
                                            2,
                                        )
                                    )
                                else:
                                    return float(
                                        truncate(
                                            float(
                                                df[df["currency"] == currency][
                                                    "available"
                                                ].values[0]
                                            ),
                                            4,
                                        )
                                    )
                    else:
                        time.sleep(5)
                        trycnt += 1
                        if trycnt >= maxretry:
                            raise Exception(
                                "TradingAccount: Kucoin API Error while getting balance."
                            )
                else:
                    return 0.0

            else:
                # return dummy balances
                if currency == "":
                    # retrieve all balances
                    return self.balance
                else:
                    self.balance = self.balance.replace("QUOTE", currency)

                    if self.balance.currency[
                        self.balance.currency.isin([currency])
                    ].empty:
                        self.balance.loc[len(self.balance)] = [currency, 0, 0, 0]

                    # retrieve balance of specified currency
                    df = self.balance
                    df_filtered = df[df["currency"] == currency]["available"]

                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ["EUR", "GBP", "USD"]:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    2,
                                )
                            )
                        else:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    4,
                                )
                            )

        elif self.app.exchange == Exchange.BINANCE:
            if self.mode == "live":
                model = BAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_url,
                    recv_window=self.app.recv_window,
                    app=self.app
                )
                df = model.get_account()
                if isinstance(df, pd.DataFrame):
                    if currency == "":
                        # retrieve all balances
                        return df
                    else:
                        # return nil if dataframe is empty
                        if len(df) == 0:
                            return 0.0

                        # retrieve balance of specified currency
                        df_filtered = df[df["currency"] == currency]["available"]
                        if len(df_filtered) == 0:
                            # return nil balance if no positive balance was found
                            return 0.0
                        else:
                            # return balance of specified currency (if positive)
                            if currency in ["EUR", "GBP", "USD"]:
                                return float(
                                    truncate(
                                        float(
                                            df[df["currency"] == currency][
                                                "available"
                                            ].values[0]
                                        ),
                                        2,
                                    )
                                )
                            else:
                                return float(
                                    truncate(
                                        float(
                                            df[df["currency"] == currency][
                                                "available"
                                            ].values[0]
                                        ),
                                        4,
                                    )
                                )
                else:
                    return 0.0
            else:
                # return dummy balances
                if currency == "":
                    # retrieve all balances
                    return self.balance
                else:
                    if self.app.exchange == Exchange.BINANCE:
                        self.balance = self.balance.replace("QUOTE", currency)
                    else:
                        # replace QUOTE and BASE placeholders
                        if currency in ["EUR", "GBP", "USD"]:
                            self.balance = self.balance.replace("QUOTE", currency)
                        else:
                            self.balance = self.balance.replace("BASE", currency)

                    if self.balance.currency[
                        self.balance.currency.isin([currency])
                    ].empty:
                        self.balance.loc[len(self.balance)] = [currency, 0, 0, 0]

                    # retrieve balance of specified currency
                    df = self.balance
                    df_filtered = df[df["currency"] == currency]["available"]

                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ["EUR", "GBP", "USD"]:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    2,
                                )
                            )
                        else:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    4,
                                )
                            )

        elif self.app.exchange == Exchange.COINBASEPRO:
            if self.mode == "live":
                # if config is provided and live connect to Coinbase Pro account portfolio
                model = CBAuthAPI(
                    self.app.api_key,
                    self.app.api_secret,
                    self.app.api_passphrase,
                    self.app.api_url,
                    app=self.app
                )
                trycnt, maxretry = (0, 5)
                while trycnt <= maxretry:
                    df = model.get_accounts()

                    if len(df) > 0:
                        # retrieve all balances, but check the resp
                        if currency == "" and "balance" not in df:
                            time.sleep(5)
                            trycnt += 1
                        # retrieve all balances and return
                        elif currency == "":
                            return df
                        else:
                            # retrieve balance of specified currency
                            df_filtered = df[df["currency"] == currency]["available"]
                            if len(df_filtered) == 0:
                                # return nil balance if no positive balance was found
                                return 0.0
                            else:
                                # return balance of specified currency (if positive)
                                if currency in ["EUR", "GBP", "USD"]:
                                    return float(
                                        truncate(
                                            float(
                                                df[df["currency"] == currency][
                                                    "available"
                                                ].values[0]
                                            ),
                                            2,
                                        )
                                    )
                                else:
                                    return float(
                                        truncate(
                                            float(
                                                df[df["currency"] == currency][
                                                    "available"
                                                ].values[0]
                                            ),
                                            4,
                                        )
                                    )
                    else:
                        time.sleep(5)
                        trycnt += 1
                        if trycnt >= maxretry:
                            raise Exception(
                                "TradingAccount: CoinbasePro API Error while getting balance."
                            )
                else:
                    return 0.0

            else:
                # return dummy balances
                if currency == "":
                    # retrieve all balances
                    return self.balance
                else:
                    # replace QUOTE and BASE placeholders
                    if currency in ["EUR", "GBP", "USD"]:
                        self.balance = self.balance.replace("QUOTE", currency)
                    elif currency in ["BCH", "BTC", "ETH", "LTC", "XLM"]:
                        self.balance = self.balance.replace("BASE", currency)

                    if (
                        self.balance.currency[
                            self.balance.currency.isin([currency])
                        ].empty
                        is True
                    ):
                        self.balance.loc[len(self.balance)] = [currency, 0, 0, 0]

                    # retrieve balance of specified currency
                    df = self.balance
                    df_filtered = df[df["currency"] == currency]["available"]

                    if len(df_filtered) == 0:
                        # return nil balance if no positive balance was found
                        return 0.0
                    else:
                        # return balance of specified currency (if positive)
                        if currency in ["EUR", "GBP", "USD"]:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    2,
                                )
                            )
                        else:
                            return float(
                                truncate(
                                    float(
                                        df[df["currency"] == currency][
                                            "available"
                                        ].values[0]
                                    ),
                                    4,
                                )
                            )
        else:
            # dummy account

            if currency == "":
                # retrieve all balances
                return self.balance
            else:
                # retrieve balance of specified currency
                df = self.balance
                df_filtered = df[df["currency"] == currency]["available"]

                if len(df_filtered) == 0:
                    # return nil balance if no positive balance was found
                    return 0.0
                else:
                    # return balance of specified currency (if positive)
                    return float(df[df["currency"] == currency]["available"].values[0])

    def deposit_base_currency(self, base_currency: float) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if base_currency <= 0:
            raise ValueError(f"Invalid base currency: {str(base_currency)}")

        self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == self.app.base_currency, "balance"
            ]
            + base_currency
        )
        self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "balance"
        ]
        return self.balance

    def deposit_quote_currency(self, quote_currency: float) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if quote_currency <= 0:
            raise ValueError(f"Invalid quote currency: {str(quote_currency)}")

        self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == self.app.quote_currency, "balance"
            ]
            + quote_currency
        )
        self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "balance"
        ]
        return self.balance

    def withdraw_base_currency(self, base_currency: float) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if base_currency <= 0:
            raise ValueError(f"Invalid base currency: {str(base_currency)}")

        if (
            float(
                self.balance.loc[
                    self.balance["currency"] == self.app.base_currency, "balance"
                ]
                - base_currency
            )
            < 0
        ):
            raise ValueError("Insufficient funds!")

        self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == self.app.base_currency, "balance"
            ]
            - base_currency
        )
        self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == self.app.base_currency, "balance"
        ]
        return self.balance

    def withdraw_quote_currency(self, quote_currency: float) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if quote_currency <= 0:
            raise ValueError(f"Invalid quote currency: {str(quote_currency)}")

        if (
            float(
                self.balance.loc[
                    self.balance["currency"] == self.app.quote_currency, "balance"
                ]
                - quote_currency
            )
            < 0
        ):
            raise ValueError("Insufficient funds!")

        self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == self.app.quote_currency, "balance"
            ]
            - quote_currency
        )
        self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == self.app.quote_currency, "balance"
        ]
        return self.balance

    def market_buy(
        self,
        market: str = "",
        quote_currency: float = 0.0,
        buy_percent: float = 100,
        price: float = 0.0,
    ) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if price <= 0:
            raise ValueError(f"Invalid price: {str(price)}")

        if market == "":
            market = self.app.market

        p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
        if not p.match(market):
            raise ValueError(f"Invalid market: {market}")

        market_base_currency, market_quote_currency = market.split("-")

        if quote_currency > float(
            self.balance.loc[
                self.balance["currency"] == market_quote_currency, "balance"
            ]
        ):
            raise ValueError("Insufficient funds!")

        # update balances
        self.balance.loc[
            self.balance["currency"] == market_quote_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == market_quote_currency, "balance"
            ]
            - quote_currency
        )
        self.balance.loc[
            self.balance["currency"] == market_quote_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == market_quote_currency, "balance"
        ]
        fees = quote_currency * 0.001
        self.balance.loc[
            self.balance["currency"] == market_base_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == market_base_currency, "balance"
            ]
            + (quote_currency / price)
            - (fees / price)
        )
        self.balance.loc[
            self.balance["currency"] == market_base_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == market_base_currency, "balance"
        ]

        # update orders
        self.orders = pd.concat(
            [
                self.orders,
                pd.DataFrame(
                    {
                        "created_at": str(datetime.now()),
                        "market": market,
                        "action": "buy",
                        "type": "market",
                        "size": quote_currency,
                        "filled": float(
                            self.balance.loc[
                                self.balance["currency"] == market_base_currency,
                                "balance",
                            ]
                        ),
                        "fees": fees,
                        "price": price,
                        "status": "done",
                    },
                    index={0},
                ),
            ],
            ignore_index=True,
        )

        return True

    def market_sell(
        self,
        market: str = "",
        base_currency: float = 0.0,
        price: float = 0.0,
    ) -> pd.DataFrame():
        if self.app.exchange != "dummy":
            raise Exception("deposit_base_currency() is for dummy account usage only!")

        if price <= 0:
            raise ValueError(f"Invalid price: {str(price)}")

        if market == "":
            market = self.app.market

        p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
        if not p.match(market):
            raise ValueError(f"Invalid market: {market}")

        market_base_currency, market_quote_currency = market.split("-")

        if base_currency > float(
            self.balance.loc[
                self.balance["currency"] == market_base_currency, "balance"
            ]
        ):
            raise ValueError("Insufficient funds!")

        # update balances
        self.balance.loc[
            self.balance["currency"] == market_base_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == market_base_currency, "balance"
            ]
            - base_currency
        )
        self.balance.loc[
            self.balance["currency"] == market_base_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == market_base_currency, "balance"
        ]
        fees = (base_currency * price) * 0.001
        self.balance.loc[
            self.balance["currency"] == market_quote_currency, "balance"
        ] = (
            self.balance.loc[
                self.balance["currency"] == market_quote_currency, "balance"
            ]
            + (base_currency * price)
            - fees
        )
        self.balance.loc[
            self.balance["currency"] == market_quote_currency, "available"
        ] = self.balance.loc[
            self.balance["currency"] == market_quote_currency, "balance"
        ]

        # update orders
        self.orders = pd.concat(
            [
                self.orders,
                pd.DataFrame(
                    {
                        "created_at": str(datetime.now()),
                        "market": market,
                        "action": "sell",
                        "type": "market",
                        "size": base_currency,
                        "filled": base_currency,
                        "fees": fees,
                        "price": price,
                        "status": "done",
                    },
                    index={0},
                ),
            ],
            ignore_index=True,
        )

        return True

    def save_tracker_csv(self, market="", save_file="tracker.csv"):
        """Saves order tracker to CSV

        Parameters
        ----------
        market : str, optional
            Filters orders by market
        save_file : str
            Output CSV file
        """

        # validate market is syntactically correct
        self._check_market_syntax(market)

        if self.mode == "live":
            if self.app.exchange == Exchange.COINBASEPRO:
                # retrieve orders from live Coinbase Pro account portfolio
                df = self.get_orders(market, "", "done")
            elif self.app.exchange == Exchange.BINANCE:
                # retrieve orders from live Binance account portfolio
                df = self.get_orders(market, "", "done")
            elif self.app.exchange == Exchange.KUCOIN:
                # retrieve orders from live Kucoin account portfolio
                df = self.get_orders(market, "", "done")
            else:
                df = pd.DataFrame()
        else:
            # return dummy orders
            if market == "":
                df = self.orders
            else:
                if "market" in self.orders:
                    df = self.orders[self.orders["market"] == market]
                else:
                    df = pd.DataFrame()

        if list(df.keys()) != [
            "created_at",
            "market",
            "action",
            "type",
            "size",
            "value",
            "fees",
            "price",
            "status",
        ]:
            # no data, return early
            return False

        df_tracker = pd.DataFrame()

        last_action = ""
        for market in df["market"].sort_values().unique():
            df_market = df[df["market"] == market]

            df_buy = pd.DataFrame()
            df_sell = pd.DataFrame()

            pair = 0
            # pylint: disable=unused-variable
            for index, row in df_market.iterrows():
                if row["action"] == "buy":
                    pair = 1

                if pair == 1 and (row["action"] != last_action):
                    if row["action"] == "buy":
                        df_buy = row
                    elif row["action"] == "sell":
                        df_sell = row

                if row["action"] == "sell" and len(df_buy) != 0:
                    df_pair = pd.DataFrame(
                        [
                            [
                                df_sell["status"],
                                df_buy["market"],
                                df_buy["created_at"],
                                df_buy["type"],
                                df_buy["size"],
                                df_buy["value"],
                                df_buy["fees"],
                                df_buy["price"],
                                df_sell["created_at"],
                                df_sell["type"],
                                df_sell["size"],
                                df_sell["value"],
                                df_sell["fees"],
                                df_sell["price"],
                            ]
                        ],
                        columns=[
                            "status",
                            "market",
                            "buy_at",
                            "buy_type",
                            "buy_size",
                            "buy_value",
                            "buy_fees",
                            "buy_price",
                            "sell_at",
                            "sell_type",
                            "sell_size",
                            "sell_value",
                            "sell_fees",
                            "sell_price",
                        ],
                    )
                    df_tracker = pd.concat([df_tracker, df_pair])
                    pair = 0

                last_action = row["action"]

        if list(df_tracker.keys()) != [
            "status",
            "market",
            "buy_at",
            "buy_type",
            "buy_size",
            "buy_value",
            "buy_fees",
            "buy_price",
            "sell_at",
            "sell_type",
            "sell_size",
            "sell_value",
            "sell_fees",
            "sell_price",
        ]:
            # no data, return early
            return False

        df_tracker["profit"] = np.subtract(
            np.subtract(df_tracker["sell_value"], df_tracker["buy_value"]),
            np.add(df_tracker["buy_fees"], df_tracker["sell_fees"]),
        )
        df_tracker["margin"] = np.multiply(
            np.true_divide(df_tracker["profit"], df_tracker["buy_value"]), 100
        )
        df_sincebot = df_tracker[df_tracker["buy_at"] > "2021-02-1"]

        try:
            df_sincebot.to_csv(save_file, index=False)
        except OSError:
            raise SystemExit(f"Unable to save: {save_file}")

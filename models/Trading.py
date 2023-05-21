"""Technical analysis on a trading Pandas DataFrame"""

import warnings
import pandas_ta as ta

from re import compile
from numpy import (
    abs,
    floor,
    max,
    maximum,
    mean,
    minimum,
    nan,
    ndarray,
    round,
    sum as np_sum,
    where,
)
from pandas import concat, DataFrame, Series
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResultsWrapper
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from views.PyCryptoBot import RichText

warnings.simplefilter("ignore", ConvergenceWarning)


class TechnicalAnalysis:
    def __init__(self, data=DataFrame(), total_periods: int = 300, app: object = None) -> None:
        """Technical Analysis object model

        Parameters
        ----------
        data : Pandas Time Series
            data[ts] = [ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]
        """
        
        if not isinstance(data, DataFrame):
            raise TypeError("Data is not a Pandas dataframe.")

        if (
            "date" not in data
            and "market" not in data
            and "granularity" not in data
            and "low" not in data
            and "high" not in data
            and "open" not in data
            and "close" not in data
            and "volume" not in data
        ):
            raise ValueError("Data not not contain date, market, granularity, low, high, open, close, volume")

        if "close" not in data.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not data["close"].dtype == "float64" and not data["close"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        # app
        self.app = app

        self.df = data
        self.levels = []
        self.total_periods = total_periods

    def get_df(self) -> DataFrame:
        """Returns the Pandas DataFrame"""

        return self.df

    def add_all(self) -> None:
        """Adds analysis to the DataFrame"""

        self.add_change_pcnt()

        self.add_cma()
        self.add_sma(5)
        self.add_sma(8)
        self.add_sma(13)
        self.add_sma(20)
        if self.total_periods >= 50:
            self.add_sma(50)
        if self.total_periods >= 200:
            self.add_sma(200)
        self.add_ema(8)
        self.add_ema(12)
        self.add_ema(26)

        self.add_golden_cross()
        self.add_death_cross()

        self.add_bollinger_bands(20)
        self.add_fibonacci_bollinger_bands()
        self.add_support_resistance_levels(20)

        self.add_rsi(14)
        self.add_stochrsi(14)
        self.add_williamsr(14)
        self.add_macd()
        self.add_obv()
        self.add_elder_ray_index()

        self.add_ema_buy_signals()
        if self.total_periods >= 200:
            self.add_sma_buy_signals()
        self.add_macd_buy_signals()
        self.add_adx_buy_signals()
        self.add_bbands_buy_signals()

    """Candlestick References
    https://commodity.com/technical-analysis
    https://www.investopedia.com
    https://github.com/SpiralDevelopment/candlestick-patterns
    https://www.incrediblecharts.com/candlestick_patterns/candlestick-patterns-strongest.php
    """

    def add_candles(self) -> None:
        frames = [
            self.candle_astral_buy(),
            self.candle_astral_sell(),
            self.candle_hammer(),
            self.candle_inverted_hammer(),
            self.candle_shooting_star(),
            self.candle_hanging_man(),
            self.candle_three_white_soldiers(),
            self.candle_three_black_crows(),
            self.candle_doji(),
            self.candle_three_line_strike(),
            self.candle_two_black_gapping(),
            self.candle_morning_star(),
            self.candle_evening_star(),
            self.candle_abandoned_baby(),
            self.candle_morning_doji_star(),
            self.candle_evening_doji_star(),
        ]
        df_candles = concat(frames, axis=1)
        df_candles.columns = [
            "astral_buy",
            "astral_sell",
            "hammer",
            "inverted_hammer",
            "shooting_star",
            "hanging_man",
            "three_white_soldiers",
            "three_black_crows",
            "doji",
            "three_line_strike",
            "two_black_gapping",
            "morning_star",
            "evening_star",
            "abandoned_baby",
            "morning_doji_star",
            "evening_doji_star",
        ]
        self.df = concat([self.df, df_candles], axis=1)

    def candle_hammer(self) -> Series:
        """* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up"""

        return (
            ((self.df["high"] - self.df["low"]) > 3 * (self.df["open"] - self.df["close"]))
            & (((self.df["close"] - self.df["low"]) / (0.001 + self.df["high"] - self.df["low"])) > 0.6)
            & (((self.df["open"] - self.df["low"]) / (0.001 + self.df["high"] - self.df["low"])) > 0.6)
        )

    def candle_shooting_star(self) -> Series:
        """* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")"""

        return (
            ((self.df["open"].shift(1) < self.df["close"].shift(1)) & (self.df["close"].shift(1) < self.df["open"]))
            & (self.df["high"] - maximum(self.df["open"], self.df["close"]) >= (abs(self.df["open"] - self.df["close"]) * 3))
            & ((minimum(self.df["close"], self.df["open"]) - self.df["low"]) <= abs(self.df["open"] - self.df["close"]))
        )

    def candle_hanging_man(self) -> Series:
        """* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")"""

        return (
            ((self.df["high"] - self.df["low"]) > (4 * (self.df["open"] - self.df["close"])))
            & (((self.df["close"] - self.df["low"]) / (0.001 + self.df["high"] - self.df["low"])) >= 0.75)
            & (((self.df["open"] - self.df["low"]) / (0.001 + self.df["high"] - self.df["low"])) >= 0.75)
            & (self.df["high"].shift(1) < self.df["open"])
            & (self.df["high"].shift(2) < self.df["open"])
        )

    def candle_inverted_hammer(self) -> Series:
        """* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")"""

        return (
            ((self.df["high"] - self.df["low"]) > 3 * (self.df["open"] - self.df["close"]))
            & ((self.df["high"] - self.df["close"]) / (0.001 + self.df["high"] - self.df["low"]) > 0.6)
            & ((self.df["high"] - self.df["open"]) / (0.001 + self.df["high"] - self.df["low"]) > 0.6)
        )

    def candle_three_white_soldiers(self) -> Series:
        """*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            ((self.df["open"] > self.df["open"].shift(1)) & (self.df["open"] < self.df["close"].shift(1)))
            & (self.df["close"] > self.df["high"].shift(1))
            & (self.df["high"] - maximum(self.df["open"], self.df["close"]) < (abs(self.df["open"] - self.df["close"])))
            & ((self.df["open"].shift(1) > self.df["open"].shift(2)) & (self.df["open"].shift(1) < self.df["close"].shift(2)))
            & (self.df["close"].shift(1) > self.df["high"].shift(2))
            & (
                self.df["high"].shift(1) - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def candle_three_black_crows(self) -> Series:
        """* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")"""

        return (
            ((self.df["open"] < self.df["open"].shift(1)) & (self.df["open"] > self.df["close"].shift(1)))
            & (self.df["close"] < self.df["low"].shift(1))
            & (self.df["low"] - maximum(self.df["open"], self.df["close"]) < (abs(self.df["open"] - self.df["close"])))
            & ((self.df["open"].shift(1) < self.df["open"].shift(2)) & (self.df["open"].shift(1) > self.df["close"].shift(2)))
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1) - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def candle_doji(self) -> Series:
        """! Candlestick Detected: Doji ("Indecision")"""

        return (
            ((abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"])) < 0.1)
            & ((self.df["high"] - maximum(self.df["close"], self.df["open"])) > (3 * abs(self.df["close"] - self.df["open"])))
            & ((minimum(self.df["close"], self.df["open"]) - self.df["low"]) > (3 * abs(self.df["close"] - self.df["open"])))
        )

    def candle_three_line_strike(self) -> Series:
        """** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            ((self.df["open"].shift(1) < self.df["open"].shift(2)) & (self.df["open"].shift(1) > self.df["close"].shift(2)))
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1) - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
            & ((self.df["open"].shift(2) < self.df["open"].shift(3)) & (self.df["open"].shift(2) > self.df["close"].shift(3)))
            & (self.df["close"].shift(2) < self.df["low"].shift(3))
            & (
                self.df["low"].shift(2) - maximum(self.df["open"].shift(2), self.df["close"].shift(2))
                < (abs(self.df["open"].shift(2) - self.df["close"].shift(2)))
            )
            & ((self.df["open"] < self.df["low"].shift(1)) & (self.df["close"] > self.df["high"].shift(3)))
        )

    def candle_two_black_gapping(self) -> Series:
        """*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (
            ((self.df["open"] < self.df["open"].shift(1)) & (self.df["open"] > self.df["close"].shift(1)))
            & (self.df["close"] < self.df["low"].shift(1))
            & (self.df["low"] - maximum(self.df["open"], self.df["close"]) < (abs(self.df["open"] - self.df["close"])))
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def candle_morning_star(self) -> Series:
        """*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            (maximum(self.df["open"].shift(1), self.df["close"].shift(1)) < self.df["close"].shift(2)) & (self.df["close"].shift(2) < self.df["open"].shift(2))
        ) & ((self.df["close"] > self.df["open"]) & (self.df["open"] > maximum(self.df["open"].shift(1), self.df["close"].shift(1))))

    def candle_evening_star(self) -> ndarray:
        """*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")"""

        return (
            (minimum(self.df["open"].shift(1), self.df["close"].shift(1)) > self.df["close"].shift(2)) & (self.df["close"].shift(2) > self.df["open"].shift(2))
        ) & ((self.df["close"] < self.df["open"]) & (self.df["open"] < minimum(self.df["open"].shift(1), self.df["close"].shift(1))))

    def candle_abandoned_baby(self):
        """** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            (self.df["open"] < self.df["close"])
            & (self.df["high"].shift(1) < self.df["low"])
            & (self.df["open"].shift(2) > self.df["close"].shift(2))
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def candle_morning_doji_star(self) -> Series:
        """** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (self.df["close"].shift(2) < self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2)) / (self.df["high"].shift(2) - self.df["low"].shift(2)) >= 0.7
        ) & (abs(self.df["close"].shift(1) - self.df["open"].shift(1)) / (self.df["high"].shift(1) - self.df["low"].shift(1)) < 0.1) & (
            self.df["close"] > self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"]) >= 0.7
        ) & (
            self.df["close"].shift(2) > self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) > self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) < self.df["open"]
        ) & (
            self.df["open"].shift(1) < self.df["open"]
        ) & (
            self.df["close"] > self.df["close"].shift(2)
        ) & (
            (self.df["high"].shift(1) - maximum(self.df["close"].shift(1), self.df["open"].shift(1)))
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1)) - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def candle_evening_doji_star(self) -> Series:
        """** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (self.df["close"].shift(2) > self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2)) / (self.df["high"].shift(2) - self.df["low"].shift(2)) >= 0.7
        ) & (abs(self.df["close"].shift(1) - self.df["open"].shift(1)) / (self.df["high"].shift(1) - self.df["low"].shift(1)) < 0.1) & (
            self.df["close"] < self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"]) >= 0.7
        ) & (
            self.df["close"].shift(2) < self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) < self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) > self.df["open"]
        ) & (
            self.df["open"].shift(1) > self.df["open"]
        ) & (
            self.df["close"] < self.df["close"].shift(2)
        ) & (
            (self.df["high"].shift(1) - maximum(self.df["close"].shift(1), self.df["open"].shift(1)))
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1)) - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def candle_astral_buy(self) -> Series:
        """*** Candlestick Detected: Astral Buy (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] < self.df["close"].shift(3))
            & (self.df["low"] < self.df["low"].shift(5))
            & (self.df["close"].shift(1) < self.df["close"].shift(4))
            & (self.df["low"].shift(1) < self.df["low"].shift(6))
            & (self.df["close"].shift(2) < self.df["close"].shift(5))
            & (self.df["low"].shift(2) < self.df["low"].shift(7))
            & (self.df["close"].shift(3) < self.df["close"].shift(6))
            & (self.df["low"].shift(3) < self.df["low"].shift(8))
            & (self.df["close"].shift(4) < self.df["close"].shift(7))
            & (self.df["low"].shift(4) < self.df["low"].shift(9))
            & (self.df["close"].shift(5) < self.df["close"].shift(8))
            & (self.df["low"].shift(5) < self.df["low"].shift(10))
            & (self.df["close"].shift(6) < self.df["close"].shift(9))
            & (self.df["low"].shift(6) < self.df["low"].shift(11))
            & (self.df["close"].shift(7) < self.df["close"].shift(10))
            & (self.df["low"].shift(7) < self.df["low"].shift(12))
        )

    def candle_astral_sell(self) -> Series:
        """*** Candlestick Detected: Astral Sell (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] > self.df["close"].shift(3))
            & (self.df["high"] > self.df["high"].shift(5))
            & (self.df["close"].shift(1) > self.df["close"].shift(4))
            & (self.df["high"].shift(1) > self.df["high"].shift(6))
            & (self.df["close"].shift(2) > self.df["close"].shift(5))
            & (self.df["high"].shift(2) > self.df["high"].shift(7))
            & (self.df["close"].shift(3) > self.df["close"].shift(6))
            & (self.df["high"].shift(3) > self.df["high"].shift(8))
            & (self.df["close"].shift(4) > self.df["close"].shift(7))
            & (self.df["high"].shift(4) > self.df["high"].shift(9))
            & (self.df["close"].shift(5) > self.df["close"].shift(8))
            & (self.df["high"].shift(5) > self.df["high"].shift(10))
            & (self.df["close"].shift(6) > self.df["close"].shift(9))
            & (self.df["high"].shift(6) > self.df["high"].shift(11))
            & (self.df["close"].shift(7) > self.df["close"].shift(10))
            & (self.df["high"].shift(7) > self.df["high"].shift(12))
        )

    def add_adx_buy_signals(self, interval: int = 14) -> None:
        """Adds Average Directional Index (ADX) buy and sell signals to the DataFrame"""

        data = self._average_directional_index(interval)
        self.df["-di" + str(interval)] = data["-di" + str(interval)]
        self.df["+di" + str(interval)] = data["+di" + str(interval)]
        self.df["adx" + str(interval)] = data["adx" + str(interval)]
        self.df["adx" + str(interval) + "_trend"] = data["adx" + str(interval) + "_trend"]
        self.df["adx" + str(interval) + "_strength"] = data["adx" + str(interval) + "_strength"]

    def add_adx(self, interval: int = 14) -> None:
        """Adds Average Directional Index (ADX)"""

        data = self._average_directional_index(interval)
        self.df["-di" + str(interval)] = data["-di" + str(interval)]
        self.df["+di" + str(interval)] = data[["+di" + str(interval)]]
        self.df["adx" + str(interval)] = data[["adx" + str(interval)]]

    def _average_directional_index(self, interval: int = 14) -> DataFrame:
        """Average Directional Index (ADX)"""

        if not isinstance(interval, int):
            raise TypeError("interval parameter is not intervaleric.")

        if interval > self.total_periods or interval < 5 or interval > 200:
            raise ValueError("interval is out of range")

        if len(self.df) < interval:
            raise Exception("Data range too small.")

        df = self.df.copy()

        df["-dm"] = df["low"].shift(1) - df["low"]
        df["+dm"] = df["high"] - df["high"].shift(1)
        df["+dm"] = where((df["+dm"] > df["-dm"]) & (df["+dm"] > 0), df["+dm"], 0.0)
        df["-dm"] = where((df["-dm"] > df["+dm"]) & (df["-dm"] > 0), df["-dm"], 0.0)

        df["tr_tmp1"] = df["high"] - df["low"]
        df["tr_tmp2"] = abs(df["high"] - df["close"].shift(1))
        df["tr_tmp3"] = abs(df["low"] - df["close"].shift(1))
        df["tr"] = df[["tr_tmp1", "tr_tmp2", "tr_tmp3"]].max(axis=1)

        df["tr" + str(interval)] = df["tr"].rolling(interval).sum()

        df["+dmi" + str(interval)] = df["+dm"].rolling(interval).sum()
        df["-dmi" + str(interval)] = df["-dm"].rolling(interval).sum()

        df["+di" + str(interval)] = df["+dmi" + str(interval)] / df["tr" + str(interval)] * 100
        df["-di" + str(interval)] = df["-dmi" + str(interval)] / df["tr" + str(interval)] * 100
        df["di" + str(interval) + "-"] = abs(df["+di" + str(interval)] - df["-di" + str(interval)])
        df["di" + str(interval) + "+"] = df["+di" + str(interval)] + df["-di" + str(interval)]

        df["dx"] = (df["di" + str(interval) + "-"] / df["di" + str(interval) + "+"]) * 100

        df["adx" + str(interval)] = df["dx"].rolling(interval).mean()

        df["-di" + str(interval)] = df["-di" + str(interval)].fillna(df["-di" + str(interval)].mean())
        df["+di" + str(interval)] = df["+di" + str(interval)].fillna(df["+di" + str(interval)].mean())
        df["adx" + str(interval)] = df["adx" + str(interval)].fillna(df["adx" + str(interval)].mean())

        df["adx" + str(interval) + "_trend"] = where(df["+di" + str(interval)] > df["-di" + str(interval)], "bull", "bear")
        df["adx" + str(interval) + "_strength"] = where(
            df["adx" + str(interval)] > 25,
            "strong",
            where(df["adx" + str(interval)] < 20, "weak", "normal"),
        )

        return df[
            [
                "-di" + str(interval),
                "+di" + str(interval),
                "adx" + str(interval),
                "adx" + str(interval) + "_trend",
                "adx" + str(interval) + "_strength",
            ]
        ]

    def add_atr(self, interval: int = 14) -> None:
        """Adds Average True Range (ATR)"""

        self.df["atr" + str(interval)] = self._average_true_range(interval)
        self.df["atr" + str(interval)] = self.df["atr" + str(interval)].fillna(self.df["atr" + str(interval)].mean())

    def _average_true_range(self, interval: int = 14) -> DataFrame:
        """Average True Range (ATX)"""

        if not isinstance(interval, int):
            raise TypeError("interval parameter is not intervaleric.")

        if interval > self.total_periods or interval < 5 or interval > 200:
            raise ValueError("interval is out of range")

        if len(self.df) < interval:
            raise Exception("Data range too small.")

        high_low = self.df["high"] - self.df["low"]
        high_close = abs(self.df["high"] - self.df["close"].shift())
        low_close = abs(self.df["low"] - self.df["close"].shift())

        ranges = concat([high_low, high_close, low_close], axis=1)
        true_range = max(ranges, axis=1)

        return true_range.rolling(interval).sum() / interval

    def change_pcnt(self) -> DataFrame:
        """Close change percentage"""

        close_pc = self.df["close"] / self.df["close"].shift(1) - 1
        close_pc = close_pc.fillna(0)
        return close_pc

    def add_change_pcnt(self) -> None:
        """Adds the close percentage to the DataFrame"""

        self.df["close_pc"] = self.change_pcnt()

        # cumulative returns
        self.df["close_cpc"] = (1 + self.df["close_pc"]).cumprod() - 1

    def cumulative_moving_average(self) -> float:
        """Calculates the Cumulative Moving Average (CMA)"""

        return self.df.close.expanding().mean()

    def add_cma(self) -> None:
        """Adds the Cumulative Moving Average (CMA) to the DataFrame"""

        self.df["cma"] = self.cumulative_moving_average()

    def exponential_moving_average(self, period: int) -> float:
        """Calculates the Exponential Moving Average (EMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.ewm(span=period, adjust=False).mean()

    def add_bollinger_bands(self, period: int = 20, std: int = 2) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        df_tmp = ta.bbands(length=period, std=std, mamode="sma", close=self.df.close, fillna=self.df.close)
        self.df["bb" + str(period) + "_upper"] = df_tmp[f"BBU_{period}_{std}.0"]
        self.df["bb" + str(period) + "_mid"] = df_tmp[f"BBM_{period}_{std}.0"]
        self.df["bb" + str(period) + "_lower"] = df_tmp[f"BBL_{period}_{std}.0"]

    def add_ema(self, period: int) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        # self.df["ema" + str(period)] = self.exponential_moving_average(period)
        self.df["ema" + str(period)] = ta.ema(self.df["close"], length=period, fillna=self.df.close)

    def calculate_relative_strength_index(self, series: int, interval: int = 14) -> float:
        """Calculates the RSI on a Pandas series of closing prices."""

        if not isinstance(series, Series):
            raise TypeError("Pandas Series required.")

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if len(series) < interval:
            raise IndexError("Pandas Series smaller than interval.")

        diff = series.diff(1).dropna()

        sum_gains = 0 * diff
        sum_gains[diff > 0] = diff[diff > 0]
        avg_gains = sum_gains.ewm(com=interval - 1, min_periods=interval).mean()

        sum_losses = 0 * diff
        sum_losses[diff < 0] = diff[diff < 0]
        avg_losses = sum_losses.ewm(com=interval - 1, min_periods=interval).mean()

        rs = abs(avg_gains / avg_losses)
        rsi = 100 - 100 / (1 + rs)

        return rsi

    def calculate_stochastic_relative_strength_index(self, series: int, interval: int = 14) -> float:
        """Calculates the Stochastic RSI on a Pandas series of RSI"""

        if not isinstance(series, Series):
            raise TypeError("Pandas Series required.")

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if len(series) < interval:
            raise IndexError("Pandas Series smaller than interval.")

        return (series - series.rolling(interval).min()) / (series.rolling(interval).max() - series.rolling(interval).min())

    def add_fibonacci_bollinger_bands(self, interval: int = 20, multiplier: int = 3) -> None:
        """Adds Fibonacci Bollinger Bands."""

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if not isinstance(multiplier, int):
            raise TypeError("Multiplier integer required.")

        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        sma = tp.rolling(interval).mean()
        sd = multiplier * tp.rolling(interval).std()

        sma = sma.fillna(0)
        sd = sd.fillna(0)

        self.df["fbb_mid"] = sma
        self.df["fbb_upper0_236"] = sma + (0.236 * sd)
        self.df["fbb_upper0_382"] = sma + (0.382 * sd)
        self.df["fbb_upper0_5"] = sma + (0.5 * sd)
        self.df["fbb_upper0_618"] = sma + (0.618 * sd)
        self.df["fbb_upper0_786"] = sma + (0.786 * sd)
        self.df["fbb_upper1"] = sma + (1 * sd)
        self.df["fbb_lower0_236"] = sma - (0.236 * sd)
        self.df["fbb_lower0_382"] = sma - (0.382 * sd)
        self.df["fbb_lower0_5"] = sma - (0.5 * sd)
        self.df["fbb_lower0_618"] = sma - (0.618 * sd)
        self.df["fbb_lower0_786"] = sma - (0.786 * sd)
        self.df["fbb_lower1"] = sma - (1 * sd)

    def moving_average_convergence_divergence(self) -> DataFrame:
        """Calculates the Moving Average Convergence Divergence (MACD)"""

        if len(self.df) < 26:
            raise Exception("Data range too small.")

        if not self.df["ema12"].dtype == "float64" and not self.df["ema12"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'ema12' column not int64 or float64.")

        if not self.df["ema26"].dtype == "float64" and not self.df["ema26"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'ema26' column not int64 or float64.")

        df = DataFrame()
        df["macd"] = self.df["ema12"] - self.df["ema26"]
        df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        return df

    def add_macd(self, slow: int = 12, fast: int = 26) -> None:
        """Adds the Moving Average Convergence Divergence (MACD) to the DataFrame"""

        # df = self.moving_average_convergence_divergence()
        # self.df["macd"] = df["macd"]
        # self.df["signal"] = df["signal"]
        df_macd = ta.macd(self.df["close"], slow=slow, fast=fast, fillna=0)
        df_macd.fillna(0, inplace=True)
        df_macd.columns = ["macd", "histogram", "signal"]
        self.df["macd"] = df_macd["macd"]
        self.df["signal"] = df_macd["signal"]

    def on_balance_volume(self) -> ndarray:
        """Calculate On-Balance Volume (OBV)"""

        try:
            return where(
                self.df["close"] == self.df["close"].shift(1),
                0,
                where(
                    self.df["close"] > self.df["close"].shift(1),
                    self.df["volume"],
                    where(
                        self.df["close"] < self.df["close"].shift(1),
                        -self.df["volume"].apply(lambda x: float(x)),
                        self.df.iloc[0]["volume"],
                    ),
                ),
            ).cumsum()
        except Exception:
            return 0

    def add_obv(self) -> None:
        """Add the On-Balance Volume (OBV) to the DataFrame"""

        self.df["obv"] = self.on_balance_volume()
        self.df["obv_pc"] = self.df["obv"].pct_change() * 100
        self.df["obv_pc"] = round(self.df["obv_pc"].fillna(0), 2)

    def relative_strength_index(self, period) -> DataFrame:
        """Calculate the Relative Strength Index (RSI)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        # calculate relative strength index
        rsi = self.calculate_relative_strength_index(self.df["close"], period)
        # default to midway-50 for first entries
        rsi = rsi.fillna(50)
        return rsi

    def stochastic_relative_strength_index(self, period) -> DataFrame:
        """Calculate the Stochastic Relative Strength Index (Stochastic RSI)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        if "rsi" + str(period) not in self.df:
            self.add_rsi(period)

        # calculate relative strength index
        stochrsi = self.calculate_stochastic_relative_strength_index(self.df["rsi" + str(period)], period)
        # default to midway-50 for first entries
        stochrsi = stochrsi.fillna(0.5)
        return stochrsi

    def add_stochrsi(self, period: int = 14) -> None:
        """Adds the Stochastic RSI to the DataFrame"""

        # df = self.moving_average_convergence_divergence()
        # self.df["macd"] = df["macd"]
        # self.df["signal"] = df["signal"]
        df_stochrsi = ta.stochrsi(high=self.df["high"], close=self.df["close"], low=self.df["low"], interval=period, fillna=50)
        df_stochrsi.fillna(0, inplace=True)
        df_stochrsi.columns = ["stochrsik", "stochrsid"]
        self.df[f"stochrsi{period}k"] = df_stochrsi["stochrsik"]
        self.df[f"stochrsi{period}d"] = df_stochrsi["stochrsid"]

    def williamsr(self, period) -> DataFrame:
        """Calculate the Williams %R"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        dividend = self.df["high"].rolling(14).max() - self.df["close"]
        divisor = self.df["high"].rolling(14).max() - self.df["low"].rolling(14).min()

        return (dividend / divisor) * -100

    def add_rsi(self, period: int = 14) -> None:
        """Adds the Relative Strength Index (RSI) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        # self.df["rsi" + str(period)] = self.relative_strength_index(period)
        # self.df["rsi" + str(period)] = self.df["rsi" + str(period)].replace(nan, 50)
        self.df["rsi" + str(period)] = ta.rsi(self.df["close"], length=period, fillna=50)

    def add_williamsr(self, period: int = 14) -> None:
        """Adds the Willams %R to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        # self.df["williamsr" + str(period)] = self.williamsr(period)
        # self.df["williamsr" + str(period)] = self.df["williamsr" + str(period)].replace(nan, -50)
        self.df["williamsr" + str(period)] = ta.willr(high=self.df["high"], close=self.df["close"], low=self.df["low"], interval=period, fillna=self.df.close)

    def seasonal_arima_model(self) -> SARIMAXResultsWrapper:
        """Returns the Seasonal ARIMA Model for price predictions"""

        # hyperparameters for SARIMAX
        if not self.df.index.freq:
            freq = str(self.df["granularity"].iloc[-1]).replace("m", "T").replace("h", "H").replace("d", "D")
            if freq.isdigit():
                freq += "S"
            self.df.index = self.df.index.to_period(freq)
        model = SARIMAX(self.df["close"], trend="n", order=(0, 1, 0), seasonal_order=(1, 1, 1, 12))
        return model.fit(disp=-1)

    def seasonal_arima_model_fitted_values(self):  # TODO: annotate return type
        """Returns the Seasonal ARIMA Model for price predictions"""

        return self.seasonal_arima_model().fittedvalues

    def seasonal_arima_model_prediction(self, minutes: int = 180) -> tuple:
        """Returns seasonal ARIMA model prediction

        Parameters
        ----------
        minutes     : int
            Number of minutes to predict
        """

        if not isinstance(minutes, int):
            raise TypeError("Prediction minutes is not numeric.")

        if minutes < 1 or minutes > 4320:
            raise ValueError("Predication minutes is out of range")

        results_ARIMA = self.seasonal_arima_model()

        start_ts = self.df.last_valid_index()
        end_ts = start_ts + timedelta(minutes=minutes)
        pred = results_ARIMA.predict(start=str(start_ts), end=str(end_ts), dynamic=True)

        try:
            if len(pred) == 0:
                df_last = self.df["close"].tail(1)
                return (
                    str(df_last.index.values[0]).replace("T", " ").replace(".000000000", ""),
                    df_last.values[0],
                )
            else:
                df_last = pred.tail(1)
                return (
                    str(df_last.index.values[0]).replace("T", " ").replace(".000000000", ""),
                    df_last.values[0],
                )
        except Exception:
            return None

        return None

    def simple_moving_average(self, period: int) -> float:
        """Calculates the Simple Moving Average (SMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.rolling(period, min_periods=1).mean()

    def add_sma(self, period: int) -> None:
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period > self.total_periods or period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        # self.df["sma" + str(period)] = self.simple_moving_average(period)
        self.df["sma" + str(period)] = ta.sma(self.df["close"], length=period, fillna=self.df.close)

    def add_golden_cross(self) -> None:
        """Add Golden Cross SMA50 over SMA200"""

        if self.total_periods < 200:
            self.df["goldencross"] = False
            return

        if "sma50" not in self.df:
            self.add_sma(50)

        if "sma200" not in self.df:
            self.add_sma(200)

        self.df["goldencross"] = self.df["sma50"] > self.df["sma200"]

    def add_death_cross(self) -> None:
        """Add Death Cross SMA50 over SMA200"""

        if self.total_periods < 200:
            self.df["deathcross"] = False
            return

        if "sma50" not in self.df:
            self.add_sma(50)

        if "sma200" not in self.df:
            self.add_sma(200)

        self.df["deathcross"] = self.df["sma50"] < self.df["sma200"]

    def add_elder_ray_index(self, period: int = 14) -> None:
        """Add Elder Ray Index"""

        # if "ema13" not in self.df:
        #    self.add_ema(13)

        # self.df["elder_ray_bull"] = self.df["high"] - self.df["ema13"]
        # self.df["elder_ray_bear"] = self.df["low"] - self.df["ema13"]
        df_eri = ta.eri(high=self.df["high"], close=self.df["close"], low=self.df["low"], interval=period, fillna=0)
        df_eri.fillna(0, inplace=True)
        df_eri.columns = ["elder_ray_bull", "elder_ray_bear"]
        self.df["elder_ray_bull"] = df_eri["elder_ray_bull"]
        self.df["elder_ray_bear"] = df_eri["elder_ray_bear"]

        # bear power’s value is negative but increasing (i.e. becoming less bearish)
        # bull power’s value is increasing (i.e. becoming more bullish)
        self.df["eri_buy"] = ((self.df["elder_ray_bear"] < 0) & (self.df["elder_ray_bear"] > self.df["elder_ray_bear"].shift(1))) | (
            (self.df["elder_ray_bull"] > self.df["elder_ray_bull"].shift(1))
        )

        # bull power’s value is positive but decreasing (i.e. becoming less bullish)
        # bear power’s value is decreasing (i.e., becoming more bearish)
        self.df["eri_sell"] = ((self.df["elder_ray_bull"] > 0) & (self.df["elder_ray_bull"] < self.df["elder_ray_bull"].shift(1))) | (
            (self.df["elder_ray_bear"] < self.df["elder_ray_bear"].shift(1))
        )

    def add_support_resistance_levels(self, window: int = 20) -> DataFrame:
        # Calculate the rolling mean of the closing price using a window size of 20
        self.df["rolling_mean"] = self.df["close"].rolling(window=window).mean()

        # Calculate the rolling standard deviation of the closing price using a window size of 20
        self.df["rolling_std"] = self.df["close"].rolling(window=window).std()

        # Set the support level to the rolling mean minus two times the rolling standard deviation
        self.df["support"] = self.df["rolling_mean"] - 2 * self.df["rolling_std"]

        # Set the resistance level to the rolling mean plus two times the rolling standard deviation
        self.df["resistance"] = self.df["rolling_mean"] + 2 * self.df["rolling_std"]

    def get_support_resistance_levels(self) -> Series:
        """Calculate the Support and Resistance Levels"""

        self.levels = []
        self._calculate_support_resistence_levels()
        levels_ts = {}
        for level in self.levels:
            levels_ts[self.df.index[level[0]]] = level[1]
        # add the support levels to the DataFrame
        return Series(levels_ts, dtype="float64")

    def print_support_resistance_levels_v1(self, price: float = 0) -> None:
        if isinstance(price, int) or isinstance(price, float):
            df = self.get_support_resistance_levels()

            if len(df) > 0:
                df_last = df.tail(1)
                if float(df_last[0]) < price:
                    RichText.notify(f"Support level of {str(df_last[0])} formed at {str(df_last.index[0])}", self.app, "normal")
                elif float(df_last[0]) > price:
                    RichText.notify(f"Resistance level of {str(df_last[0])} formed at {str(df_last.index[0])}", self.app, "normal")
                else:
                    RichText.notify(f"Support/Resistance level of {str(df_last[0])} formed at {str(df_last.index[0])}", self.app, "normal")

    def print_support_resistance_levels_v2(self, price: float = 0) -> None:
        if isinstance(price, int) or isinstance(price, float):
            if "support" not in self.df.columns and "resistance" not in self.df.columns:
                self.add_support_resistance_levels()

            support, resistance = self.df[["support", "resistance"]].tail(1).values[0]
            RichText.notify(f"Support level is {str(round(support, 4))} and Resistance level is {str(round(resistance, 4))}", self.app, "normal")

    def get_resistance(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                sr = self.get_support_resistance_levels()
                for r in sr.sort_values():
                    if r > price:
                        return r

        return price

    def get_fibonacci_upper(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                fb = self.get_fibonacci_retracement_levels()
                for f in fb.values():
                    if f > price:
                        return f

        return price

    def get_trade_exit(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                r = self.get_resistance(price)
                f = self.get_fibonacci_upper(price)
                if price < r and price < f:
                    r_margin = ((r - price) / price) * 100
                    f_margin = ((f - price) / price) * 100

                    if r_margin > 1 and f_margin > 1 and r <= f:
                        return r
                    elif r_margin > 1 and f_margin > 1 and f <= r:
                        return f
                    elif r_margin > 1 and f_margin < 1:
                        return r
                    elif f_margin > 1 and r_margin < 1:
                        return f

        return price

    def print_support_resistance_fibonacci_levels(self, price: float = 0) -> str:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                sr = self.get_support_resistance_levels()

                s = price
                for r in sr.sort_values():
                    if r > price:
                        fb = self.get_fibonacci_retracement_levels()

                        low = price
                        for b in fb.values():
                            if b > price:
                                return f"support: {str(s)}, resistance: {str(r)}, fibonacci (l): {str(low)}, fibonacci (u): {str(b)}"
                            else:
                                low = b

                        break
                    else:
                        s = r

                if len(sr) > 1 and sr.iloc[-1] < price:
                    fb = self.get_fibonacci_retracement_levels()

                    low = price
                    for b in fb.values():
                        if b > price:
                            return f"support: {str(sr.iloc[-1])}, fibonacci (l): {str(low)}, fibonacci (u): {str(b)}"
                        else:
                            low = b

        return ""

    def add_bbands_buy_signals(self) -> None:
        """Adds the Bollinger Bands buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if "close" not in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df["close"].dtype == "float64" and not self.df["close"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        if "bb20_upper" not in self.df.columns:
            self.add_bollinger_bands(20)

        # true if close is above the upper band
        self.df["closegtbb20_upper"] = self.df.close > self.df.bb20_upper
        # true if the current frame is where close crosses over above
        self.df["closegtbb20_upperco"] = self.df.closegtbb20_upper.ne(self.df.closegtbb20_upper.shift())
        self.df.loc[self.df["closegtbb20_upper"] == False, "closegtbb20_upperco"] = False  # noqa: E712

        # true if close is below the middle band
        self.df["closeltbb20_mid"] = self.df.close < self.df.bb20_mid
        # true if the current frame is where close crosses over below
        self.df["closeltbb20_midco"] = self.df.closeltbb20_mid.ne(self.df.closeltbb20_mid.shift())
        self.df.loc[self.df["closeltbb20_mid"] == False, "closeltbb20_midco"] = False  # noqa: E712

        # true if close is below the lower band
        self.df["closeltbb20_lower"] = self.df.close < self.df.bb20_lower
        # true if the current frame is where close crosses over below
        self.df["closeltbb20_lowerco"] = self.df.closeltbb20_lower.ne(self.df.closeltbb20_lower.shift())
        self.df.loc[self.df["closeltbb20_lower"] == False, "closeltbb20_lowerco"] = False  # noqa: E712

        # true if close is below the middle band
        self.df["closegtbb20_mid"] = self.df.close > self.df.bb20_mid
        # true if the current frame is where close crosses over below
        self.df["closegtbb20_midco"] = self.df.closegtbb20_mid.ne(self.df.closegtbb20_mid.shift())
        self.df.loc[self.df["closegtbb20_mid"] == False, "closegtbb20_midco"] = False  # noqa: E712

    def add_ema_buy_signals(self) -> None:
        """Adds the EMA12/EMA26 buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if "close" not in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df["close"].dtype == "float64" and not self.df["close"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        if "ema8" not in self.df.columns:
            self.add_ema(8)

        if "ema12" not in self.df.columns:
            self.add_ema(12)

        if "ema26" not in self.df.columns:
            self.add_ema(26)

        # true if EMA8 is above the EMA12
        self.df["ema8gtema12"] = self.df.ema8 > self.df.ema12
        # true if the current frame is where EMA8 crosses over above
        self.df["ema8gtema12co"] = self.df.ema8gtema12.ne(self.df.ema8gtema12.shift())
        self.df.loc[self.df["ema8gtema12"] == False, "ema8gtema12co"] = False  # noqa: E712

        # true if the EMA8 is below the EMA12
        self.df["ema8ltema12"] = self.df.ema8 < self.df.ema12
        # true if the current frame is where EMA8 crosses over below
        self.df["ema8ltema12co"] = self.df.ema8ltema12.ne(self.df.ema8ltema12.shift())
        self.df.loc[self.df["ema8ltema12"] == False, "ema8ltema12co"] = False  # noqa: E712

        # true if EMA12 is above the EMA26
        self.df["ema12gtema26"] = self.df.ema12 > self.df.ema26
        # true if the current frame is where EMA12 crosses over above
        self.df["ema12gtema26co"] = self.df.ema12gtema26.ne(self.df.ema12gtema26.shift())
        self.df.loc[self.df["ema12gtema26"] == False, "ema12gtema26co"] = False  # noqa: E712

        # true if the EMA12 is below the EMA26
        self.df["ema12ltema26"] = self.df.ema12 < self.df.ema26
        # true if the current frame is where EMA12 crosses over below
        self.df["ema12ltema26co"] = self.df.ema12ltema26.ne(self.df.ema12ltema26.shift())
        self.df.loc[self.df["ema12ltema26"] == False, "ema12ltema26co"] = False  # noqa: E712

    def add_sma_buy_signals(self) -> None:
        """Adds the SMA50/SMA200 buy and sell signals to the DataFrame"""

        if self.total_periods < 200:
            raise ValueError("Period is out of range")

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if "close" not in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df["close"].dtype == "float64" and not self.df["close"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        if not "sma50" or "sma200" not in self.df.columns:
            self.add_sma(50)
            self.add_sma(200)

        # true if SMA5 is above the SMA8
        self.df["sma5gtsma8"] = self.df.sma5 > self.df.sma8
        # true if the current frame is where SMA5 crosses over above
        self.df["sma5gtsma8co"] = self.df.sma5gtsma8.ne(self.df.sma5gtsma8.shift())
        self.df.loc[self.df["sma5gtsma8"] == False, "sma5gtsma8co"] = False  # noqa: E712

        # true if the SMA5 is below the SMA8
        self.df["sma5ltsma8"] = self.df.sma5 < self.df.sma8
        # true if the current frame is where SMA5 crosses over below
        self.df["sma5ltsma8co"] = self.df.sma5ltsma8.ne(self.df.sma5ltsma8.shift())
        self.df.loc[self.df["sma5ltsma8"] == False, "sma5ltsma8co"] = False  # noqa: E712

        # true if SMA8 is above the SMA13
        self.df["sma8gtsma13"] = self.df.sma8 > self.df.sma13
        # true if the current frame is where SMA8 crosses over above
        self.df["sma8gtsma13co"] = self.df.sma8gtsma13.ne(self.df.sma8gtsma13.shift())
        self.df.loc[self.df["sma8gtsma13"] == False, "sma8gtsma13co"] = False  # noqa: E712

        # true if the SMA8 is below the SMA13
        self.df["sma8ltsma13"] = self.df.sma8 < self.df.sma13
        # true if the current frame is where SMA8 crosses over below
        self.df["sma8ltsma13co"] = self.df.sma8ltsma13.ne(self.df.sma8ltsma13.shift())
        self.df.loc[self.df["sma8ltsma13"] == False, "sma8ltsma13co"] = False  # noqa: E712

        # true if SMA50 is above the SMA200
        self.df["sma50gtsma200"] = self.df.sma50 > self.df.sma200
        # true if the current frame is where SMA50 crosses over above
        self.df["sma50gtsma200co"] = self.df.sma50gtsma200.ne(self.df.sma50gtsma200.shift())
        self.df.loc[self.df["sma50gtsma200"] == False, "sma50gtsma200co"] = False  # noqa: E712

        # true if the SMA50 is below the SMA200
        self.df["sma50ltsma200"] = self.df.sma50 < self.df.sma200
        # true if the current frame is where SMA50 crosses over below
        self.df["sma50ltsma200co"] = self.df.sma50ltsma200.ne(self.df.sma50ltsma200.shift())
        self.df.loc[self.df["sma50ltsma200"] == False, "sma50ltsma200co"] = False  # noqa: E712

    def add_macd_buy_signals(self) -> None:
        """Adds the MACD/Signal buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if "close" not in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df["close"].dtype == "float64" and not self.df["close"].dtype == "int64":
            raise AttributeError("Pandas DataFrame 'close' column not int64 or float64.")

        if not "macd" or "signal" not in self.df.columns:
            self.add_macd()
            self.add_obv()

        # true if MACD is above the Signal
        self.df["macdgtsignal"] = self.df.macd > self.df.signal
        # true if the current frame is where MACD crosses over above
        self.df["macdgtsignalco"] = self.df.macdgtsignal.ne(self.df.macdgtsignal.shift())
        self.df.loc[self.df["macdgtsignal"] == False, "macdgtsignalco"] = False  # noqa: E712

        # true if the MACD is below the Signal
        self.df["macdltsignal"] = self.df.macd < self.df.signal
        # true if the current frame is where MACD crosses over below
        self.df["macdltsignalco"] = self.df.macdltsignal.ne(self.df.macdltsignal.shift())
        self.df.loc[self.df["macdltsignal"] == False, "macdltsignalco"] = False  # noqa: E712

    def get_fibonacci_retracement_levels(self, price: float = 0) -> dict:
        # validates price is numeric
        if not isinstance(price, int) and not isinstance(price, float):
            raise TypeError("Optional price is not numeric.")

        price_min = self.df.close.min()
        price_max = self.df.close.max()

        diff = price_max - price_min

        data = {}

        if price != 0 and (price <= price_min):
            data["ratio1"] = float(self._truncate(price_min, 2))
        elif price == 0:
            data["ratio1"] = float(self._truncate(price_min, 2))

        if price != 0 and (price > price_min) and (price <= (price_max - 0.768 * diff)):
            data["ratio1"] = float(self._truncate(price_min, 2))
            data["ratio0_768"] = float(self._truncate(price_max - 0.768 * diff, 2))
        elif price == 0:
            data["ratio0_768"] = float(self._truncate(price_max - 0.768 * diff, 2))

        if price != 0 and (price > (price_max - 0.768 * diff)) and (price <= (price_max - 0.618 * diff)):
            data["ratio0_768"] = float(self._truncate(price_max - 0.768 * diff, 2))
            data["ratio0_618"] = float(self._truncate(price_max - 0.618 * diff, 2))
        elif price == 0:
            data["ratio0_618"] = float(self._truncate(price_max - 0.618 * diff, 2))

        if price != 0 and (price > (price_max - 0.618 * diff)) and (price <= (price_max - 0.5 * diff)):
            data["ratio0_618"] = float(self._truncate(price_max - 0.618 * diff, 2))
            data["ratio0_5"] = float(self._truncate(price_max - 0.5 * diff, 2))
        elif price == 0:
            data["ratio0_5"] = float(self._truncate(price_max - 0.5 * diff, 2))

        if price != 0 and (price > (price_max - 0.5 * diff)) and (price <= (price_max - 0.382 * diff)):
            data["ratio0_5"] = float(self._truncate(price_max - 0.5 * diff, 2))
            data["ratio0_382"] = float(self._truncate(price_max - 0.382 * diff, 2))
        elif price == 0:
            data["ratio0_382"] = float(self._truncate(price_max - 0.382 * diff, 2))

        if price != 0 and (price > (price_max - 0.382 * diff)) and (price <= (price_max - 0.286 * diff)):
            data["ratio0_382"] = float(self._truncate(price_max - 0.382 * diff, 2))
            data["ratio0_286"] = float(self._truncate(price_max - 0.286 * diff, 2))
        elif price == 0:
            data["ratio0_286"] = float(self._truncate(price_max - 0.286 * diff, 2))

        if price != 0 and (price > (price_max - 0.286 * diff)) and (price <= price_max):
            data["ratio0_286"] = float(self._truncate(price_max - 0.286 * diff, 2))
            data["ratio0"] = float(self._truncate(price_max, 2))
        elif price == 0:
            data["ratio0"] = float(self._truncate(price_max, 2))

        if price != 0 and (price < (price_max + 0.272 * diff)) and (price >= price_max):
            data["ratio0"] = float(self._truncate(price_max, 2))
            data["ratio1_272"] = float(self._truncate(price_max + 0.272 * diff, 2))
        elif price == 0:
            data["ratio1_272"] = float(self._truncate(price_max + 0.272 * diff, 2))

        if price != 0 and (price < (price_max + 0.414 * diff)) and (price >= (price_max + 0.272 * diff)):
            data["ratio1_272"] = float(self._truncate(price_max, 2))
            data["ratio1_414"] = float(self._truncate(price_max + 0.414 * diff, 2))
        elif price == 0:
            data["ratio1_414"] = float(self._truncate(price_max + 0.414 * diff, 2))

        if price != 0 and (price < (price_max + 0.618 * diff)) and (price >= (price_max + 0.414 * diff)):
            data["ratio1_618"] = float(self._truncate(price_max + 0.618 * diff, 2))
        elif price == 0:
            data["ratio1_618"] = float(self._truncate(price_max + 0.618 * diff, 2))

        return data

    def save_csv(self, filename: str = "tradingdata.csv") -> None:
        """Saves the DataFrame to an uncompressed CSV."""

        p = compile(r"^[\w\-. ]+$")
        if not p.match(filename):
            raise TypeError("Filename required.")

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        try:
            self.df.to_csv(filename)
        except OSError:
            RichText.notify(f"Unable to save: {filename}", self.app, "critical")

    def _calculate_support_resistence_levels(self):
        """Support and Resistance levels. (private function)"""

        for i in range(2, self.df.shape[0] - 2):
            if self._is_support(self.df, i):
                level = self.df["low"][i]
                if self._is_far_from_level(level):
                    self.levels.append((i, level))
            elif self._is_resistance(self.df, i):
                level = self.df["high"][i]
                if self._is_far_from_level(level):
                    self.levels.append((i, level))
        return self.levels

    def _is_support(self, df, i) -> bool:
        """Is support level? (private function)"""

        try:
            c1 = df["low"][i] < df["low"][i - 1]
            c2 = df["low"][i] < df["low"][i + 1]
            c3 = df["low"][i + 1] < df["low"][i + 2]
            c4 = df["low"][i - 1] < df["low"][i - 2]
            support = c1 and c2 and c3 and c4
            return support
        except Exception:
            support = False
            return support

    def _is_resistance(self, df, i) -> bool:
        """Is resistance level? (private function)"""

        try:
            c1 = df["high"][i] > df["high"][i - 1]
            c2 = df["high"][i] > df["high"][i + 1]
            c3 = df["high"][i + 1] > df["high"][i + 2]
            c4 = df["high"][i - 1] > df["high"][i - 2]
            resistance = c1 and c2 and c3 and c4
            return resistance
        except Exception:
            resistance = False
            return resistance

    def _is_far_from_level(self, level) -> float:
        """Is far from support level? (private function)"""

        s = mean(self.df["high"] - self.df["low"])
        return np_sum([abs(level - x) < s for x in self.levels]) == 0

    def _truncate(self, f, n) -> float:
        return floor(f * 10**n) / 10**n

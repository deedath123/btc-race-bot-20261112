"""cbBTC trend rider for the make.fun 24h bars-replay race.

Long only, one position, minute bars. The bot reads every batch the harness
sends, keeps the close of every bar it has seen, and trades rarely: a full
round trip costs about 26 bps in fee, slippage and price impact, so only a
confirmed move is worth paying for.

Entry (flat, off cooldown): the fast EMA is above the slow EMA and the
trailing 60-bar momentum is above +0.55%. The buy spends all cash and fills
at the next bar's open.
Exit (first that fires, after a minimum hold): the trailing momentum falls
below -0.15%, the fast EMA crosses under the slow EMA, the close falls 0.80%
under the peak close since entry (trailing stop), or 0.60% under the entry
mark (hard stop). A 30-bar cooldown follows every exit.

Everything is integer or float arithmetic on the bars seen so far: no clock,
no randomness, no files, so two runs of the same window give the same orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
FAST_SPAN = 45
SLOW_SPAN = 80
LOOKBACK = 60
THETA = 0.0055
THETA_DN = 0.0015
TRAIL = 0.008
HARD_STOP = 0.006
COOLDOWN_BARS = 30
MIN_HOLD_BARS = 10
MAX_SLIPPAGE_BPS = 150
MIN_NOTIONAL = 1_000_000


class Ema:
    """EMA seeded with the mean of its first span of closes."""

    __slots__ = ("span", "warm", "value")

    def __init__(self, span):
        self.span = span
        self.warm = []
        self.value = None

    def push(self, x):
        if self.value is None:
            self.warm.append(x)
            if len(self.warm) == self.span:
                self.value = sum(self.warm) / self.span
            return self.value
        k = 2 / (self.span + 1)
        self.value += k * (x - self.value)
        return self.value


class Rider:
    def __init__(self):
        self.fast = Ema(FAST_SPAN)
        self.slow = Ema(SLOW_SPAN)
        self.closes = []
        self.peak = None
        self.entry_mark = None
        self.cooldown = 0
        self.held_bars = 0

    def on_batch(self, state, batch):
        bar = None
        for b in batch["bars"]:
            if b["symbol"] == SYMBOL:
                bar = b
        if bar is None:
            return []
        close = int(bar["c"])
        self.closes.append(close)
        f = self.fast.push(close)
        s = self.slow.push(close)
        if f is None or s is None or len(self.closes) <= LOOKBACK:
            return []
        momentum = self.closes[-1] / self.closes[-1 - LOOKBACK] - 1
        holding = state.positions.get(SYMBOL)
        orders = []
        if holding is not None and holding.qty > 0:
            self.held_bars += 1
            if self.peak is None or close > self.peak:
                self.peak = close
            if self.held_bars >= MIN_HOLD_BARS:
                sell = False
                if momentum < -THETA_DN or f < s:
                    sell = True
                elif self.peak is not None and close <= self.peak * (1 - TRAIL):
                    sell = True
                elif self.entry_mark is not None and close <= self.entry_mark * (1 - HARD_STOP):
                    sell = True
                if sell:
                    orders.append({
                        "side": "sell",
                        "symbol": SYMBOL,
                        "qty": holding.qty,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    self.peak = None
                    self.entry_mark = None
                    self.held_bars = 0
                    self.cooldown = COOLDOWN_BARS
            return orders
        if state.warming_up:
            return []
        if self.cooldown > 0:
            self.cooldown -= 1
            return []
        if f > s and momentum > THETA:
            stake = state.cash
            if stake >= MIN_NOTIONAL:
                orders.append({
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": stake,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                })
                self.entry_mark = close
                self.peak = close
                self.held_bars = 0
        return orders


RIDER = Rider()
makefun_bars.run(RIDER.on_batch)

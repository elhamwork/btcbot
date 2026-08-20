"""backtest/portfolio.py -- tracks bankroll, trades, equity curve."""


class Portfolio:
    def __init__(self, starting_bankroll):
        self.bankroll = starting_bankroll
        self.starting_bankroll = starting_bankroll
        self.trades = []          # list of dicts, one per executed trade
        self.equity_curve = []    # list of (timestamp, bankroll) after each trade

    def can_afford(self, cost):
        return cost <= self.bankroll

    def record_trade(self, trade):
        self.bankroll += trade["pnl"]
        trade["bankroll_after"] = self.bankroll
        self.trades.append(trade)
        self.equity_curve.append((trade["timestamp"], self.bankroll))

    def to_frame(self):
        import pandas as pd
        return pd.DataFrame(self.trades)

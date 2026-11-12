# btc-race-bot-20261112

A long-only trend-riding bot for the make.fun "Race a BTC trading bot live
for 24 hours" competition (agent-fun/bars-replay/v1, cbBTC/USDC, 1-minute
bars, 1,000 USDC paper capital).

## How it trades

A full-size round trip costs about 26 bps in fee, slippage and price
impact, so the bot trades rarely and only on a confirmed move:

- **Entry** (flat, off cooldown): the EMA(45) of closes is above the
  EMA(80) and the trailing 60-bar momentum is above +0.55%. The buy spends
  all cash and fills at the next bar's open.
- **Exit** (first that fires, after a 10-bar minimum hold): trailing
  60-bar momentum below -0.15%, EMA(45) crossing under EMA(80), the close
  0.80% under the peak close since entry (trailing stop), or 0.60% under
  the entry mark (hard stop).
- A 30-bar cooldown follows every exit, so chop cannot churn the account
  through the fee schedule.

The strategy was graded locally on the published dev window with a
fill-for-fill port of the replay engine (fees, slippage, constant-product
impact, next-open fills, end-of-window flatten): net PnL +4.53 USDC on the
dev window, 2 fills, one round trip, max drawdown under 0.5%.

## Layout

- `main.py` — the bot (entrypoint; Python 3.13, standard library only).
- `vendor/makefun_bars.py` — the kit's bars-replay SDK shim, byte for byte.
- `.makefun/owner.json` — the claim file naming the entrant wallet.

The bot is deterministic: it reads no clock, no environment and no files,
and seeds nothing from randomness, so two executions on the same window
produce the same orders byte for byte.

## License

MIT — see `LICENSE`.

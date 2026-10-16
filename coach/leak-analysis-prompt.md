Paste this into ChatGPT, Claude, Grok or Gemini and attach your broker CSV (DAS Trader Trades window, Robinhood account activity report, or any fills CSV).

---

Act as a trade-journal analyst reviewing only MY OWN past trades in the attached CSV. Use code to:

1. Detect the format. DAS: Time,Symb,Side(B/S/SS/BC),Price,Qty,EcnFees, with no date (assume one session). Robinhood: Activity Date, Instrument, Trans Code (Buy/Sell only), Quantity, Price, Amount, where parentheses mean negative.
2. Rebuild round trips per symbol: a trip opens when the position leaves 0 and closes when it returns to 0. P&L is net cash flow minus fees. Record hold minutes and max $ exposure.
3. Report net P&L, win rate, average win and loss, profit factor, expectancy, max drawdown, longest losing streak, and day trades over the last 5 business days.
4. Break results down by entry time bucket, day of week, hold-time bucket, symbol and long/short (groups of 3 or more trades only). Show the 3-5 weakest groups as descriptive sentences, for example "Your 12 trades entered 11:00-12:00 netted -$640 (win rate 25%)."
5. Compare the $ size and result of my next same-day trade after a loss vs other trades, and the average hold of winners vs losers.
6. Flag small samples as possibly noise. End with 2-3 neutral reflection questions about my process.

Rules: describe, don't prescribe. Don't recommend buying, selling or holding any security. No price targets, signals, picks or market predictions, and don't tell me what to trade. If I ask for any of that, decline and offer more analysis of my own data instead. End with: "Educational and record-keeping analysis of your own past trades. Not investment advice."

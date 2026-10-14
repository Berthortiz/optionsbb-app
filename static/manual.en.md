# User manual · Options BB Command Center

> Educational content. This is not financial or tax advice. Trading stocks and options involves risk of loss.

## 1. What this app is
Options BB Command Center brings together in one place: strategy signals on your stocks, an analysis of each stock, the **Covered Call** module (calculator and simulator), the **401(k) and retirement** module, the flow from options volume to open interest, strategy rankings, a video library and more. What you see depends on your subscription **plan**.

## 2. First steps
1. **Create your account**: choose the plan you want to try for free (7 days, no card).
2. **Answer the Home questionnaire** (4 questions). The app shows you a path with the modules that suit you best according to your profile: Conservative, Moderate, Growth or Active.
3. When the trial ends, go to **Plans** and subscribe to keep using the app. Without an active subscription you will only see Plans and Account.

## 3. What each plan includes
| Module | Basic | Intermediate | Advanced |
|---|---|---|---|
| Home, Where do I start?, Command Center, My lists, Analysis | Yes | Yes | Yes |
| Covered Call | Yes | Yes | Yes |
| 401(k) and retirement | Yes | Yes | Yes |
| Strategies | 1 bullish + 1 bearish | 6 + 6 | 10 + 10 |
| My ETF (3 Optionsbb ETFs and your own), Dividends, What would have happened if…? | Yes | Yes | Yes |
| Options calculator | No | Templates | Templates + free legs |
| Sectors, Ranking, Performance | No | Yes | Yes |
| OI Flow | No | No | Yes |
| Earnings history | No | No | Yes |
| Gamma exposure (GEX) | No | No | Yes |
| Leveraged + Covered Call | No | No | Yes |
| Mentor signals | No | No | Yes |
| Custom strategies | No | No | 2 |
| Videos | Basic level | Up to intermediate level | All |

The menu only shows what your plan includes (so it is shorter and clearer). You can see the rest in **Plans**.

## 4. Command Center
- **Chart**: type a symbol and choose the range (1D, 5D, 1M, 3M, 1Y). Arrows mark recent signals of the chosen strategies.
- **Bullish / bearish strategy**: choose one strategy on each side. The central panel draws the pattern and explains the rule. The green or red number shows how many stocks have a signal now.
- **Dynamic lists**: stocks with a signal now, with price and % change. Tap a symbol to see it on the chart.
- **Highest-volume contracts**: the most traded option contracts right now.
- **Watchlists (Optionsbb)**: now lives in its own menu (see section 4b).

## 4b. My lists
Three boxes of 10 stocks: **Optionsbb List · Low risk**, **Moderate risk** and **High risk**. Each box has two tabs: **Optionsbb list** (Optionsbb's selection) and **My list** (yours, up to 10 stocks per risk level; you can add, remove or press *Copy Optionsbb list* to start from it). By default you see the change for **Today**; tick the periods you want: 7, 15, 30, 90, 180 and 360 days. From each row you open the **Analysis**.
When you add a company from **Analysis** (the *+ My list* button), you choose the risk level and the app takes you to **My lists** so you can see it added.

## 4c. Where do I start?
Welcome screen: which platform to use (**Thinkorswim by Charles Schwab**, with paperMoney to practice without risk), how much money is needed (100 shares per covered-call contract) and what can realistically be expected. It includes the myths of "get rich in 3 weeks". On **Home** you will also see a different illustration depending on your plan.

## 5. Stock analysis
Type a symbol and press **Analyze**. You will see:
- **Change** for Today, 7, 15, 30, 90 and 360 days.
- **Financial summary**: 90-day chart, position within the 52-week range, distance from the high and low, annual volatility, largest drop of the last year, RSI, moving averages, trend and volume against its average.
- **By timeframe** (5 min, 15 min, 30 min, 1 hour and daily): trend, RSI and the strategies with the best track record on **that** stock. A NOW label indicates the strategy is active at this moment.
- Buttons to view the chart, add to your list and **open the Covered Call with that stock already loaded**.

> P/E, earnings, dividends and market cap will be added when the Schwab account is linked. Today the summary comes from price, volume and options.

## 6. Covered Call
A covered call consists of selling one call option contract for every 100 shares you already own. You collect a **premium** in exchange for agreeing to sell your shares at the **strike** if at expiration the price is above it.

### 6.1 Calculator
1. Enter the current price, your cost per share, the number of shares (multiples of 100) and the dates.
2. Paste the **calls** chain for the expiration (columns Strike, Bid, Ask and optionally Delta, Volume and OI). In Thinkorswim: open the chain, select the calls rows, copy and paste. You can also use the **A strike by hand** option.
3. Choose which strike to sell: **1st** (the one immediately above the price), **5th** or another number.
4. Press **Calculate**.

It shows you, in words: how much you collect, **at what price you get assigned**, how much it has risen or must rise, your maximum profit, what you earn if the stock doesn't move, the breakeven and a chart. The table of all strikes lets you tap any of them to recalculate. A red spread means the bid and the ask are far apart or there is little open interest: the real premium may be lower.

**Premium at Bid or at the midpoint?** Bid is the conservative choice. The midpoint is the usual result with a limit order, but it may take longer to fill.

### 6.2 How to choose the strike
- **Immediate strike above**: you collect more premium, but you almost give up the upside and are more likely to be assigned.
- **5th strike above the price**: you collect less, but you let the stock rise before hitting your profit cap. If you are assigned, the maximum profit is usually larger.
- The calculator compares both and tells you **above which price the 5th strike wins**.
- Check whether there are **earnings** before expiration: the price can jump beyond any strike.

### 6.3 Monthly simulator
1. Enter the stock, the shares, the cost, the strike rule and **for how many months** you want to simulate (1 to 36).
2. Press **Create the months**. For each month enter sale date, expiration, price when selling, the calls chain, the strike you sold (optional) and the price at expiration.
3. Press **Simulate**. If you are assigned in a month, the app assumes you **rebuy the shares** at the next month's price and keep selling.
4. **Compare 1st vs 5th strike** runs both scenarios with the same data.
5. **Save simulation** puts it in the Saved tab.

Result: total profit, return and annualized, premiums collected, times assigned, comparison with **just holding the stock**, largest drop and the upside you gave up.

> Assignment is evaluated only at expiration. In practice it can happen earlier, especially before a dividend.

## 7. 401(k) and retirement
The goal of this module is to show that **idle money loses purchasing power** and to compare paths with your own numbers.

- **Projection**: compares **Cash**, **Stocks** and **Stocks + Covered Call**, in future dollars or in today's dollars. If you enter your salary and what your employer contributes, it calculates that contribution (free money you shouldn't miss).
- **Retirement goal**: given the monthly income you want (in today's dollars), it calculates how much you need to save each month in cash and how much by investing.
- **Fees**: how much it costs you to pay 1 % instead of 0.1 % in annual fees.
- **My portfolio**: save your positions, see their value and gain, and press **Covered Call** on a row to open the calculator with that stock loaded.

All returns are **assumptions you edit**, not promises. 2026 IRS limits: employee in a 401(k) $24,500 and IRA $7,500 (they change every year).

> A normal 401(k) offers a fixed menu of funds. Options (like covered calls) can only be used if your plan has a brokerage window and your broker approves options. In an IRA it is more common. Check with your plan or your broker.

## 7b. My ETF
At the top you have the **3 Optionsbb ETFs** (Low risk, Moderate risk and High risk). You choose one and next to it you see its composition and the number of shares. Those ETFs **are fixed**: you only change the **amount to invest** and the shares adjust in the same proportion; only the administrator can change their stocks. For a different mix, press **Create my ETF from this one**, or create a new one and use **Add shares from another ETF** (from the 3 Optionsbb ETFs or your own).
Build your own ETF: type the symbol, choose whether you enter **shares** or **dollars** and press *Add*. You can have up to 5 ETFs with 20 stocks each.
- **Composition**: donut chart with the logo and the **% weight** of each stock (by current value). If the logo doesn't load, you will see the initials.
- **Performance table**: choose the period (30 to 360 days), how many % out of the money you sell the call and, if you want, your own volatility. For each stock you will see: *without covered call*, *covered call (income)* and the **sum of both**, as well as whether it was **not moving** or **moving**. Below, subtotals and the ETF total.
- **Important**: the covered call only covers lots of **100 shares** (if you have 250, you cover 200). Premiums are estimated with a model; use it to compare, not as a promise.

## 7c. What would have happened if…?
Examples like **BYND** (a stock that falls month after month) and **MSFT** (a solid company that stays flat or pulls back): how much the covered call would have generated and what part of the loss it would have offset. The examples use illustrative prices that **you can change** to the real ones; you can also use the history of any symbol.

## 7d. Leveraged + Covered Call (Advanced)
NVDL, AMDL, TSLL, TQQQ and other leveraged instruments with covered calls. It includes risk warnings (daily reset and volatility decay), a simulator and a decay calculator. These are **high-risk** instruments: only with money you can afford to lose.

## 7e. Dividends
A table of the stocks in your lists with their annual yield, the payment per share, the frequency and the annual income with 100 shares. On the Intermediate and Advanced plans you can open a stock's **payment history** and its annual growth. With 100 shares you collect the dividend and can also sell a covered call each month: two incomes on the same shares. Payment data requires the data keys set up by the administrator; in DEMO mode it is simulated.

## 7f. Language
At the top right choose **ES**, **EN** or **PT**. Menus, titles, tables, messages and this manual are translated. Limitations: the translation was done by Claude without review by a native speaker; sector names and some symbols stay in English; the texts you write yourself (ETF names, strategies, videos) are not translated.

## 7g. Referrals
Open **Referidos** (Referrals): copy your code or link. When someone you refer **pays** their subscription you get 20% off the following month. 10 paid referrals = 6 free months of Advanced; 20 = one free year.

## 7h. What's new in 3.1
- **Dividends**: calculate by number of shares or amount to invest.
- **Earnings**: last 12 reports with trend.
- **What if…?**: pick a case study from the list or save your own.
- **Custom strategy**: golden cross, bullish/bearish breakout, doji and engulfing candle.
- **Sectors**: the administrator can add or remove companies.

## 8. Tools
### Options calculator (Intermediate and Advanced)
Choose a strategy (long call, long put, covered call, cash-secured put, protective put, spreads, straddle, iron condor), the symbol or the price, the volatility and the days to expiration. You will see the **cost or credit**, the **maximum profit and loss**, the **breakeven points**, the **probability of profit** and the **Greeks**, with a chart at expiration and the "today" curve. On Advanced you can build up to 6 **free legs** and type your own premium. Premiums are estimated with Black-Scholes.
### Earnings history (Advanced)
Choose a stock and you will see how the price moved on each previous report: opening gap, the day's change, range and next day, plus the average move. Everything is calculated **automatically** with the report dates (Finnhub) and the prices (Schwab); nothing is entered by hand.
### Gamma exposure – GEX (Advanced)
Shows per strike the gamma exposure of calls and puts for an expiration, the **call wall** (possible resistance), the **put wall** (possible support), the **gamma flip** and whether the regime is positive gamma (calmer moves) or negative gamma (wider moves). It is an estimate with an assumption about dealer positioning.

## 8b. Market
### OI Flow (Advanced only)
Compares a day's options volume with the next morning's open interest. If OI rises a lot relative to the volume, new positions were probably **opened**; if it falls, they were **closed**. It does not distinguish buying from selling.
### Sectors
The key stocks of each sector with their price, % change, put/call ratio and signals.
### Ranking
Shows the strategies **most effective by timeframe** (5 min, 15 min, 30 min, 1 hour and daily). Each signal is measured by the price change 5 candles later. You will see signals, hit rate %, average return, profit factor, **on which stocks it is active now** and **on which it has worked best**. Only strategies with 20 or more signals are included.
### Performance
Upload the report exported from Thinkorswim (Strategy Report) and see how effective each strategy was in the backtest.

## 9. Signals (Advanced)
- **Strategy catalog**: rule-based strategies, with the list of stocks that meet them now. Tap **Follow** to save them.
- **My selection**: gathers the strategies you follow (base, catalog or your own) with their signals. Tick or untick in "Choose what to follow".
- **My strategies**: create up to 2 of your own strategies with the rule builder: moving-average crossovers, breakouts, RSI, volume, candle color and price change. They trigger when **all** the conditions are met on the same 5-minute candle.

## 10. Videos
Video library from the Options BB YouTube channel. Filter by category or search by title. Videos of a higher level appear with a lock.

## 11. Plans and account
- **Plans**: compare and subscribe. You can change plans whenever you want.
- **Account**: your status (trial, active, expired), the renewal date, managing the subscription and signing out.

## 12. For the administrator
- **Starting the app**: open a console in the folder (in Explorer, click the address bar, type `cmd` and Enter) and run `python server.py`. Open `http://127.0.0.1:8080`. Create your user with `python server.py create-admin you@email.com`.
- **Users** (Account): activate paid days, extend the trial, revoke, change the plan or make administrator.
- **Prices**: type them on the Plans screen.
- **Videos**: add by YouTube link, with category and minimum plan.
- **Signal catalog**: add your mentors' rules with their name.
- **Stocks by sector**: upload the Excel in Account → Data and lists.
- **Performance report**: upload the file exported from Thinkorswim.
- **Real data**: link Schwab in Account → Schwab connection (the permission lasts 7 days).
- **Optionsbb ETFs**: the administrator can change their stocks and quantities from My ETF → *Edit (administrator)*.
- **Earnings and dividends**: set the `FINNHUB_API_KEY` and `ALPHAVANTAGE_API_KEY` variables (free plans) for report dates and dividend history.
- **Bank rates and indicative premiums** on the welcome screens: edited with the administrator service `/api/admin/guide`.

## 13. Glossary
| Term | Meaning |
|---|---|
| Strike | Price at which the option can be exercised |
| Premium | Money you collect when selling the option |
| Assigned | They buy your shares at the strike |
| Breakeven | Price below which you start losing in a covered call |
| Bid / Ask | Price at which they buy / sell in the market |
| Delta | Approximation of the probability that the option ends in the money |
| Open interest (OI) | Open contracts |
| RSI | Strength indicator: above 70 overbought, below 30 oversold |
| SMA | Simple moving average |
| Profit factor | Total gains divided by total losses |

## 14. Common problems
- **"Windows can't find … cmd"**: don't type `cmd` with a file selected. Click an empty space, press Ctrl + L, type `cmd` and Enter.
- **Windows blocks `iniciar.bat`**: open a console in the folder and run `python server.py`.
- **Simulated data**: while Schwab is not linked, the app shows demo data and says so in the yellow bar.
- **I don't see a module**: it has a lock because it belongs to a higher plan.
- **A stock doesn't load**: check the symbol. With real data, only symbols that exist at Schwab work.

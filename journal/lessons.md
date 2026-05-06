# Trading Lessons

Curated, append-only durable lessons from past trades. The EOD routine writes here only when a day produced a NON-OBVIOUS lesson (surprise, broken thesis, pattern). Morning + trading routines read this file before deciding.

Quality over quantity — terse, actionable, dated. Better to skip a day than write fluff.

Format:
- YYYY-MM-DD: <lesson>

---

- 2026-05-04: Trading routine bought 2 of 4 tickers that were NOT in morning's TOP 5 (TSM, LWLG instead of FN, COHR, CRDO). Haiku's trading agent re-scanned rather than honoring morning's research. Action: tighten trading prompt to forbid re-picking, or move trading to Sonnet.
- 2026-05-04: Limit-price strategy of 0.2% above ask consistently overshot — actual fills came in 0.4-4% below limit (LITE saved $39/share). Aggressive limits are fine; we leave money on the table being too conservative.
- 2026-05-05: SELLs need a limit price just like BUYs. Closed LWLG at -7.47% as a "stop-loss" but submitted with no limit, which silently became a market order — direct CLAUDE.md violation. The "no market orders" rule applies to both sides. Also: -7.47% is not yet the 8% mandatory-close threshold; discretionary closes are allowed but must still follow the limit-order rule. trade.py now refuses orders without limit_price.
- 2026-05-05: 0.2%-above-ask buy limits expired unfilled on 2/4 high-conviction picks (COHR, AVGO) when momentum ran up >1% intraday — opposite failure mode from 5/4's "fills overshoot below limit." Lesson: the 0.2% rule is symmetric and cuts both ways. When an unfilled buy expires because price ran AWAY (not toward), the thesis isn't broken — re-evaluate at the new level rather than dropping the pick. Don't widen the rule preemptively; track whether this becomes a pattern over the next ~5 trading days first.

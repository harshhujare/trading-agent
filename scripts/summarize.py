"""Regenerate journal/SUMMARY.md from recent daily journal entries.

Run this at end of day after writing the new YYYY-MM-DD.md entry.
The agent reads SUMMARY.md at start of day instead of every full journal.
"""

import re
from datetime import datetime
from pathlib import Path

JOURNAL_DIR = Path(__file__).resolve().parent.parent / "journal"
SUMMARY_PATH = JOURNAL_DIR / "SUMMARY.md"
LOOKBACK_DAYS = 7
REFLECTION_DAYS = 3


def list_entries():
    """Return YYYY-MM-DD.md journal paths, oldest → newest."""
    entries = []
    for p in JOURNAL_DIR.glob("*.md"):
        if p.name == "SUMMARY.md" or p.name.startswith("_"):
            continue
        try:
            datetime.strptime(p.stem, "%Y-%m-%d")
        except ValueError:
            continue
        entries.append(p)
    return sorted(entries)


def extract_section(text, heading):
    """Return content under '## heading' up to next '## ' or EOF."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def summarize():
    entries = list_entries()
    if not entries:
        SUMMARY_PATH.write_text("# Journal Summary\n\n_No entries yet._\n")
        print(f"wrote {SUMMARY_PATH} (empty)")
        return

    recent = entries[-LOOKBACK_DAYS:]
    latest = entries[-1]
    latest_text = latest.read_text()

    portfolio = extract_section(latest_text, "Portfolio Status") or "_not recorded_"

    trade_blocks = []
    for p in recent:
        trades = extract_section(p.read_text(), "Trades Executed")
        if trades and trades.lower() != "none today.":
            trade_blocks.append(f"### {p.stem}\n{trades}")

    reflection_blocks = []
    for p in recent[-REFLECTION_DAYS:]:
        ref = extract_section(p.read_text(), "End-of-Day Reflection")
        if ref:
            reflection_blocks.append(f"### {p.stem}\n{ref}")

    out = [
        "# Journal Summary",
        "",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} from "
        f"{len(recent)} of {len(entries)} entries "
        f"({recent[0].stem} → {recent[-1].stem})_",
        "",
        f"## Latest Portfolio Status _(from {latest.stem})_",
        "",
        portfolio,
        "",
        f"## Recent Trades (last {LOOKBACK_DAYS} days)",
        "",
        "\n\n".join(trade_blocks) if trade_blocks else "_no trades in window_",
        "",
        f"## Recent Reflections (last {REFLECTION_DAYS} days)",
        "",
        "\n\n".join(reflection_blocks) if reflection_blocks else "_no reflections recorded_",
        "",
    ]
    SUMMARY_PATH.write_text("\n".join(out))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    summarize()

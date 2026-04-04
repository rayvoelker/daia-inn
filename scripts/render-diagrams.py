#!/usr/bin/env python3
"""Render Mermaid diagrams to PNG for mobile/offline viewing.

Usage: uv run python scripts/render-diagrams.py
Requires: pip install mermaid-py
"""

from pathlib import Path

import mermaid
from mermaid.graph import Graph

DIAGRAMS_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

DIAGRAMS = {
    "kitchen": """flowchart LR
    subgraph Kitchen
        direction TB
        BAKER["Baker\\n(Haiku, $0.001)\\nScaffolds files"]
        KITCHENBOY["Kitchen Boy\\n(Haiku, $0.001)\\nBoilerplate"]
        LINECOOK["Line Cook\\n(local 26B, free)\\n50 tok/s"]
        HEADCHEF["Head Chef\\n(Sonnet, $$)\\nComplex work"]
        OWNER["Owner Cooks\\n(Opus, $$$)\\nLast resort"]
    end
    BAKER --> LINECOOK
    KITCHENBOY --> LINECOOK
    LINECOOK -->|stuck 3x| HEADCHEF
    HEADCHEF -->|stuck| OWNER""",

    "dining-room": """flowchart LR
    COOK["Cook\\n(done)"] --> MAID["Chambermaid\\n(Haiku)\\nlint, format"]
    MAID --> WAITER["Waitstaff\\n(Sonnet)\\ninspects"]
    WAITER -->|approved| CUSTOMER["Customer\\n(Tests)"]
    CUSTOMER -->|satisfied| SCRIBE["Scribe\\n(Haiku)\\ncommit msg"]
    CUSTOMER -->|sends back| COOK""",

    "star-topology": """flowchart TB
    INNKEEPER["INNKEEPER\\n(Opus)\\nSees everything\\nDecides everything"]
    SCOUT["Scout"] --> INNKEEPER
    INNKEEPER --> BAKER["Baker"]
    INNKEEPER --> COOK["Cook"]
    INNKEEPER --> MAID["Chambermaid"]
    INNKEEPER --> REVIEWER["Reviewer"]
    INNKEEPER --> SCRIBE["Scribe"]
    INNKEEPER --> CUSTOMER["Tests"]
    LEDGER[("Ledger")] <-.-> INNKEEPER
    CUSTOMER -->|sends back| INNKEEPER
    REVIEWER -->|flags| INNKEEPER""",

    "full-flow": """flowchart TB
    ORDER["New Order"] --> INNKEEPER["INNKEEPER\\n(Opus)"]
    INNKEEPER <-.-> LEDGER[("LEDGER")]
    INNKEEPER -->|classify| SCOUT["Scout\\n(e4b, free)"]
    SCOUT --> BAKER["Baker\\n(Haiku)"]
    SCOUT -->|trivial| KB["Kitchen Boy\\n(Haiku)"]
    BAKER --> LC["Line Cook\\n(gemma4:26b, free)"]
    LC -->|stuck| HC["Head Chef\\n(Sonnet)"]
    HC -->|stuck| OC["Owner Cooks\\n(Opus)"]
    KB --> MAID["Chambermaid\\n(Haiku)"]
    LC -->|done| MAID
    HC -->|done| MAID
    OC -->|done| MAID
    MAID --> REV["Waitstaff\\n(Sonnet)"]
    REV --> CUST["Customer\\n(Tests)"]
    CUST -->|sends back| INNKEEPER
    CUST -->|satisfied| SCRIBE["Scribe\\n(Haiku)"]
    SCRIBE --> SHIP["SHIPPED"]
    SHIP --> LEDGER""",
}


def main():
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    for name, mmd in DIAGRAMS.items():
        out = DIAGRAMS_DIR / f"{name}.png"
        g = Graph(name, mmd)
        r = mermaid.Mermaid(g)
        r.to_png(str(out))
        print(f"  {out.relative_to(DIAGRAMS_DIR.parent.parent)}")
    print(f"\nRendered {len(DIAGRAMS)} diagrams.")


if __name__ == "__main__":
    main()

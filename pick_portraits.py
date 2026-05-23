"""One-time script to set final portrait picks. Run from Studio root, then delete."""
import shutil
from pathlib import Path

BASE = Path("data/anchors/portraits")

PICKS = [
    ("aisha_thompson",  3),
    ("carlos_mendez",   5),
    ("dana_reyes",      6),
    ("james_callahan",  2),
    ("kevin_park",      2),
    ("layla_hassan",    7),
    ("marcus_webb",     3),
    ("mei_lin_zhou",    8),
    ("priya_nair",      5),
    ("rachel_torres",   1),
    ("sofia_okafor",    5),
    ("tyler_brooks",    3),
]

for anchor_id, n in PICKS:
    src = BASE / f"{anchor_id}_candidate_{n}.png"
    dst = BASE / f"{anchor_id}.png"
    if not src.exists():
        print(f"MISSING: {src}")
        continue
    shutil.copy2(src, dst)
    print(f"  {anchor_id}.png  ← candidate {n}")

print("\nDone. Run: python scripts/anchors/generate_portraits.py --status")

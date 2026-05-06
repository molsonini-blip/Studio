import sys
sys.path.insert(0, "/opt/studio")
from core.training.scraper import collect_dataset
from pathlib import Path

clips = collect_dataset(
    output_dir=Path("/opt/studio/data/test_clips"),
    query="news anchor broadcast",
    max_clips=3,
    max_duration_sec=7200,
)
print(f"\nDownloaded {len(clips)} clips")
for c in clips:
    print(f"  {c.item_id}  {c.duration_sec:.0f}s  caps={c.has_captions}  audio={c.audio_path is not None}")

import sys
sys.path.insert(0, "/opt/studio")
from core.training.scraper import search_archive

results = search_archive(query="news anchor broadcast", max_results=10, min_duration_sec=0)
print(f"Results: {len(results)}")
for r in results:
    col = r['collection']
    if isinstance(col, list):
        col = col[0] if col else ''
    print(f"  {r['id']}  dur={r['duration']}  col={col}")

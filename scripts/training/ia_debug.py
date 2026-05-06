import internetarchive as ia

# Test 1: broad query no filter
r1 = list(ia.search_items(
    "news anchor broadcast",
    fields=["identifier", "title", "collection", "duration"],
    params={"rows": 3}
))
print(f"Broad query: {len(r1)} results")
for x in r1:
    print("  ", x.get("identifier"), "dur:", x.get("duration"))

# Test 2: tvnews via fq param
r2 = list(ia.search_items(
    "news anchor",
    fields=["identifier", "title", "collection", "duration"],
    params={"rows": 3, "fq": "collection:tvnews"}
))
print(f"tvnews fq: {len(r2)} results")
for x in r2:
    print("  ", x.get("identifier"), "dur:", x.get("duration"))

# Test 3: collection in query string
r3 = list(ia.search_items(
    "news AND collection:tvnews",
    fields=["identifier", "title", "duration"],
    params={"rows": 3}
))
print(f"collection in query: {len(r3)} results")
for x in r3:
    print("  ", x.get("identifier"), "dur:", x.get("duration"))

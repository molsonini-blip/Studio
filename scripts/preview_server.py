"""
Preview server for Studio broadcast outputs.
Lists produced MP4s and plays them in the browser.

Run:  .venv/bin/python scripts/preview_server.py
Open: http://<server-ip>:5050
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string, send_file

STUDIO_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = STUDIO_DIR / "outputs"

app = Flask(__name__)

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Studio Preview</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0d0d0d; color: #ddd;
         display: flex; height: 100vh; overflow: hidden; }

  /* ── Sidebar ── */
  #sidebar { width: 300px; flex-shrink: 0; display: flex; flex-direction: column;
             border-right: 1px solid #222; overflow: hidden; }
  #sidebar-header { padding: 16px; border-bottom: 1px solid #222; }
  #sidebar-header h1 { font-size: 16px; color: #fff; font-weight: 600; }
  #sidebar-header p  { font-size: 12px; color: #555; margin-top: 3px; }
  #sidebar-body { flex: 1; overflow-y: auto; padding: 12px; }

  .section { font-size: 10px; color: #444; text-transform: uppercase;
             letter-spacing: 1px; margin: 14px 0 6px; }
  .section:first-child { margin-top: 0; }

  .card { padding: 10px 12px; border-radius: 6px; cursor: pointer;
          background: #161616; border: 1px solid #222; margin-bottom: 6px; }
  .card:hover { background: #1e1e1e; border-color: #333; }
  .card.active { background: #1a2030; border-color: #3a5080; }
  .card .title { font-size: 13px; font-weight: 500; color: #eee; }
  .card .meta  { font-size: 11px; color: #555; margin-top: 3px; }

  .seg-card { padding: 7px 10px; border-radius: 4px; cursor: pointer;
              background: #121212; border: 1px solid #1e1e1e; margin-bottom: 4px;
              font-size: 12px; color: #aaa; }
  .seg-card:hover { background: #1a1a1a; color: #ccc; }
  .seg-card.active { color: #7ab; border-color: #2a4060; }

  /* ── Player ── */
  #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #player-bar { padding: 14px 20px; border-bottom: 1px solid #1a1a1a;
                display: flex; align-items: center; gap: 12px; }
  #now-playing { font-size: 14px; color: #ccc; }
  #file-size    { font-size: 12px; color: #444; margin-left: auto; }
  #player-wrap  { flex: 1; display: flex; align-items: center; justify-content: center;
                  background: #000; padding: 24px; }
  video { max-width: 100%; max-height: 100%; border-radius: 6px; }
  #placeholder { color: #333; font-size: 15px; }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Studio Preview</h1>
    <p id="count">Loading...</p>
  </div>
  <div id="sidebar-body">
    <div class="section">Broadcasts</div>
    <div id="broadcast-list"></div>
    <div class="section" id="seg-label" style="display:none">Segments</div>
    <div id="segment-list"></div>
  </div>
</div>

<div id="main">
  <div id="player-bar">
    <span id="now-playing">Select a broadcast to preview</span>
    <span id="file-size"></span>
  </div>
  <div id="player-wrap">
    <span id="placeholder">No video selected</span>
    <video id="player" controls style="display:none"></video>
  </div>
</div>

<script>
let activeCard = null;
let activeSeg  = null;

async function load() {
  const data = await fetch('/api/files').then(r => r.json());
  const list = document.getElementById('broadcast-list');
  const count = document.getElementById('count');

  count.textContent = data.broadcasts.length
    ? data.broadcasts.length + ' broadcast' + (data.broadcasts.length > 1 ? 's' : '')
    : 'No broadcasts yet';

  data.broadcasts.forEach(b => {
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML =
      '<div class="title">' + b.label + '</div>' +
      '<div class="meta">' + b.date + ' &bull; ' + b.size_kb + ' KB</div>';
    el.onclick = () => playBroadcast(el, b);
    list.appendChild(el);
  });
}

function playBroadcast(el, b) {
  if (activeCard) activeCard.classList.remove('active');
  activeCard = el;
  el.classList.add('active');
  playVideo('/video/' + b.path, b.label, b.size_kb);

  const segList  = document.getElementById('segment-list');
  const segLabel = document.getElementById('seg-label');
  segList.innerHTML = '';
  activeSeg = null;

  if (b.segments && b.segments.length) {
    segLabel.style.display = '';
    b.segments.forEach(s => {
      const sel = document.createElement('div');
      sel.className = 'seg-card';
      sel.textContent = s.name;
      sel.onclick = (ev) => {
        ev.stopPropagation();
        if (activeSeg) activeSeg.classList.remove('active');
        activeSeg = sel;
        sel.classList.add('active');
        playVideo('/video/' + s.path, s.name, s.size_kb);
      };
      segList.appendChild(sel);
    });
  } else {
    segLabel.style.display = 'none';
  }
}

function playVideo(url, title, size_kb) {
  document.getElementById('now-playing').textContent = title;
  document.getElementById('file-size').textContent   = size_kb + ' KB';
  document.getElementById('placeholder').style.display = 'none';
  const player = document.getElementById('player');
  player.style.display = '';
  player.src = url;
  player.play();
}

load();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(_HTML)


@app.route("/api/files")
def api_files():
    broadcasts = []
    for mp4 in sorted(OUTPUTS_DIR.glob("broadcast_*.mp4"), reverse=True):
        timestamp = mp4.stem.replace("broadcast_", "")   # "20260523_170459"
        episode_dir = OUTPUTS_DIR / f"episode_{timestamp}"

        # Parse display date from timestamp
        d, t = (timestamp.split("_") + [""])[:2]
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}" if len(d) == 8 else timestamp

        # Anchor segments from episode dir
        segments = []
        if episode_dir.exists():
            for seg in sorted(episode_dir.glob("*_seg.mp4")):
                anchor = seg.stem.replace("_seg", "").replace("_", " ").title()
                segments.append({
                    "name": anchor,
                    "path": str(seg.relative_to(STUDIO_DIR)),
                    "size_kb": seg.stat().st_size // 1024,
                })

        broadcasts.append({
            "label":    mp4.name,
            "path":     str(mp4.relative_to(STUDIO_DIR)),
            "size_kb":  mp4.stat().st_size // 1024,
            "date":     date_str,
            "segments": segments,
        })

    return jsonify({"broadcasts": broadcasts})


@app.route("/video/<path:filepath>")
def serve_video(filepath):
    full = STUDIO_DIR / filepath
    if not full.exists() or full.suffix != ".mp4":
        return "Not found", 404
    return send_file(full, mimetype="video/mp4", conditional=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"[preview] http://0.0.0.0:{port}")
    print(f"[preview] outputs: {OUTPUTS_DIR}")
    app.run(host="0.0.0.0", port=port)

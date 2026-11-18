"""tools/inventory.py   every file in the experiment folder with its size and time, grouped by folder (frames counted, not listed). Feeds EVERYTHING.md."""
import os, time, collections
F = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
groups = collections.OrderedDict()
for root, dirs, files in os.walk(F):
    dirs[:] = sorted(d for d in dirs if d not in ('_tmp',) and not d.startswith('._'))
    rel = os.path.relpath(root, F); fs = sorted(f for f in files if not f.startswith('._') and f != '.DS_Store')
    if not fs: continue
    if os.path.basename(root).startswith('frames'):
        tot = sum(os.path.getsize(os.path.join(root, f)) for f in fs); groups[rel] = ['(%d PNG frames, %.0f MB)' % (len(fs), tot / 1e6)]; continue
    groups[rel] = ['%s  %s  %s' % (f, ('%.1f MB' % (os.path.getsize(os.path.join(root, f)) / 1e6)) if os.path.getsize(os.path.join(root, f)) > 1e6 else ('%d KB' % max(1, os.path.getsize(os.path.join(root, f)) // 1024)), time.strftime('%H:%M', time.localtime(os.path.getmtime(os.path.join(root, f))))) for f in fs]
for g, rows in groups.items():
    print('\n### %s\n' % ('top level' if g == '.' else g)); [print('- ' + r) for r in rows]

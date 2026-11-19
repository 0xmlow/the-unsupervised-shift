"""
tools/pano_render.py   (Nov 18) Cycles 360 photographs of the block for the walk's no-WebGL version.

  Blender -b --factory-startup --python tools/pano_render.py -- OUTDIR [--res 7168x3584] [--samples 32] [--only 0317_s01,...]

MLow, 13:37: the photographed walk "looks fuzzy af. make it look more realistic". The first photographs came from the
real-time walk at 2048 wide. These are rendered by Cycles with the finals' look (AgX Medium High Contrast, the bloom,
exposure by the sun), equirectangular, from the same 28 points and five moments as tools/panos.mjs, so walk/pano.js
reads them unchanged. The centre of each image looks north (+y), east is to the right.
"""
import sys, os, time, runpy, math
import bpy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = os.path.abspath(argv[0]); os.makedirs(OUT, exist_ok=True)
def opt(k, d): return argv[argv.index(k) + 1] if k in argv else d
RES = opt('--res', '7168x3584'); SAMPLES = int(opt('--samples', '16')); ONLY = set(opt('--only', '').split(',')) - {''}
MOMENTS = [('0030', '00:30'), ('0240', '02:40'), ('0317', '03:17:20'), ('0520', '05:20'), ('0713', '07:13')]
NODES = []
for side, y in (('s', -6.4), ('n', 6.4)):
    for i, x in enumerate(range(-4, 101, 8)): NODES.append(('%s%02d' % (side, i), x, y))
sys.argv = [os.path.join(HERE, 'build_block.py'), '--', '--norender', '--samples', str(SAMPLES), '--res', RES]
g = runpy.run_path(os.path.join(HERE, 'build_block.py'), run_name='bb')
K = g['K']; scene = bpy.context.scene; T0 = time.time()
cd = bpy.data.cameras.new('pano'); cd.type = 'PANO'
try: cd.panorama_type = 'EQUIRECTANGULAR'
except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
cd.clip_start = 0.05; cd.clip_end = 2000
cam = bpy.data.objects.new('pano', cd); scene.collection.objects.link(cam); scene.camera = cam
cam.rotation_euler = (math.pi / 2, 0, 0)          # level, looking north (+y): the centre of the image
rx, ry = (int(v) for v in RES.split('x')); r = scene.render; r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
scene.cycles.samples = SAMPLES; r.use_persistent_data = True; scene.cycles.denoising_use_gpu = True; r.use_compositing = '--bloom' in argv; r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 88
n = 0
for key, ts in MOMENTS:
    todo = [nd for nd in NODES if (not ONLY or '%s_%s' % (key, nd[0]) in ONLY) and not os.path.exists(os.path.join(OUT, '%s_%s.jpg' % (key, nd[0])))]
    if not todo: continue
    t = K.T(ts); g['apply_time'](t); scene.view_settings.exposure = g['exposure_for'](t)
    for nid, x, y in todo:
        cam.location = (x, y, 1.62 + 0.16)
        r.filepath = os.path.join(OUT, '%s_%s.jpg' % (key, nid)); t1 = time.time(); bpy.ops.render.render(write_still=True); n += 1
        print('PANO %s_%s %.0fs (total %.0fs)' % (key, nid, time.time() - t1, time.time() - T0), flush=True)
print('PANO done', n)

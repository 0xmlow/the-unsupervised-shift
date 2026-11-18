"""
tools/web_encode.py   (Nov 18, for the walkable block)  baked EXRs -> the JPEGs the walk loads.

  Blender -b --factory-startup --python tools/web_encode.py -- BAKE_DIR SITE_ASSETS_DIR

For every lm_<state>_<atlas>.exr in BAKE_DIR: denoise it (OIDN, in the compositor), then encode all the atlases of a
state with ONE scale, so two atlases meeting at a seam agree: value = srgb(E / S), S = the 99.7th percentile of the
covered texels of the near atlases. Writes lm/<state>_<atlas>.png (full size) and the scales into scene.json beside
them; the JPEG and the 2048 copies for phones are made afterwards with PIL (tools/web_build.sh).
"""
import bpy, sys, os, glob, json, re, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]; SRC, DST = a[0], a[1]
os.makedirs(os.path.join(DST, 'png'), exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.view_settings.view_transform = 'Standard'; sc.render.resolution_percentage = 100
ng = bpy.data.node_groups.new('dn', 'CompositorNodeTree'); ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
sc.compositing_node_group = ng; out = ng.nodes.new('NodeGroupOutput'); src = ng.nodes.new('CompositorNodeImage'); dn = ng.nodes.new('CompositorNodeDenoise')
for k, v in (('prefilter', 'ACCURATE'), ('use_hdr', True), ('quality', 'HIGH')):
    try: setattr(dn, k, v)
    except Exception: pass
ng.links.new(src.outputs[0], dn.inputs[0]); ng.links.new(dn.outputs[0], out.inputs[0]); sc.render.use_compositing = True
def denoise(path):
    img = bpy.data.images.load(path); w, h = img.size; sc.render.resolution_x, sc.render.resolution_y = w, h
    src.image = img; o = path.replace('.exr', '.dn.exr'); sc.render.filepath = o; bpy.ops.render.render(write_still=True)
    bpy.data.images.remove(img); r = bpy.data.images.load(o); px = np.empty(w * h * 4, np.float32); r.pixels.foreach_get(px); bpy.data.images.remove(r); os.remove(o)
    return px.reshape(h, w, 4)[..., :3], w, h
files = sorted(glob.glob(os.path.join(SRC, 'lm_*_*.exr')))
by = {}
for f in files:
    st, at = re.match(r'lm_([a-z]+)_(.+)\.exr', os.path.basename(f)).groups(); by.setdefault(st, []).append((at, f))
scales = {}
for st, items in by.items():
    data = {at: denoise(f) for at, f in items}
    near = np.concatenate([d[0][d[0].max(-1) > 1e-5].max(-1) for at, d in data.items() if at.startswith('n')])
    S = float(np.percentile(near, 99.7)); scales[st] = S; print('SCALE', st, S, flush=True)
    for at, (rgb, w, h) in data.items():
        x = np.clip(rgb / S, 0, 1); e = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
        o = bpy.data.images.new('o', w, h); o.colorspace_settings.name = 'Non-Color'
        o.pixels.foreach_set(np.dstack([e, np.ones((h, w))]).astype(np.float32).ravel())
        o.filepath_raw = os.path.join(DST, 'png', '%s_%s.png' % (st, at)); o.file_format = 'PNG'; o.save(); bpy.data.images.remove(o)
        print('ENCODED', st, at, w, flush=True)
json.dump(scales, open(os.path.join(DST, 'scales.json'), 'w'))

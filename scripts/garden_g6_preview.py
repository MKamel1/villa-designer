"""Neutral Blender diagnostics of actual G6 assemblies, never presentation renders.

Run Blender with ``-b --python-exit-code 1 -P scripts/garden_g6_preview.py --
--input out/garden-g6/specimens.json``. The input contains materials and
assemblies (each an identifier and actual mesh list). A metre-native 1.8 m
scale reference accompanies each isolated specimen. Geometry is translated
as one rigid assembly for isolation; its shape and materials are preserved.
``--scene`` instead previews selected authored cameras in architectural context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def render(args):
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(ROOT / "src"))
    from archpipe.blender import villa_scene as builder

    data = json.loads(args.input.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = []
    reference = {row['id']: row for row in json.loads(args.reference_receipt.read_text())} if args.reference_receipt else {}

    def setup(meshes, materials):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        warnings = []
        names = {m["material"] for m in meshes} | {n for m in meshes for n in m.get("face_materials", [])}
        built_materials = {name: builder.add_material(name, materials[name], str(args.library), warnings)
                           for name in names}
        objects = builder.build_meshes(meshes, built_materials, materials, warnings)
        builder.build_climbers(meshes, objects, built_materials, warnings)
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.samples = args.samples
        scene.cycles.max_bounces = 8
        scene.render.threads_mode = "FIXED"
        scene.render.threads = 8
        preferences = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                preferences.compute_device_type = backend
                preferences.get_devices()
                devices = preferences.get_devices_for_type(backend)
                if any(d.type != "CPU" for d in devices):
                    for device in devices:
                        device.use = device.type != "CPU"
                    scene.cycles.device = "GPU"
                    break
            except Exception:
                pass
        scene.render.resolution_x = 960
        scene.render.resolution_y = 720 if not args.scene else 640
        scene.render.resolution_percentage = 100
        scene.world.use_nodes = True
        background = scene.world.node_tree.nodes["Background"]
        background.inputs[0].default_value = (.8, .8, .8, 1)
        background.inputs[1].default_value = .8
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.exposure = 0
        scene.render.image_settings.file_format = "PNG"
        return scene, objects, warnings

    if args.scene:
        scene, objects, warnings = setup(data["meshes"], data["materials"])
        imported = builder.import_props(data.get("props", []), str(args.library))
        # Candidate camera preview keeps the exported geometry untouched.
        authored_views = [json.loads(args.candidate_view.read_text())] if args.candidate_view else data["views"]
        for view in authored_views:
            if view["id"] not in args.views:
                continue
            # Keep the authored physical sensor aspect, including portrait.
            # Forcing 960x640 silently crops a correctly framed portrait view.
            width,height=view['resolution']
            scale=960/max(width,height)
            scene.render.resolution_x=round(width*scale)
            scene.render.resolution_y=round(height*scale)
            camera, _ = builder.configure_camera(view)
            scene.camera = camera
            path = args.output / (view["id"] + "-neutral.png")
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            evidence.append(dict(id=view["id"], image=str(path), neutral=True,
                                 camera=view["camera"], source_geometry_sha256=canonical_hash(data["meshes"]),
                                 resolution=[scene.render.resolution_x,scene.render.resolution_y],
                                 subjects=builder.subjects(view, data["meshes"], objects, imported), warnings=warnings))
            bpy.data.objects.remove(camera, do_unlink=True)
    else:
        for specimen in data["assemblies"]:
            if args.specimens and specimen["id"] not in args.specimens:
                continue
            meshes = json.loads(json.dumps(specimen["meshes"]))
            points = [p for m in meshes for f in m["faces"] for p in f]
            low = [min(p[k] for p in points) for k in range(3)]
            high = [max(p[k] for p in points) for k in range(3)]
            origin = [(low[0]+high[0])/2, (low[1]+high[1])/2, low[2]]
            prior = reference.get(specimen['id'])
            if prior:
                origin = prior['staging']['origin']
            for mesh in meshes:
                mesh["faces"] = [[[p[k]-origin[k] for k in range(3)] for p in f] for f in mesh["faces"]]
            scene, objects, warnings = setup(meshes, data["materials"])
            span = [high[k]-low[k] for k in range(3)]
            if prior:
                span = prior['staging']['span']
            bpy.ops.mesh.primitive_plane_add(size=max(20, max(span)*4))
            floor = bpy.data.materials.new("neutral diagnostic floor")
            floor.diffuse_color = (.45, .45, .45, 1)
            bpy.context.object.data.materials.append(floor)
            # Scale aid: top of head is exactly 1.8 metres above its feet.
            fx, fy = -span[0]/2-.45, -span[1]/2
            scale_objects = []
            for location, scale in (((fx,fy,1.02),(.12,.075,.39)),
                                    ((fx-.08,fy,.31),(.042,.045,.31)),
                                    ((fx+.08,fy,.31),(.042,.045,.31)),
                                    ((fx,fy,1.68),(.12,.12,.12))):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=location)
                bpy.context.object.scale = scale
                scale_objects.append(bpy.context.object)
            light = bpy.data.lights.new("neutral softbox", "AREA")
            light.energy, light.size = 500, max(3, max(span))
            lamp = bpy.data.objects.new("neutral softbox", light)
            bpy.context.collection.objects.link(lamp)
            lamp.location = (1, -3, max(3, span[2]+1))
            lamp.rotation_euler = (Vector((0,0,span[2]/2))-lamp.location).to_track_quat("-Z", "Y").to_euler()
            camera_data = bpy.data.cameras.new("neutral specimen camera")
            camera_data.type = "ORTHO"
            camera_data.ortho_scale = max(span[0]+1.2, span[1]+1.2, (span[2]+.5)*4/3)*1.15
            camera = bpy.data.objects.new("neutral specimen camera", camera_data)
            bpy.context.collection.objects.link(camera)
            direction = specimen.get("camera_direction", [1.8, -3, 1.7])
            target = Vector((-.2, 0, max(.9, span[2]/2)))
            camera.location = target + Vector(direction)*max(1, max(span))
            camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.camera = camera
            # Fit every actual mesh and the whole reference, including plan
            # depth projected into the inclined diagnostic image. Width and
            # height alone clipped the bowl and nearest pergola post.
            bpy.context.view_layer.update()
            right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
            up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
            framed_objects = set(objects.values()) | set(scale_objects)
            world_points = [obj.matrix_world @ Vector(corner) for obj in framed_objects for corner in obj.bound_box]
            projected = [(p.dot(right), p.dot(up)) for p in world_points]
            xmin, xmax = min(p[0] for p in projected), max(p[0] for p in projected)
            ymin, ymax = min(p[1] for p in projected), max(p[1] for p in projected)
            camera.location += right*((xmin+xmax)/2-camera.location.dot(right))
            camera.location += up*((ymin+ymax)/2-camera.location.dot(up))
            aspect = scene.render.resolution_x / scene.render.resolution_y
            camera_data.ortho_scale = max(xmax-xmin, (ymax-ymin)*aspect)/.88
            if prior:
                camera.location = prior['staging']['camera_location']
                camera.rotation_euler = prior['staging']['camera_rotation']
                camera_data.ortho_scale = prior['staging']['ortho_scale']
            path = args.output / (specimen["id"]+".png")
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            evidence.append(dict(id=specimen["id"], image=str(path), neutral=True, scale_reference_height_m=1.8,
                                 actual_bounds_m=[low, high], isolation_translation_m=[-v for v in origin],
                                 staging=dict(origin=origin, span=span, camera_location=list(camera.location),
                                              camera_rotation=list(camera.rotation_euler), ortho_scale=camera_data.ortho_scale),
                                 source_geometry_sha256=canonical_hash(specimen["meshes"]), warnings=warnings))
    receipt = args.output / ("context-preview-evidence.json" if args.scene else "isolated-preview-evidence.json")
    previous = json.loads(receipt.read_text()) if receipt.exists() else []
    by_identifier = {row["id"]: row for row in previous}
    by_identifier.update({row["id"]: row for row in evidence})
    receipt.write_text(json.dumps(list(by_identifier.values()), indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "out/garden-g6")
    parser.add_argument("--library", type=Path, default=Path("/home/omar/archpipe/assets/library"))
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--scene", action="store_true")
    parser.add_argument("--candidate-view", type=Path)
    parser.add_argument("--reference-receipt", type=Path, help="Reuse before-preview camera, scale aid and neutral staging exactly")
    parser.add_argument("--views", nargs="+", default=[])
    parser.add_argument("--specimens", nargs="+", default=[])
    parser.add_argument("--graphics-lock", type=Path,
                        default=Path('/home/omar/archpipe/locks/graphics.lock'))
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:]
    args=parser.parse_args(argv)
    # Acquire the configured workstation graphics lock by descriptor;
    # opening it read-only preserves shared lock-file bytes and metadata.
    import fcntl
    with args.graphics_lock.open('rb') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        render(args)


if __name__ == "__main__":
    main()

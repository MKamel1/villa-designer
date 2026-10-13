"""Start each diagnostic import with no inherited, hidden scene objects."""


def clear_objects(bpy):
    """Remove datablock objects directly; selection cannot reach hidden objects."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def scene_meshes(bpy):
    """Exclude importer bone-display helpers outside the active scene.

    glTF armatures create custom-shape spheres in a hidden helper collection.
    Exclude the actual bone references, never meshes matched by name or size.
    These are editor aids, not source geometry or omitted extras.
    """
    helpers = {bone.custom_shape for obj in bpy.data.objects
               if obj.type == 'ARMATURE' for bone in obj.pose.bones
               if bone.custom_shape is not None}
    return [obj for obj in bpy.context.scene.objects
            if obj.type == 'MESH' and obj not in helpers]

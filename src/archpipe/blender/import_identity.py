"""Namespace the whole imported glTF hierarchy, preserving source-part names."""
def namespace_objects(objects, instance_id):
    """Empty nodes and meshes share Blender's global object-name namespace."""
    for obj in objects:
        obj.name='model-%s-%s' % (instance_id,obj.name)

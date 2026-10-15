# Frozen actual pre-polish-budget-correction selection function.
def with_models(scene, models):
    """Author a new selection atomically, retaining strict incoming admission.

    A source scene's pairs certify its old model list. Validate those pairs
    before selecting; construct the new pairs from the new authored list.
    Select on authored scenes, before physical expansion. Expanded meshes
    would retain orphan colliders when a model is removed.
    """
    bound = any(k in scene for k in
            ('imported_appearances', 'physical_model_meshes', 'imported_admission_policy'))
    if needs_scene_admission(scene) and bound:
        require_scene(scene)
    selected = list(models)
    if not bound or not isinstance(scene.get('physical_model_meshes'), list):
        return bind_scene(dict(scene, models=selected))
    # Reuse only models that are the exact incoming objects just validated.
    # New objects (even with matching IDs) require complete source construction.
    # Copy pairs so a new selection cannot mutate the admitted source scene.
    appearances, parts = [], []
    old = {m['id']:m for m in scene.get('models', [])}
    by_model = {}
    by_part = {a['standin_id']:a for a in scene['imported_appearances']}
    for part in scene['physical_model_meshes']:
        by_model.setdefault(part['model_instance'], []).append(part)
    for model in selected:
        if model.get('status') == 'procedural-bed-fallback':
            continue
        if model is old.get(model['id']):
            physical = deepcopy(by_model.get(model['id'], []))
            appearance = [deepcopy(by_part[p['id']]) for p in physical]
        else:
            appearance, physical = build_pairs([model])
        appearances.extend(appearance)
        parts.extend(physical)
    return dict(scene, models=selected, imported_appearances=appearances,
                physical_model_meshes=parts, imported_admission_policy=POLICY_SOURCE)

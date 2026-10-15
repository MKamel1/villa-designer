"""Preserve the pinned Nishita model across Blender's sky API rename."""
def configure_legacy_sky(sky):
    """Select the old single-scattering model and its explicit optical defaults.

    Blender 5 renamed Nishita and changed the new-node altitude from zero
    to 100 metres. An API adapter must preserve the original light source.
    """
    supported={item.identifier for item in sky.bl_rna.properties['sky_type'].enum_items}
    if 'NISHITA' in supported:
        sky.sky_type='NISHITA'
    elif 'SINGLE_SCATTERING' in supported:
        sky.sky_type='SINGLE_SCATTERING'
    else:
        raise ValueError('Legacy Nishita single-scattering sky is unavailable')
    sky.altitude=0.0
    sky.air_density=1.0
    sky.ozone_density=1.0
    if hasattr(sky,'dust_density'):
        sky.dust_density=1.0
    elif hasattr(sky,'aerosol_density'):
        sky.aerosol_density=1.0
    else:
        raise ValueError('Legacy sky aerosol density is unavailable')

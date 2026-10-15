"""The real 5.2 RNA enum and default changes must preserve 4.5 optics."""
from types import SimpleNamespace as N
import unittest
from archpipe.blender.sky_compat import configure_legacy_sky
class SkyCompatibility(unittest.TestCase):
    def test_standalone_calibration_bootstraps_without_pythonpath_in_other_checkout(self):
        import os
        from pathlib import Path
        import shutil
        import subprocess
        import sys
        import tempfile
        source=Path(__file__).resolve().parents[1]/'src/archpipe/blender'
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'other-checkout/src/archpipe/blender';target.mkdir(parents=True)
            for name in ('calibrate_sky.py','sky_compat.py'):shutil.copyfile(source/name,target/name)
            # Exercise the actual module imports in a Blender-like isolated
            # interpreter; remove only its rendering entry call, not imports.
            program='''import ast,sys,types
from pathlib import Path
path=Path(sys.argv[1])
sys.modules['bpy']=types.ModuleType('bpy')
tree=ast.parse(path.read_text())
tree.body=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='main')]
scope={'__file__':str(path),'__name__':'calibration_import_probe'}
exec(compile(tree,str(path),'exec'),scope)
assert Path(sys.modules['archpipe.blender.sky_compat'].__file__).parent==path.parent
'''
            env=dict(os.environ);env.pop('PYTHONPATH',None)
            path=target/'calibrate_sky.py'
            clean=subprocess.run([sys.executable,'-I','-c',program,str(path)],env=env,capture_output=True,text=True)
            self.assertEqual(clean.returncode,0,clean.stderr)
            path.write_text(path.read_text().replace('sys.path.insert(0, str(Path(__file__).resolve().parents[2]))',''))
            broken=subprocess.run([sys.executable,'-I','-c',program,str(path)],env=env,capture_output=True,text=True)
            self.assertNotEqual(broken.returncode,0)
            self.assertIn("No module named 'archpipe'",broken.stderr)

    def node(self,identifiers,new):
        p=N(enum_items=[N(identifier=i) for i in identifiers])
        node=N(bl_rna=N(properties={'sky_type':p}),sky_type='MULTIPLE_SCATTERING' if new else 'NISHITA',altitude=100. if new else 0.,air_density=1.,ozone_density=1.)
        setattr(node,'aerosol_density' if new else 'dust_density',1.)
        return node
    def test_frozen_real_52_api_selects_legacy_and_removes_altitude_drift(self):
        node=self.node(['SINGLE_SCATTERING','MULTIPLE_SCATTERING','PREETHAM','HOSEK_WILKIE'],True)
        configure_legacy_sky(node)
        self.assertEqual(node.sky_type,'SINGLE_SCATTERING');self.assertEqual(node.altitude,0.)
        self.assertEqual(node.aerosol_density,1.)
    def test_45_defaults_stay_unchanged_and_other_atmospheres_fail_closed(self):
        node=self.node(['PREETHAM','HOSEK_WILKIE','NISHITA'],False)
        before=(node.sky_type,node.altitude,node.air_density,node.ozone_density,node.dust_density)
        configure_legacy_sky(node)
        self.assertEqual(before,(node.sky_type,node.altitude,node.air_density,node.ozone_density,node.dust_density))
        with self.assertRaisesRegex(ValueError,'unavailable'):configure_legacy_sky(self.node(['PREETHAM'],True))
    def test_mutated_node_defaults_are_set_explicitly(self):
        node=self.node(['SINGLE_SCATTERING'],True);node.air_density=2;node.ozone_density=3;node.aerosol_density=4
        configure_legacy_sky(node)
        self.assertEqual((node.air_density,node.ozone_density,node.aerosol_density),(1.,1.,1.))

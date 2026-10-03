import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/ch_blender'))
from backend import identify_backend,OFFICIAL,LEGACY
from agent_worker import blender_identity,WorkerError,_run
class LegacyBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.exe=Path(self.temp.name)/'blender.exe';self.exe.touch()
    def mark(self,tag='v4.2.3'):
        (self.exe.parent/'ch-legacy-build.json').write_text(json.dumps({'backend':LEGACY,'upstreamTag':tag}))
    def test_official_without_marker(self):self.assertEqual(identify_backend(self.exe),OFFICIAL)
    def test_legacy_preserves_423_version(self):
        self.mark()
        with patch('agent_worker.subprocess.run') as p:
            p.return_value.stdout='Blender 4.2.3\n';p.return_value.stderr=''
            identity=blender_identity(self.exe)
        self.assertEqual((identity['version'],identity['backend']),('4.2.3',LEGACY))
    def test_marker_rejects_other_upstream(self):
        self.mark('v3.6.0')
        with self.assertRaises(ValueError):identify_backend(self.exe)
    def test_rejects_prefix_version_and_empty_output(self):
        for text in ('Blender 4.2.30\n','Blender 3.6.0\n',''):
            with self.subTest(text=text),patch('agent_worker.subprocess.run') as p:
                p.return_value.stdout=text;p.return_value.stderr=''
                with self.assertRaises(WorkerError) as error:blender_identity(self.exe)
                self.assertEqual(error.exception.code,'BLENDER_VERSION_MISMATCH')
    def test_official_clears_inherited_legacy_setting(self):
        with patch.dict(os.environ,{'CH_BLENDER_BACKEND':LEGACY}),patch('agent_worker.subprocess.run') as process:
            process.return_value.returncode=0
            _run([str(self.exe),'--background'],error_code='BLENDER_FAILED')
            self.assertEqual(process.call_args.kwargs['env']['CH_BLENDER_BACKEND'],OFFICIAL)
    def test_legacy_setting_reaches_scene_process(self):
        self.mark()
        with patch('agent_worker.subprocess.run') as process:
            process.return_value.returncode=0
            _run([str(self.exe),'--background'],error_code='BLENDER_FAILED')
            self.assertEqual(process.call_args.kwargs['env']['CH_BLENDER_BACKEND'],LEGACY)
    def test_bad_marker_becomes_worker_error(self):
        self.mark('v3.6.0')
        with patch('agent_worker.subprocess.run') as process:
            process.return_value.stdout='Blender 4.2.3\n'
            with self.assertRaises(WorkerError) as error:blender_identity(self.exe)
            self.assertEqual(error.exception.code,'BLENDER_VERSION_MISMATCH')
if __name__=='__main__':unittest.main()

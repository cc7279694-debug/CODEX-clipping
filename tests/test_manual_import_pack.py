import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from codex_clipping import manual_import_pack as pack
except ImportError:
    pack = None


class ManualImportPackTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(pack, 'manual import pack is not implemented')
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.output = self.root / 'output'; self.output.mkdir()
        self.sources = {}
        metadata = []
        for sid, ext, content in [('a','.mp4',b'a'),('b','.mp4',b'b'),('bed','.wav',b'c')]:
            path=self.source/(sid+ext); path.write_bytes(content); self.sources[sid]=path
            metadata.append({'source_id':sid,'relative_path':path.name,'sha256':hashlib.sha256(content).hexdigest(), 'media_type':'audio' if sid=='bed' else 'video'})
        def clip(cid,sid,tid,start,end,role):
            return {'clip_id':cid,'source_id':sid,'track_id':tid,'role':role,'media_type':'video' if role=='main' else 'audio','review_status':'accepted','source_start':0,'source_end':end-start,'timeline_start':start,'timeline_duration':end-start,'speed':1,'volume':1,'muted':False}
        self.plan={'schema_version':1,'output':{'duration':15},'sources':metadata,'tracks':[{'track_id':'v','role':'main','media_type':'video'},{'track_id':'a','role':'music','media_type':'audio'}], 'clips':[clip('a1','a','v',0,7.5,'main'),clip('b1','b','v',7.5,15,'main'),clip('c1','bed','a',0,15,'music')]}

    def run_pack(self,name='example',plan=None):
        with patch.object(pack, 'validate_clip_plan', return_value=self.sources) as validate:
            result=pack.create_manual_import_pack(plan or self.plan,self.source,self.output/name,'ffprobe',allowed_output_root=self.output)
            self.assertTrue(validate.call_args.kwargs['require_approved'])
            return result

    def test_media_and_mapping_are_separate_and_preserved(self):
        result=self.run_pack(); mapping=json.loads((result/'timeline.json').read_text(encoding='utf-8'))
        self.assertEqual([x['source_id'] for x in mapping['video_clips']],['a','b'])
        self.assertEqual(mapping['video_clips'][1]['timeline_start'],7.5)
        self.assertEqual(mapping['audio_clips'][0]['timeline_duration'],15)
        self.assertEqual(mapping['video_clips'][0]['track_id'],'v')
        self.assertEqual(mapping['video_clips'][0]['review_status'],'accepted')
        for entry in mapping['sources']:
            self.assertEqual(hashlib.sha256((result/entry['asset_path']).read_bytes()).hexdigest(),entry['sha256'])
        self.assertFalse((result/'draft_content.json').exists())

    def test_existing_and_escape_destinations_rejected(self):
        self.run_pack()
        with self.assertRaises(FileExistsError): self.run_pack()
        with self.assertRaises(ValueError): self.run_pack('../escape')

    def test_unhandled_overlay_or_gap_is_rejected_before_writing(self):
        for change in ('broll','gap'):
            p=copy.deepcopy(self.plan)
            if change=='broll': p['tracks'][0]['role']='broll'
            else: p['clips'][1]['timeline_start']=8
            with self.subTest(change=change),self.assertRaises(ValueError): self.run_pack(change,p)
            self.assertFalse((self.output/change).exists())

    def test_nonzero_source_range_is_preserved_in_readable_instructions(self):
        p=copy.deepcopy(self.plan); p['clips'][0]['source_start']=2; p['clips'][0]['source_end']=9.5
        result=self.run_pack('source-range',p)
        timeline=json.loads((result/'timeline.json').read_text(encoding='utf-8'))
        self.assertEqual((timeline['video_clips'][0]['source_start'],timeline['video_clips'][0]['source_end']),(2,9.5))
        self.assertIn('源 2–9.5 秒', (result/'README.md').read_text(encoding='utf-8'))

    def test_changed_source_is_rejected(self):
        self.sources['a'].write_bytes(b'changed')
        with self.assertRaises(ValueError): self.run_pack()

    def test_real_review_gate_and_changed_plan_cannot_export(self):
        from codex_clipping.clipplan import review_clip
        p=copy.deepcopy(self.plan)
        p.update(revision=0, history=[])
        p['output'].update(width=1080,height=1920,fps=30)
        for source in p['sources']:
            source['duration_seconds']=15 if source['source_id']=='bed' else 7.5
        for clip in p['clips']:
            clip['review_status']='pending'; clip['evidence']=['synthetic']
        def fake_probe(path, _):
            return {'duration_seconds':15 if Path(path).suffix=='.wav' else 7.5,
                    'streams':[{'codec_type':'audio' if Path(path).suffix=='.wav' else 'video'}]}
        def create(plan,name):
            return pack.create_manual_import_pack(plan,self.source,self.output/name,'ffprobe',allowed_output_root=self.output)
        with patch('codex_clipping.clipplan.probe_media',side_effect=fake_probe):
            with self.assertRaises(ValueError): create(p,'pending')
            self.assertFalse((self.output/'pending').exists())
            for clip in p['clips']:
                p=review_clip(p,clip['clip_id'],'accept')
            tampered=copy.deepcopy(p); tampered['clips'][0]['source_start']=0.1
            with self.assertRaises(ValueError): create(tampered,'tampered')
            self.assertFalse((self.output/'tampered').exists())
            self.assertTrue((create(p,'accepted')/'timeline.json').is_file())

if __name__=='__main__': unittest.main()

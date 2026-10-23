import unittest
import tempfile
from pathlib import Path
import profiledl

class TestProfileDL(unittest.TestCase):
    def test_validation(self):
        v=profiledl.validate({'url':'https://www.instagram.com/example/','media':'photos'})
        self.assertEqual(v['platform'],'instagram')
        for url in ('http://instagram.com/example','https://127.0.0.1/x','https://instagram.com.evil.test/x', 'file:///etc/passwd'):
            with self.assertRaises(ValueError): profiledl.validate({'url':url})
    def test_build_command(self):
        with tempfile.TemporaryDirectory() as d:
            base=dict(folder=d,url='https://instagram.com/example/', platform='instagram', media='photos',
                limit_posts=20,metadata=1,after_date='2026-01-01',before_date=None)
            cmd=profiledl.build_command(base)
            self.assertIn('--post-range',cmd)
            self.assertIn('--filter',cmd)
            base.update(platform='youtube',url='https://youtube.com/@example/videos',media='videos')
            cmd=profiledl.build_command(base)
            self.assertEqual(cmd[0],'yt-dlp')
            self.assertIn('--download-archive',cmd)

if __name__=='__main__': unittest.main()

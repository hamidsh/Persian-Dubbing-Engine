import shutil
import pytest
import numpy as np
from persian_dubbing.core.config import Config
from persian_dubbing.core.pipeline import Pipeline
from persian_dubbing.core.process import run
from persian_dubbing.storage.project import Project
from persian_dubbing.media.audio import probe,read,mux,write,conform
pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg unavailable')
def test_real_video_ingest_mux(tmp_path):
    cfg=Config();source=tmp_path/'input with spaces.mp4'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x120:r=24:d=3','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source])
    p=Project(tmp_path/'project');Pipeline(p,cfg).ingest(source)
    data,sr=read(p.root/'audio/source.wav');assert sr==24000 and len(data)/sr>=2.9
    short=tmp_path/'short.wav';write(short,np.sin(np.arange(24000)*.1)*.02)
    out=tmp_path/'output.mp4';mux(source,short,out,cfg)
    info=probe(out,cfg);assert info['duration']==pytest.approx(3,abs=.1)
    assert any(s['codec_type']=='video' for s in info['streams'])
def test_rubberband(tmp_path):
    if 'rubberband' not in run(['ffmpeg','-hide_banner','-filters']):pytest.skip('No rubberband')
    source=tmp_path/'source.wav';dest=tmp_path/'dest.wav';write(source,.05*np.sin(2*np.pi*440*np.arange(48000)/24000))
    conform(source,dest,Config(),speed=1.1);data,sr=read(dest);assert len(data)/sr==pytest.approx(2/1.1,abs=.05)

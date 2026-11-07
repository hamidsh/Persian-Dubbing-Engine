from dataclasses import replace
import json,sys,time,threading
import numpy as np
import pytest
from persian_dubbing.core.config import Config
from persian_dubbing.core.types import Segment,Voice,Capabilities
from persian_dubbing.core.prosody import plan
from persian_dubbing.core.pipeline import Pipeline
from persian_dubbing.core.process import Cancellation,Cancelled,run
from persian_dubbing.storage.project import Project
from persian_dubbing.media.audio import write,read,mix_timeline
from persian_dubbing.media.subtitles import import_srt,export_srt,timestamp
from persian_dubbing.persian_frontend.frontend import normalize,number

@pytest.fixture
def project(tmp_path):
    p=Project(tmp_path/'project');ref=p.root/'references'/'native.wav'
    write(ref,.05*np.sin(2*np.pi*220*np.arange(24000)/24000))
    p.save_voice(Voice('native',str(ref)));p.assign('A','native');p.assign('B','native')
    p.save_segments([Segment('s1',.5,2.5,source='Hello',speaker='A',translation='سلام'),Segment('s2',2,4,source='Thanks',speaker='B',translation='ممنون')])
    return p
@pytest.fixture
def config():return Config(tts_engine='diagnostic')

@pytest.mark.parametrize('value,expected',[(0,'صفر'),(19,'نوزده'),(23,'بیست و سه'),(105,'صد و پنج'),(1001,'یک هزار و یک'),(-6,'منفی شش')])
def test_numbers(value,expected):assert number(value)==expected

def test_normalization():
    text,warnings=normalize('يك GPU با ۱۲۵٪ توان و 3.5 ولت',{'GPU':'جی پی یو'})
    assert 'یک جی پی یو' in text and 'صد و بیست و پنج درصد' in text and 'سه ممیز پنج' in text
    assert normalize('گل')[1]
    assert normalize('گل',{'گل':'گُل'})==('گُل',[])

def test_manual_pronunciation_wins(project,config):
    s=project.segments()[0];s.pronunciation='گُل';cfg=replace(config,dictionary={'گُل':'گِل'})
    result,_=plan(s,project.voice_for('A'),cfg,Capabilities());assert result.text=='گُل'

@pytest.mark.parametrize('a,b',[(0,0),(-1,2),(2,1),(float('nan'),2),(0,float('inf'))])
def test_bad_times(a,b):
    with pytest.raises(ValueError):Segment('s',a,b).validate()

def test_storage(project):
    s=project.segments()[0];s.translation='ویرایش';project.update_segment(s)
    assert Project(project.root).segments()[0].translation=='ویرایش'
    with pytest.raises(ValueError):project.save_segments([s,s])
    assert len(project.segments())==2

def test_srt_roundtrip(project,tmp_path):
    f=tmp_path/'x.srt';export_srt(project.segments(),f);r=import_srt(f,True)
    assert r[0].translation=='سلام' and r[0].start==.5
    assert timestamp(59.9996)=='00:01:00,000'
    f.write_text('1\n00:00:00,000 --> 00:00:02,000\n[A] سلام\n',encoding='utf-8')
    assert import_srt(f,True)[0].speaker=='A'

def test_anchor_requires_approval(project):
    v=project.voice_for('A');v.anchor=v.reference
    with pytest.raises(ValueError):v.selected_reference('anchor')
    v.anchor_approved=True;assert v.selected_reference('anchor')==v.reference

def test_resume_invalidation(project,config):
    pipe=Pipeline(project,config);assert pipe.render()==2
    first=project.artifact('s1')[0];assert pipe.render()==0
    folder=pipe.export();assert (folder/'dubbed.wav').exists()
    assert len(list(folder.glob('speaker_*.wav')))==2
    assert json.loads((folder/'report.json').read_text())['diagnostic_only']
    s=project.segments()[0];s.translation='سلام دوباره';project.update_segment(s)
    with pytest.raises(ValueError,match='stale'):pipe.export()
    assert pipe.render()==1 and project.artifact('s1')[0]!=first
    write(project.voice_for('A').reference,np.ones(24000)*.03);assert pipe.render()==2

def test_overlap_mixing(tmp_path,config):
    a=tmp_path/'a.wav';write(a,np.ones(24000)*.2);dest=tmp_path/'mix.wav'
    mix_timeline([(0,a),(.5,a)],2,dest,config);data,sr=read(dest)
    assert len(data)==48000 and data[int(.75*sr)]==pytest.approx(.4,abs=.001)
    assert data[int(.25*sr)]==pytest.approx(.2,abs=.001) and data[int(1.75*sr)]==0

def test_limiting(tmp_path,config):
    a=tmp_path/'a.wav';write(a,np.ones(24000)*.8);out=tmp_path/'out.wav'
    m=mix_timeline([(0,a),(0,a)],1,out,config);assert m['limiter_engaged'] and np.max(read(out)[0])<=1

def test_export_rejects_long_audio(project,config):
    pipe=Pipeline(project,config);pipe.render();path,metrics=project.artifact('s1');metrics['actual_duration']=6
    with project.connect() as db:db.execute('UPDATE artifacts SET metrics=? WHERE segment=?',(json.dumps(metrics),'s1'))
    with pytest.raises(ValueError,match='exceeds'):pipe.export()

def test_vram_no_silent_fallback(monkeypatch,config):
    from persian_dubbing.core.scheduler import require_vram
    import persian_dubbing.core.telemetry as t
    monkeypatch.setattr(t,'snapshot',lambda:{'vram_total_mb':16000,'vram_used_mb':15500})
    with pytest.raises(RuntimeError):require_vram(config)

def test_quick_explicitly_unavailable(project,config):
    with pytest.raises(ValueError,match='not yet'):Pipeline(project,replace(config,mode='quick')).render()

def test_cancellation_timeout():
    cancel=Cancellation();timer=threading.Timer(.2,cancel.cancel);timer.start();start=time.monotonic()
    with pytest.raises(Cancelled):run([sys.executable,'-c','import time;time.sleep(20)'],cancel=cancel)
    timer.join();assert time.monotonic()-start<5
    with pytest.raises(TimeoutError):run([sys.executable,'-c','import time;time.sleep(20)'],timeout=.15)

def test_process_failure():
    with pytest.raises(RuntimeError,match='exit'):run([sys.executable,'-c','raise SystemExit(3)'])

def test_diarization_alignment():
    from persian_dubbing.speech.diarization import assign_segments
    segments=[Segment('x',0,2)];assign_segments(segments,[{'start':0,'end':.5,'speaker':'A'},{'start':.5,'end':2,'speaker':'B'}])
    assert segments[0].speaker=='B' and segments[0].warnings

def test_capability_gate(project,config):
    segment=project.segments()[0];segment.emotion='excited'
    synthesis,warnings=plan(segment,project.voice_for('A'),config,Capabilities())
    assert synthesis.emotion=='neutral' and warnings

def test_quality_gate(tmp_path):
    from persian_dubbing.quality.audio import gate
    path=tmp_path/'silent.wav';write(path,np.zeros(24000))
    with pytest.raises(ValueError,match='silent'):gate(path)

def test_batch_failure_preserves_completed(project,config,monkeypatch):
    from persian_dubbing.tts.engines import DiagnosticEngine
    import persian_dubbing.core.pipeline as mod
    class Broken(DiagnosticEngine):
        def synthesize_batch(self,jobs,project,cancel=None):
            super().synthesize_batch(jobs[:1],project,cancel);raise RuntimeError('interrupted')
    monkeypatch.setattr(mod,'engine',lambda c:Broken(c))
    with pytest.raises(RuntimeError):Pipeline(project,config).render()
    assert project.artifact('s1') is not None and project.artifact('s2') is None

def test_filename_traversal(project,config):
    segments=project.segments();segments[0].speaker='../../escape';project.save_segments(segments)
    project.assign('../../escape','native');pipe=Pipeline(project,config);pipe.render();folder=pipe.export()
    assert len(list(folder.glob('speaker_*.wav')))==2

def test_cancelled_raw_cache_resumes(project,config,monkeypatch):
    from persian_dubbing.tts.engines import DiagnosticEngine
    import persian_dubbing.core.pipeline as mod
    class Interrupted(DiagnosticEngine):
        def synthesize_batch(self,jobs,project,cancel=None):
            super().synthesize_batch(jobs[:1],project,cancel)
            cancel.cancel();cancel.check()
    monkeypatch.setattr(mod,'engine',lambda c:Interrupted(c))
    with pytest.raises(Cancelled):Pipeline(project,config).render()
    captured=[]
    class Resume(DiagnosticEngine):
        def synthesize_batch(self,jobs,project,cancel=None):
            captured.extend(j['id'] for j in jobs);super().synthesize_batch(jobs,project,cancel)
    monkeypatch.setattr(mod,'engine',lambda c:Resume(c))
    Pipeline(project,config).render()
    assert captured==['s2'] and project.artifact('s1') is not None

def test_project_voice_portability(project,tmp_path):
    import shutil
    moved=tmp_path/'moved';shutil.copytree(project.root,moved)
    voice=Project(moved).voice_for('A')
    assert voice.reference.startswith(str(moved))
    assert voice.selected_reference()==voice.reference

def test_deadline_buffer_policy():
    from persian_dubbing.core.scheduler import DeadlineQueue,PlaybackGate
    queue=DeadlineQueue();queue.push(20,'late');queue.push(5,'first');queue.push(5,'second')
    assert [queue.pop(),queue.pop(),queue.pop()]==['first','second','late']
    gate=PlaybackGate(10)
    assert gate.should_pause(10,15,50)
    assert not gate.should_pause(10,21,50)
    assert not gate.should_pause(45,50,50)

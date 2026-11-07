import os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from persian_dubbing.ui.app import Window
from persian_dubbing.core.config import Config
from persian_dubbing.storage.project import Project
from persian_dubbing.cli import demo

def test_desktop_edit_and_background_job(tmp_path):
    app=QApplication.instance() or QApplication([])
    p=Project(tmp_path/'desktop');demo(p,Config())
    window=Window(Config(tts_engine='diagnostic'));window.project=p;window.refresh();window.show();app.processEvents()
    assert window.table.rowCount()==1 and window.assignments.rowCount()==1
    window.table.item(0,5).setText('سلام دوباره');window.save_table()
    assert p.segments()[0].translation=='سلام دوباره'
    results=[];window.launch(lambda c,progress:42,results.append)
    deadline=time.monotonic()+5
    while window.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not window.busy and results==[42]
    assert window.table.isEnabled()
    window.close();app.processEvents()

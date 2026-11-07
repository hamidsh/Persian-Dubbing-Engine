import json, sys, traceback, uuid
from pathlib import Path
from dataclasses import asdict,replace
from PySide6.QtCore import QThread,Signal,Qt,QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,
    QLabel,QTabWidget,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,QMessageBox,QLineEdit,
    QPlainTextEdit,QComboBox,QInputDialog,QCheckBox,QSplitter,QDialog,QDialogButtonBox,QFormLayout)
from persian_dubbing.core.config import Config
from persian_dubbing.core.pipeline import Pipeline
from persian_dubbing.core.process import Cancellation,Cancelled
from persian_dubbing.core.types import Voice,Segment
from persian_dubbing.storage.project import Project
from persian_dubbing.ui.player import Player

class Task(QThread):
    progress=Signal(str);result=Signal(object);failed=Signal(str)
    def __init__(self,fn,parent=None):
        super().__init__(parent);self.fn=fn;self.cancel=Cancellation()
    def run(self):
        try: self.result.emit(self.fn(self.cancel,self.progress.emit))
        except Cancelled: self.progress.emit('لغو شد؛ نتیجه‌های ذخیره‌شده باقی می‌مانند.')
        except Exception: self.failed.emit(traceback.format_exc())

STYLE="""
QMainWindow,QWidget { background:#131b29; color:#e8eef7; font-family:'Segoe UI'; font-size:13px; }
QPushButton { background:#263950; padding:8px 12px; border:1px solid #3a506c; border-radius:5px; }
QPushButton:hover { background:#355470; } QPushButton:disabled { color:#67758b; }
QLineEdit,QPlainTextEdit,QTableWidget,QComboBox { background:#0b1320; border:1px solid #32445d; padding:5px; }
QHeaderView::section { background:#263950; padding:7px; }
QTabBar::tab { background:#263950; padding:10px 20px; } QTabBar::tab:selected { background:#1d6375; }
QLabel#title { font-size:24px; font-weight:600; } QSplitter::handle { background:#32445d; }
"""

class Window(QMainWindow):
    def __init__(self,config=None):
        super().__init__();self.config=config or Config();self.project=None;self.task=None;self.busy=False;self.lab_rows=[]
        self.setWindowTitle('Persian Dubbing Engine • 0.1');self.resize(1400,900)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        title=QLabel('Persian Dubbing Engine  |  استودیوی دوبله فارسی');title.setObjectName('title');layout.addWidget(title)
        self.banner=QLabel('Quality / Offline • ابتدا پروژه بسازید، سپس مرجع فارسی هر گوینده را تعیین کنید.');layout.addWidget(self.banner)
        bar=QHBoxLayout();layout.addLayout(bar);self.action_buttons=[]
        self.button(bar,'پروژه جدید / بازکردن',self.open_project)
        self.button(bar,'تنظیمات',self.settings)
        self.button(bar,'بررسی نصب',self.doctor)
        self.cancel_button=QPushButton('توقف پردازش');self.cancel_button.setEnabled(False);bar.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self.cancel_task)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.build_editor();self.build_voices();self.build_lab();self.build_export()
        self.logs=QPlainTextEdit();self.logs.setReadOnly(True);self.logs.setMaximumHeight(125);layout.addWidget(self.logs)
        self.status=QLabel('آماده');layout.addWidget(self.status)
        self.setStyleSheet(STYLE)

    def button(self,layout,text,callback):
        button=QPushButton(text);button.clicked.connect(lambda _=False:self.safe(callback));layout.addWidget(button)
        self.action_buttons.append(button);return button
    def safe(self,fn):
        try: fn()
        except Exception as exc: QMessageBox.warning(self,'خطا',str(exc))
    def require(self):
        if not self.project: raise ValueError('ابتدا یک پوشه پروژه انتخاب کنید.')
    def log(self,text): self.logs.appendPlainText(str(text))
    def launch(self,fn,done=None):
        if self.busy: raise ValueError('یک پردازش دیگر فعال است.')
        self.busy=True;self.cancel_button.setEnabled(True)
        self.tabs.setEnabled(False)
        for b in self.action_buttons: b.setEnabled(False)
        self.task=Task(fn,self);self.task.progress.connect(self.log);self.task.failed.connect(self.failure)
        if done: self.task.result.connect(done)
        self.task.finished.connect(self.finished);self.task.start()
    def failure(self,text):
        self.log(text);QMessageBox.warning(self,'پردازش انجام نشد',text[-2500:])
    def finished(self):
        self.busy=False;self.cancel_button.setEnabled(False);self.tabs.setEnabled(True)
        for b in self.action_buttons: b.setEnabled(True)
        self.refresh();self.status.setText('آماده')
        self.task.deleteLater();self.task=None
    def cancel_task(self):
        if self.task: self.task.cancel.cancel();self.status.setText('در حال توقف؛ ممکن است یک فراخوانی مدل تا پایان درخواست جاری ادامه یابد.')
    def closeEvent(self,event):
        if self.busy:
            self.cancel_task();event.ignore();return
        self.player.stop();event.accept()

    def build_editor(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'۱. ویدئو و متن')
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split)
        self.player=Player();split.addWidget(self.player)
        controls=QWidget();col=QVBoxLayout(controls);split.addWidget(controls)
        self.button(col,'ورود ویدئو / صوت',self.ingest)
        self.button(col,'تشخیص گفتار انگلیسی',lambda:self.pipeline_action('transcribe'))
        self.button(col,'تفکیک گویندگان — pyannote اختیاری',lambda:self.pipeline_action('diarize'))
        self.button(col,'ورود SRT',self.import_subtitle)
        self.button(col,'ترجمه جمله‌های ترجمه‌نشده',lambda:self.pipeline_action('translate'))
        col.addWidget(QLabel('متن، زمان و شناسه گوینده را در جدول ویرایش کنید.\nتلفظ دستی از متن ترجمه اولویت بالاتری دارد.'))
        self.table=QTableWidget(0,8);layout.addWidget(self.table,1)
        self.table.setHorizontalHeaderLabels(['ID','شروع','پایان','گوینده','انگلیسی','فارسی','تلفظ دستی','وضعیت'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i in [4,5,6]: self.table.setColumnWidth(i,240)
        row=QHBoxLayout();layout.addLayout(row)
        self.button(row,'ذخیره ویرایش‌ها',self.save_table)
        self.button(row,'افزودن جمله',self.add_segment)
        self.button(row,'حذف جمله منتخب',self.delete_segment)
        self.button(row,'تولید / ادامه همه',lambda:self.render(False))
        self.button(row,'بازتولید جمله منتخب',lambda:self.render(True))
        self.button(row,'شنیدن جمله منتخب',self.play_segment)

    def build_voices(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'۲. گویندگان و Anchor')
        layout.addWidget(QLabel('مرجع‌ها را از صدای فارسی تمیز و دارای مجوز انتخاب کنید. بانک صدای آماده همراه برنامه نیست.'))
        row=QHBoxLayout();layout.addLayout(row)
        self.button(row,'افزودن صدای فارسی',self.add_voice)
        self.voice_combo=QComboBox();row.addWidget(self.voice_combo,1)
        self.button(row,'شنیدن مرجع',self.play_voice)
        self.button(row,'نمونه انگلیسی هدف',self.add_target)
        self.button(row,'ساخت Anchor با Seed-VC',self.anchor)
        self.button(row,'شنیدن Anchor',self.play_anchor)
        self.button(row,'تأیید شنیداری Anchor',self.approve_anchor)
        self.assignments=QTableWidget(0,2);self.assignments.setHorizontalHeaderLabels(['گوینده','صدای فارسی'])
        self.assignments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(self.assignments)
        self.button(layout,'ذخیره تخصیص صداها',self.save_assignments)
        self.voice_info=QPlainTextEdit();self.voice_info.setReadOnly(True);layout.addWidget(self.voice_info)
        self.voice_combo.currentTextChanged.connect(self.show_voice)

    def build_lab(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'۳. آزمایش صدا / A–B')
        layout.addWidget(QLabel('از صدای منتخب در پنل گویندگان استفاده می‌شود. معیار طبیعی‌بودن و شباهت را جداگانه ثبت کنید.'))
        self.lab_text=QPlainTextEdit('سلام، خوش اومدین. امروز می‌خوایم دربارهٔ هوش مصنوعی و آیندهٔ آموزش صحبت کنیم.');self.lab_text.setMaximumHeight(100);layout.addWidget(self.lab_text)
        row=QHBoxLayout();layout.addLayout(row);self.route_checks={}
        for key,label in [('native','مرجع فارسی'),('anchor','Anchor شخصی‌سازی‌شده'),('direct','مرجع مستقیم انگلیسی'),('post_vc','تبدیل بعد از تولید')]:
            check=QCheckBox(label);check.setChecked(key=='native');row.addWidget(check);self.route_checks[key]=check
        self.button(layout,'ساخت نمونه‌های مقایسه',self.run_lab)
        self.lab_table=QTableWidget(0,5);self.lab_table.setHorizontalHeaderLabels(['نمونه','مدت','RTF با بارگذاری','طبیعی‌بودن ۱–۵','شباهت ۱–۵']);layout.addWidget(self.lab_table)
        row=QHBoxLayout();layout.addLayout(row)
        self.button(row,'پخش نمونه منتخب',self.play_lab)
        self.button(row,'ذخیره امتیازها',self.save_ratings)
        self.button(row,'نمایش روش هر نمونه',lambda:self.log(json.dumps(self.lab_rows,ensure_ascii=False,indent=2)))

    def build_export(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'۴. خروجی و عملکرد')
        layout.addWidget(QLabel('خروجی شامل WAV، SRT، صدای مستقل هر گوینده و گزارش است.\nQuick Preview و Live هنوز منتشر نشده‌اند؛ این نسخه با حالت Quality کار می‌کند.'))
        self.background=QLineEdit();self.background.setPlaceholderText('مسیر موسیقی / صدای محیطِ جداشده — اختیاری');layout.addWidget(self.background)
        self.button(layout,'انتخاب صدای پس‌زمینه',self.pick_background)
        self.video_export=QCheckBox('ساخت MP4 دوبله‌شده (نیازمند ویدئوی ورودی)');layout.addWidget(self.video_export)
        self.button(layout,'ساخت خروجی نهایی',self.export)
        self.button(layout,'بازکردن پوشه خروجی',self.open_export)
        self.button(layout,'پخش آخرین خروجی',self.play_export)
        self.button(layout,'اندازه‌گیری منابع فعلی',self.telemetry)
        self.resources=QPlainTextEdit();self.resources.setReadOnly(True);layout.addWidget(self.resources)

    def open_project(self):
        path=QFileDialog.getExistingDirectory(self,'پوشه پروژه')
        if path:
            self.project=Project(path)
            saved=self.project.get('config')
            if saved: self.config=Config(**saved).validate()
            self.banner.setText(str(self.project.root));self.refresh()
            source=self.project.get('source')
            if source and Path(source).exists(): self.player.load(source)
    def settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('تنظیمات JSON — مسیرها، مدل و سرویس ترجمه');dialog.resize(850,650)
        layout=QVBoxLayout(dialog);editor=QPlainTextEdit(json.dumps(asdict(self.config),ensure_ascii=False,indent=2));layout.addWidget(editor)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec():
            config=Config(**json.loads(editor.toPlainText())).validate();self.config=config
            if self.project: self.project.set('config',asdict(config))
            self.log('تنظیمات ذخیره شد؛ تغییر تنظیمات ممکن است نیازمند تولید مجدد باشد.')
    def doctor(self):
        from persian_dubbing.cli import doctor
        self.launch(lambda c,p:doctor(self.config),lambda r:self.log(json.dumps(r,ensure_ascii=False,indent=2)))
    def pipe(self,cancel,progress): return Pipeline(self.project,replace(self.config),cancel,progress)
    def ingest(self):
        self.require();path,_=QFileDialog.getOpenFileName(self,'ویدئو یا صوت')
        if path: self.launch(lambda c,p:self.pipe(c,p).ingest(path),lambda _:self.player.load(path))
    def pipeline_action(self,name):
        self.require();self.save_table()
        if name=='transcribe' and self.project.segments():
            if QMessageBox.question(self,'بازنویسی متن','تشخیص دوباره، متن و ویرایش‌های فعلی را جایگزین می‌کند. ادامه؟')!=QMessageBox.StandardButton.Yes:return
        self.launch(lambda c,p:getattr(self.pipe(c,p),name)())
    def import_subtitle(self):
        self.require();path,_=QFileDialog.getOpenFileName(self,'SRT',filter='Subtitles (*.srt)')
        if not path:return
        if self.project.segments() and QMessageBox.question(self,'جایگزینی متن','جمله‌های موجود جایگزین شوند؟')!=QMessageBox.StandardButton.Yes:return
        choice,ok=QInputDialog.getItem(self,'زبان','زبان فایل',['English','فارسی'],0,False)
        if ok:
            from persian_dubbing.media.subtitles import import_srt
            self.project.save_segments(import_srt(path,choice=='فارسی'));self.refresh()
    def refresh(self):
        if not self.project:return
        segments=self.project.segments();self.table.setRowCount(len(segments))
        for row,s in enumerate(segments):
            artifact=self.project.artifact(s.id);status='تولید نشده'
            if artifact: status='تولید شده — اعتبار هنگام خروجی بررسی می‌شود'
            if artifact and artifact[1].get('warnings'): status=' | '.join(artifact[1]['warnings'])
            values=[s.id,f'{s.start:.3f}',f'{s.end:.3f}',s.speaker,s.source,s.translation,s.pronunciation,status]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                if col in (0,7):item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row,col,item)
        previous=self.voice_combo.currentText();self.voice_combo.clear();self.voice_combo.addItems(list(self.project.voices()))
        if previous in self.project.voices():self.voice_combo.setCurrentText(previous)
        speakers=sorted({s.speaker for s in segments});mapping=self.project.assignments();self.assignments.setRowCount(len(speakers))
        for row,speaker in enumerate(speakers):
            item=QTableWidgetItem(speaker);item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable);self.assignments.setItem(row,0,item)
            combo=QComboBox();combo.addItem('— انتخاب صدا —','');
            for voice in self.project.voices():combo.addItem(voice,voice)
            index=combo.findData(mapping.get(speaker,''));combo.setCurrentIndex(max(0,index));self.assignments.setCellWidget(row,1,combo)
    def save_table(self):
        self.require();old={s.id:s for s in self.project.segments()};segments=[]
        for row in range(self.table.rowCount()):
            values=[self.table.item(row,col).text() for col in range(7)]
            segment=old[values[0]];segment.start=float(values[1]);segment.end=float(values[2]);segment.speaker=values[3].strip()
            segment.source=values[4];segment.translation=values[5];segment.pronunciation=values[6]
            segments.append(segment.validate())
        self.project.save_segments(segments);self.project.set('config',asdict(self.config))
    def selected_segment(self):
        row=self.table.currentRow()
        if row<0:raise ValueError('یک جمله انتخاب کنید.')
        return self.table.item(row,0).text()
    def add_segment(self):
        self.save_table();segments=self.project.segments();start=max([s.end for s in segments],default=0)
        segments.append(Segment('s'+uuid.uuid4().hex[:8],start,start+3));self.project.save_segments(segments);self.refresh()
    def delete_segment(self):
        self.save_table();sid=self.selected_segment();self.project.save_segments([s for s in self.project.segments() if s.id!=sid]);self.refresh()
    def render(self,selected):
        self.save_table();self.save_assignments();ids=[self.selected_segment()] if selected else None
        self.launch(lambda c,p:self.pipe(c,p).render(ids,force=selected))
    def play_segment(self):
        self.require();sid=self.selected_segment();artifact=self.project.artifact(sid)
        if not artifact:raise ValueError('هنوز تولید نشده است.')
        self.player.load(artifact[0],True)
    def voice(self):
        self.require();key=self.voice_combo.currentText()
        if not key:raise ValueError('ابتدا صدای فارسی اضافه کنید.')
        return self.project.voices()[key]
    def show_voice(self,*_):
        if self.project and self.voice_combo.currentText() in self.project.voices():
            self.voice_info.setPlainText(json.dumps(asdict(self.voice()),ensure_ascii=False,indent=2))
    def add_voice(self):
        self.require();path,_=QFileDialog.getOpenFileName(self,'مرجع فارسی تمیز',filter='Audio (*.wav *.flac *.mp3 *.m4a)')
        if not path:return
        name,ok=QInputDialog.getText(self,'شناسه صدا','نام یکتا:')
        if not ok or not name.strip():return
        if name in self.project.voices():raise ValueError('شناسه تکراری است.')
        license,ok=QInputDialog.getText(self,'مجوز','مجوز یا توضیح اجازه استفاده:',text='user-provided with permission')
        if not ok:return
        self.project.save_voice(Voice(name,self.project.import_reference(path),license=license));self.refresh()
    def play_voice(self): self.player.load(self.voice().reference,True);self.tabs.setCurrentIndex(0)
    def add_target(self):
        voice=self.voice();path,_=QFileDialog.getOpenFileName(self,'نمونه تمیز گوینده اصلی')
        if path:
            voice.target=self.project.import_reference(path);voice.anchor_approved=False;self.project.save_voice(voice);self.show_voice()
    def anchor(self):
        from persian_dubbing.voices.seed import create_anchor
        voice=self.voice();self.launch(lambda c,p:create_anchor(voice,self.project,self.config,c),lambda path:self.log('Anchor آماده شنیدن: '+str(path)))
    def play_anchor(self):
        voice=self.voice()
        if not voice.anchor:raise ValueError('ابتدا Anchor بسازید.')
        self.player.load(voice.anchor,True);self.tabs.setCurrentIndex(0)
    def approve_anchor(self):
        voice=self.voice()
        if not voice.anchor or not Path(voice.anchor).exists():raise ValueError('Anchor موجود نیست.')
        voice.anchor_approved=True;self.project.save_voice(voice);self.show_voice();self.log('Anchor تأیید شد؛ برای استفاده، route را در تنظیمات روی anchor بگذارید.')
    def save_assignments(self):
        self.require()
        for row in range(self.assignments.rowCount()):
            voice=self.assignments.cellWidget(row,1).currentData()
            if voice:self.project.assign(self.assignments.item(row,0).text(),voice)
    def run_lab(self):
        from persian_dubbing.quality.benchmark import compare
        voice=self.voice();text=self.lab_text.toPlainText().strip();routes=[r for r,c in self.route_checks.items() if c.isChecked()]
        if not text or not routes:raise ValueError('متن و حداقل یک روش را انتخاب کنید.')
        self.launch(lambda c,p:compare(text,voice,self.project,self.config,routes,c,p),self.lab_done)
    def lab_done(self,rows):
        self.lab_rows=rows;self.lab_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,value in enumerate([r['blind_id'],f"{r['duration']:.2f}",f"{r['wall_rtf_including_load']:.2f}",'','']):
                item=QTableWidgetItem(value)
                if j<3:item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable)
                self.lab_table.setItem(i,j,item)
    def play_lab(self):
        row=self.lab_table.currentRow()
        if row<0:raise ValueError('نمونه‌ای انتخاب کنید.')
        self.player.load(self.lab_rows[row]['path'],True)
    def save_ratings(self):
        if not self.lab_rows:raise ValueError('ابتدا آزمایش را اجرا کنید.')
        scores=[]
        for i,r in enumerate(self.lab_rows):
            values=[]
            for col in (3,4):
                text=self.lab_table.item(i,col).text();value=int(text) if text else None
                if value is not None and not 1<=value<=5:raise ValueError('امتیاز باید از ۱ تا ۵ باشد.')
                values.append(value)
            scores.append({'sample':r['blind_id'],'naturalness':values[0],'similarity':values[1]})
        path=Path(self.lab_rows[0]['path']).parent/'ratings.json';path.write_text(json.dumps(scores,ensure_ascii=False,indent=2),encoding='utf-8');self.log(str(path))
    def pick_background(self):
        path,_=QFileDialog.getOpenFileName(self,'صدای محیط یا موسیقی جداشده')
        if path:self.background.setText(path)
    def export(self):
        self.save_table();background=self.background.text().strip() or None;video=self.video_export.isChecked()
        self.launch(lambda c,p:self.pipe(c,p).export(video,background),lambda path:self.log('خروجی ذخیره شد: '+str(path)))
    def open_export(self):
        self.require();QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.root/'exports')))
    def play_export(self):
        self.require();folder=self.project.get('last_export')
        if not folder:raise ValueError('خروجی موجود نیست.')
        path=Path(folder)/'dubbed.mp4'
        if not path.exists():path=Path(folder)/'dubbed.wav'
        self.player.load(path,True);self.tabs.setCurrentIndex(0)
    def telemetry(self):
        from persian_dubbing.core.telemetry import snapshot
        self.launch(lambda c,p:snapshot(),lambda result:self.resources.setPlainText(json.dumps(result,indent=2)))


def main(config=None):
    app=QApplication.instance() or QApplication(sys.argv)
    window=Window(config);window.show();return app.exec()

if __name__=='__main__':raise SystemExit(main())

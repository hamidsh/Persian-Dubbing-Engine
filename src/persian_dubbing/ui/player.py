from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QSlider,QLabel
from PySide6.QtCore import Qt,QUrl
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class Player(QWidget):
    def __init__(self):
        super().__init__();layout=QVBoxLayout(self)
        self.view=QVideoWidget();self.view.setMinimumHeight(180);layout.addWidget(self.view)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(.8)
        self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.view)
        controls=QHBoxLayout();layout.addLayout(controls)
        play=QPushButton('▶ / ❚❚');play.clicked.connect(self.toggle);controls.addWidget(play)
        self.seek=QSlider(Qt.Orientation.Horizontal);controls.addWidget(self.seek)
        self.time=QLabel('00:00');controls.addWidget(self.time)
        self.seek.sliderMoved.connect(self.player.setPosition)
        self.player.durationChanged.connect(lambda d:self.seek.setRange(0,d))
        self.player.positionChanged.connect(self.position)
        self.player.errorOccurred.connect(lambda *_:self.time.setText(self.player.errorString()))
    def position(self,value):
        if not self.seek.isSliderDown(): self.seek.setValue(value)
        self.time.setText(f'{value//60000:02}:{value//1000%60:02}')
    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else: self.player.play()
    def load(self,path,play=False):
        self.player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        if play: self.player.play()
    def stop(self): self.player.stop()

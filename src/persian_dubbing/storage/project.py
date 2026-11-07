import sqlite3, json, hashlib, uuid, shutil
from pathlib import Path
from dataclasses import asdict
from contextlib import contextmanager
from persian_dubbing.core.types import Segment, Voice


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("audio", "cache", "exports", "references", "logs", "jobs"):
            (self.root / name).mkdir(exist_ok=True)
        self.db = self.root / "project.sqlite3"
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS segments (id TEXT PRIMARY KEY, start REAL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS voices (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assignments (speaker TEXT PRIMARY KEY, voice TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts (segment TEXT PRIMARY KEY, key TEXT, path TEXT, metrics TEXT);
            CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, at TEXT DEFAULT CURRENT_TIMESTAMP, kind TEXT, data TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db: yield db
        finally:
            db.close()

    def set(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def save_segments(self, segments):
        items = [s.validate() for s in segments]
        if len({s.id for s in items}) != len(items): raise ValueError("Duplicate segment IDs")
        with self.connect() as db:
            db.execute("DELETE FROM segments")
            db.executemany("INSERT INTO segments VALUES (?,?,?)", [(s.id,s.start,json.dumps(asdict(s),ensure_ascii=False)) for s in items])
            db.execute("DELETE FROM artifacts WHERE segment NOT IN (SELECT id FROM segments)")
            db.execute("INSERT INTO history(kind,data) VALUES ('segments',?)", (json.dumps([asdict(s) for s in items],ensure_ascii=False),))

    def segments(self):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM segments ORDER BY start,id").fetchall()
        return [Segment(**json.loads(r[0])) for r in rows]

    def update_segment(self, segment):
        segment.validate()
        with self.connect() as db:
            db.execute("UPDATE segments SET start=?,data=? WHERE id=?", (segment.start,json.dumps(asdict(segment),ensure_ascii=False),segment.id))
            db.execute("INSERT INTO history(kind,data) VALUES ('edit',?)", (json.dumps(asdict(segment),ensure_ascii=False),))

    def import_reference(self, source):
        source = Path(source).resolve()
        dest = self.root / "references" / (file_hash(source)[:20] + source.suffix.lower())
        if not dest.exists(): shutil.copy2(source, dest)
        return str(dest)

    def save_voice(self, voice):
        record=asdict(voice)
        for key in ('reference','target','anchor'):
            if record[key]:
                try: record[key]=str(Path(record[key]).resolve().relative_to(self.root))
                except ValueError: record[key]=str(Path(record[key]).resolve())
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO voices VALUES (?,?)", (voice.id,json.dumps(record,ensure_ascii=False)))
            db.execute("INSERT INTO history(kind,data) VALUES ('voice',?)", (json.dumps(asdict(voice),ensure_ascii=False),))

    def voices(self):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM voices ORDER BY id").fetchall()
        result={}
        for row in rows:
            record=json.loads(row[0])
            for key in ('reference','target','anchor'):
                if record[key] and not Path(record[key]).is_absolute():record[key]=str(self.root/record[key])
            voice=Voice(**record);result[voice.id]=voice
        return result

    def assign(self, speaker, voice_id):
        if voice_id not in self.voices(): raise ValueError("Unknown voice")
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO assignments VALUES (?,?)", (speaker,voice_id))

    def assignments(self):
        with self.connect() as db: return dict(db.execute("SELECT speaker,voice FROM assignments").fetchall())

    def voice_for(self, speaker):
        voice_id = self.assignments().get(speaker)
        if not voice_id: raise ValueError(f"Assign a Persian voice to {speaker} first")
        return self.voices()[voice_id]

    def artifact(self, segment, key=None):
        with self.connect() as db:
            row = db.execute("SELECT key,path,metrics FROM artifacts WHERE segment=?", (segment,)).fetchone()
        if not row or (key is not None and row[0] != key): return None
        path = self.root / row[1]
        if not path.is_file(): return None
        return path, json.loads(row[2])

    def save_artifact(self, segment, key, path, metrics):
        relative = str(Path(path).resolve().relative_to(self.root))
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO artifacts VALUES (?,?,?,?)", (segment,key,relative,json.dumps(metrics)))

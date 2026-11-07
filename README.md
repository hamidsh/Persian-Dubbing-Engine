# Persian Dubbing Engine

استودیوی محلی دوبله فارسی برای Windows 11، با معماری ماژولار و اولویت تلفظ طبیعی فارسی.

**نسخه 0.1 یک MVP آفلاین است، نه تکمیل همه فازهای سند.** رابط دسکتاپ و هسته صوتی تست شده‌اند؛ inference واقعی مدل‌های بزرگ، نصب کامل Windows/CUDA، کیفیت فارسی و هدف بافر ۱۰ ثانیه در این محیط تأیید نشده‌اند. مدل‌ها همراه کد نیستند. تست تشخیصی از بوق استفاده می‌کند و دوبله محسوب نمی‌شود.

## شروع در ویندوز — بدون Conda

۱. Python **3.11**، Git for Windows و FFmpeg را نصب کنید. برای FFmpeg:

```powershell
winget install --id Gyan.FFmpeg -e
```

۲. پروژه را دریافت کنید و `install.bat` را اجرا کنید:

```powershell
git clone https://github.com/hamidsh/Persian-Dubbing-Engine.git
cd Persian-Dubbing-Engine
.\install.bat
```

۳. محیط جداگانه MOSS را نصب کنید:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_moss.ps1
```

۴. `run.bat` را اجرا کنید. یک پوشه پروژه جدید بسازید. در پنل گویندگان، مرجع فارسی تمیز و دارای اجازه استفاده اضافه کنید. برای اولین تست فقط پنل **آزمایش صدا / A–B → مرجع فارسی** را اجرا کنید. دانلود وزن‌های MOSS، LoRA و codec در اولین تولید انجام می‌شود. در نصب MOSS، کد مدل codec با `trust_remote_code=True` از مخزن رسمی بارگذاری می‌شود؛ revisionها در تنظیمات قابل تثبیت هستند.

۵. بعد از شنیدن خروجی مناسب، ویدئو را وارد کنید، Whisper را اجرا کنید، متن را ترجمه/ویرایش کنید، به هر گوینده صدا اختصاص دهید و تولید و خروجی را بزنید.

[راهنمای کامل نصب و کار](docs/QUICKSTART_FA.md) · [وضعیت الزامات](docs/STATUS.md) · [سند اصلی شما](docs/ARCHITECTURE_FA.md) · [بنچمارک](docs/BENCHMARK.md)

## امکانات پیاده‌سازی‌شده

- رابط PySide6 فارسی، پلیر Qt، پنل ویرایش زمان/گوینده/انگلیسی/فارسی/تلفظ، پنل صدا و A/B و خروجی؛ CLI مستقل.
- استخراج صوت با FFmpeg؛ ASR انگلیسی Faster-Whisper با Silero VAD داخلی و زمان کلمات؛ شکستن قطعات بلند در سطح کلمه.
- مترجم دارای قرارداد JSON سازگار با `llama-server`، زمینه قبل/بعد جمله و محدودیت زمانی در prompt؛ امکان واردکردن SRT فارسی بدون مترجم.
- نرمال‌سازی حروف و اعداد، واژه‌نامه پروژه، اولویت اصلاح تلفظ دستی، علامت‌گذاری هم‌نگاره‌ها؛ عدم ارسال IPA یا تگ احساس به مدل فاقد پشتیبانی.
- آداپتور واقعی MOSS-Realtime + Persian LoRA، worker مجزا با بارگذاری یک‌باره در هر batch؛ خروجی هر جمله اتمیک و قابل ادامه.
- Seed-VC v2 با `convert-style=false`: ساخت Anchor، تبدیل بعد از TTS؛ تأیید شنیداری جدا از کنترل فنی صدا.
- آزمایش چهار مسیر native / anchor / direct English / post-VC با ترتیب تصادفی نمونه‌ها، زمان، RTF و امتیازهای شنیداری.
- SQLite، تاریخچه ویرایش‌ها، کپی مرجع‌ها در پروژه، cache مبتنی بر محتوای مرجع/متن/تنظیمات، بازتولید انتخابی، توقف worker و فرزندانش.
- تفکیک گویندگان اختیاری pyannote Community-1 در محیط جدا؛ انتساب بر پایه هم‌پوشانی زمانی و هشدار برای قطعات چندگوینده؛ اصلاح دستی همیشه ممکن است.
- میکس بلوکی با مصرف حافظه محدود، هم‌پوشانی روی stem مستقل، limiter، محدودیت کشش Rubber Band؛ WAV، SRT، JSON، stem و MP4.
- سنجش CPU/RAM/GPU/VRAM، ثبت زمان و RTF MOSS، جلوگیری از شروع وقتی حاشیه آزاد VRAM ناکافی است؛ هیچ تعویض خودکار صدایی وجود ندارد.

## وضعیت صادقانه

این نسخه مسیر **Quality / Offline** را اجرا می‌کند. Quick Preview، Live Simulation، scheduler تطبیقی پخش، انتخاب خودکار صدای بانک بر اساس embedding، G2P معنایی/IPA، تشخیص احساس صوتی، جداسازی خودکار Demucs و موتورهای جایگزین هنوز محصول آماده نیستند. هسته deadline/buffer برای توسعه وجود دارد ولی به پلیر متصل نشده است. گزینه‌های quick/live خطای واضح می‌دهند، نه رفتار شبیه‌سازی‌شده.

۸ تا ۱۲ صدای حرفه‌ای همراه برنامه ارائه نشده است؛ مرجع‌های فارسی را خودتان اضافه کنید. امکان ادعای «کیفیت اثبات‌شده»، «بدون باگ» یا «اجرای real-time روی 4060 Ti» بدون تست محلی وجود ندارد.

## تست بدون مدل

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\pde.exe doctor
.\.venv\Scripts\pde.exe --project projects/diagnostic demo
```

دمو فقط بوق آزمایشی تولید می‌کند تا ذخیره/میکس/خروجی را بررسی کند. برای ادامه همان دمو از `--config projects/diagnostic/demo-config.json` استفاده کنید. تست‌ها دانلود مدل یا دسترسی به GPU لازم ندارند. CI برای Python 3.11 روی Windows و Linux تعریف شده است؛ نتیجه CI را در Actions ببینید.

## ساختار

```text
src/persian_dubbing/
  core/               پیکربندی، orchestration، لغو، plan، telemetry و سیاست صف
  media/              FFmpeg، میکس بلوکی، SRT
  speech/             Whisper و worker اختیاری diarization
  translation/        کلاینت llama.cpp با قرارداد JSON
  persian_frontend/   متن فارسی، اعداد و واژه‌نامه
  voices/             تبدیل Seed-VC و ساخت Anchor
  tts/                adapter و worker مستقل MOSS
  quality/            gate فنی و آزمایش چهار مسیر
  storage/            پروژه SQLite و cache
  ui/                 پنل‌های PySide6 و پلیر
scripts/              نصب venvهای جدا در ویندوز
examples/             متن آزمون، SRT دوگوینده و واژه‌نامه
```

وزن‌ها و کدهای طرف ثالث مجوز مستقل دارند؛ لینک و revisionهای بررسی‌شده در [SOURCES.md](docs/SOURCES.md) آمده‌اند. نمونه‌های صوتی، HF_TOKEN و پروژه‌های شخصی در Git ثبت نمی‌شوند. مترجم پیش‌فرض فقط به `127.0.0.1` وصل می‌شود. برنامه تنظیمات شبکه، route، proxy سیستم یا firewall را تغییر نمی‌دهد.

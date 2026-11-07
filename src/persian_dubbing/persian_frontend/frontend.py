"""Conservative orthographic frontend. Ambiguity is flagged, never guessed."""
import re, unicodedata

ONES = 'صفر یک دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده پانزده شانزده هفده هجده نوزده'.split()
TENS = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
HUNDREDS = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']

def number(n):
    n = int(n)
    if n < 0: return 'منفی ' + number(-n)
    if n < 20: return ONES[n]
    if n < 100: return TENS[n//10] + (' و '+number(n%10) if n%10 else '')
    if n < 1000: return HUNDREDS[n//100] + (' و '+number(n%100) if n%100 else '')
    for scale, name in [(10**12,'تریلیون'),(10**9,'میلیارد'),(10**6,'میلیون'),(1000,'هزار')]:
        if n >= scale:
            return number(n//scale)+' '+name+(' و '+number(n%scale) if n%scale else '')


def normalize(text, dictionary=None):
    text = unicodedata.normalize('NFC', text).translate(str.maketrans('يك٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', 'یک01234567890123456789'))
    text = text.replace('ـ', '').replace('\u200f', '').replace('\u200e', '')
    text = re.sub(r'[ \t]+', ' ', text).strip()
    for word, replacement in sorted((dictionary or {}).items(), key=lambda x:-len(x[0])):
        text = re.sub(r'(?<!\w)'+re.escape(word)+r'(?!\w)', lambda _:replacement, text)
    warnings = []
    if re.search(r'\d[/:]\d', text): warnings.append('Date/time requires manual pronunciation review')
    def numeric(match):
        raw = match.group().replace(',', '').replace('٬', '').replace('٫','.')
        if len(raw.lstrip('-').split('.')[0]) > 15:
            return ' '.join(ONES[int(c)] if c.isdigit() else c for c in raw)
        if '.' in raw:
            a,b = raw.split('.')
            return number(a)+' ممیز '+ ' '.join(ONES[int(c)] for c in b)
        if len(raw)>1 and raw[0]=='0': return ' '.join(ONES[int(c)] for c in raw)
        return number(raw)
    text = re.sub(r'(?<![\w])[-−]?\d+(?:[,٬]\d{3})*(?:[.٫]\d+)?', lambda m:numeric(m) if not m.group().startswith('−') else 'منفی '+numeric(re.match(r'.+',m.group()[1:])), text)
    text = text.replace('%',' درصد').replace('٪',' درصد')
    for word in ['مرد','گل','کرم']:
        if re.search(r'(?<!\w)'+word+r'(?!\w)', text): warnings.append(f'هم‌نگاره نیازمند بررسی: {word}')
    return text, warnings


def chunks(text, max_chars=180):
    parts, current = [], ''
    for word in text.split():
        if current and len(current)+len(word)+1 > max_chars:
            parts.append(current); current=''
        current = (current+' '+word).strip()
        if len(current)>45 and current[-1:] in '.!?؟؛': parts.append(current); current=''
    if current: parts.append(current)
    return parts

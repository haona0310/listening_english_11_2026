"""Phân loại độ khó nghe TƯƠNG ĐỐI (A/B/C) của một video từ transcript đã làm sạch.

3 chỉ số, mỗi chỉ số 0–2 điểm, tổng 0–6:
  - wpm      : tốc độ nói (từ/phút, tính trên thời lượng các đoạn)   <130:0 | 130–165:1 | >165:2
  - rarePct  : % từ (>2 ký tự) ngoài nhóm từ phổ biến (Zipf < 4.0)    <4%:0  | 4–8%:1    | >=8%:2
  - avgSent  : số từ trung bình mỗi câu                                <12:0  | 12–18:1   | >18:2
  A: 0–1 điểm · B: 2–4 điểm · C: 5–6 điểm
Ngưỡng là quy ước của app (heuristic), không phải chuẩn CEFR chính thức.

Dùng: python3 level.py data/videos/<id>.json [--write]   (--write: ghi level vào file video + data/index.json)
"""
import json, re, sys, os
from wordfreq import zipf_frequency

def stats(v):
    text = ' '.join(l['en'] for s in v['segments'] for l in s['lines'])
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    words = re.findall(r"[A-Za-z]+(?:'[a-z]+)?", text)
    secs = sum(s['end'] - s['start'] for s in v['segments'])
    sents = [x for x in re.split(r'[.!?]+', text) if re.search(r'[A-Za-z]', x)]
    content = [w.lower() for w in words if len(w) > 2]
    rare = [w for w in content if zipf_frequency(w, 'en') < 4.0]
    return {'wpm': round(len(words) / secs * 60),
            'rarePct': round(len(rare) / len(content) * 100, 1),
            'avgSent': round(len(words) / len(sents), 1)}

def score(st):
    p = lambda x, a, b: (x >= a) + (x >= b)
    return p(st['wpm'], 130, 166) + p(st['rarePct'], 4, 8) + p(st['avgSent'], 12, 18.01)

def level(st):
    sc = score(st)
    return ('A' if sc <= 1 else 'B' if sc <= 4 else 'C'), sc

if __name__ == '__main__':
    write = '--write' in sys.argv
    for f in [a for a in sys.argv[1:] if not a.startswith('--')]:
        v = json.load(open(f, encoding='utf-8'))
        st = stats(v); lv, sc = level(st)
        print(f"{v['id']}: {lv} (điểm {sc}/6) {st}")
        if write:
            v['level'] = lv; v['levelStats'] = st
            json.dump(v, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            ip = os.path.join(os.path.dirname(os.path.dirname(f)), 'index.json')
            idx = json.load(open(ip, encoding='utf-8'))
            for e in idx['videos']:
                if e['id'] == v['id']: e['level'] = lv; e['levelStats'] = st
            json.dump(idx, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

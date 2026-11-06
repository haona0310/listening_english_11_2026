"""Hoàn thiện một file video mới: kiểm tra, xáo vị trí đáp án, chấm trình độ, cập nhật data/index.json.

Dùng: python3 tools/finalize.py data/videos/<id>.json [--topic-name "Tên chủ đề"]
- Xáo đáp án chỉ chạy 1 lần (đánh dấu "shuffled": true), đồng thời sửa "Đáp án X" trong giải thích.
"""
import json, os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from level import stats, level

f = sys.argv[1]
topic_name = sys.argv[sys.argv.index('--topic-name') + 1] if '--topic-name' in sys.argv else None
v = json.load(open(f, encoding='utf-8'))

# 1) Kiểm tra
for s in v['segments']:
    assert s['start'] < s['end'], s['id']
    for l in s['lines']:
        assert s['start'] - 0.5 <= l['t'] < s['end'], (s['id'], l['t'])
    for q in s['questions']:
        assert len(q['options']) == 4 and 0 <= q['answer'] < 4, (s['id'], q['q'])
        assert all(0 <= c < len(s['lines']) for c in q['clue']), (s['id'], q['q'])

# 2) Xáo đáp án (cân bằng A/B/C/D)
if not v.get('shuffled'):
    rnd = random.Random(v['id'])
    qs = [q for s in v['segments'] for q in s['questions']]
    targets = [i % 4 for i in range(len(qs))]; rnd.shuffle(targets)
    for q, t in zip(qs, targets):
        others = [i for i in range(4) if i != q['answer']]; rnd.shuffle(others)
        order = others[:]; order.insert(t, q['answer'])
        newpos = {old: new for new, old in enumerate(order)}
        q['options'] = [q['options'][o] for o in order]; q['answer'] = t
        q['explain'] = re.sub(r'(Đáp án )([ABCD])', lambda m: m[1] + 'ABCD'[newpos['ABCD'.index(m[2])]], q['explain'])
    v['shuffled'] = True

# 3) Trình độ
st = stats(v); lv, sc = level(st)
v['level'] = lv; v['levelStats'] = st
json.dump(v, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# 4) index.json
ip = os.path.join(os.path.dirname(os.path.dirname(f)), 'index.json')
idx = json.load(open(ip, encoding='utf-8'))
if not any(t['id'] == v['topic'] for t in idx['topics']):
    assert topic_name, f"Chủ đề mới '{v['topic']}' cần --topic-name"
    idx['topics'].append({'id': v['topic'], 'name': topic_name})
entry = {k: v[k] for k in ('id', 'topic', 'youtubeId', 'title', 'duration')}
entry.update(level=lv, segments=len(v['segments']), questions=sum(len(s['questions']) for s in v['segments']), levelStats=st)
idx['videos'] = [e for e in idx['videos'] if e['id'] != v['id']] + [entry]
json.dump(idx, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
from collections import Counter
print(f"{v['id']}: {lv} ({sc}/6) {st} | đoạn {entry['segments']} | câu {entry['questions']} | đáp án",
      dict(Counter('ABCD'[q['answer']] for s in v['segments'] for q in s['questions'])))

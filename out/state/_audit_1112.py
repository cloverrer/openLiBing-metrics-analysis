# -*- coding: utf-8 -*-
"""11-12 归档完整性审计：与 11-10/11-11 交叉比对，找遗漏与结构缺口。

判据（都是「该有却没有」的确定性证据）：
  1) 同一组件下，别的日子有、11-12 没有的流水线；
  2) 流水线目录里缺 pipeline.json / _day.json 里没登记它 / 目录存在但 running 完没有运行历史；
  3) 当天运行里 failed/canceled 却没有对应 records（失败执行记录）；
  4) 证据文件缺失（pipeline.evidence.json 不存在或内嵌日志为空）；
  5) 编译维度应有 bc/bpc 却为 null（github 平台按口径不算，单独列出）。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join('out', 'archive', '2026', '2026-11')
DAYS = ['2026-11-10', '2026-11-11', '2026-11-12']
TARGET = '2026-11-12'


def jload(p):
    try:
        with io.open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'__err__': str(e)}


def scan(day):
    out = {}
    base = os.path.join(ROOT, day)
    for comp in sorted(os.listdir(base)):
        cdir = os.path.join(base, comp)
        if not os.path.isdir(cdir):
            continue
        for pl in sorted(os.listdir(cdir)):
            pdir = os.path.join(cdir, pl)
            if not os.path.isdir(pdir):
                continue
            rec = {'dir': pdir, 'has_pipe': False, 'has_ev': False, 'ev_bytes': 0}
            pj = os.path.join(pdir, 'pipeline.json')
            if os.path.exists(pj):
                d = jload(pj)
                rec['has_pipe'] = True
                rec['doc'] = d
                steps = (d.get('steps') or {})
                s2 = steps.get('step_2_runs') or {}
                rh = s2.get('runHistory') or []
                rec['runs'] = rh
                rec['platform'] = (d.get('platform') or '')
                rec['counts'] = d.get('counts') or {}
            else:
                rec['doc'] = {}
                rec['runs'] = []
                rec['platform'] = ''
                rec['counts'] = {}
            ev = os.path.join(pdir, 'pipeline.evidence.json')
            if os.path.exists(ev):
                rec['has_ev'] = True
                rec['ev_bytes'] = os.path.getsize(ev)
                rec['ev'] = jload(ev)
            out[(comp, pl)] = rec
    return out


data = {d: scan(d) for d in DAYS}
dayjson = {d: jload(os.path.join(ROOT, d, '_day.json')) for d in DAYS}

print('=' * 78)
print('一、每天归档流水线数 & _day.json 登记数')
for d in DAYS:
    dj = dayjson[d]
    pls = dj.get('pipelines') or []
    print('  %s  目录 %d 条 | _day.json 登记 %d 条 | counts=%s'
          % (d, len(data[d]), len(pls), json.dumps(dj.get('counts'), ensure_ascii=False)))

print()
print('=' * 78)
print('二、同一组件下「前一日有、%s 没有」的流水线' % TARGET)
tgt = data[TARGET]
prev = data['2026-11-11']
prev2 = data['2026-11-10']
miss_prev = sorted(set(prev) - set(tgt))
miss_prev2 = sorted(set(prev2) - set(tgt))
print('  11-11 有而 11-12 没有：%d 条' % len(miss_prev))
for c, p in miss_prev:
    print('    - %s / %s' % (c, p))
print('  11-10 有而 11-12 没有：%d 条' % len(miss_prev2))
for c, p in miss_prev2:
    print('    - %s / %s' % (c, p))

print()
print('=' * 78)
print('三、%s 每条流水线的结构缺口（缺文件 / 无运行 / 无证据 / 失败无记录）' % TARGET)
issues = []
no_runs, no_ev, no_rec, bad_ev, no_bc = [], [], [], [], []
for (c, p), r in sorted(tgt.items()):
    runs = r.get('runs') or []
    failed = [h for h in runs if str(h.get('status')).upper() in ('FAILED', 'CANCELED')]
    nrec = len((r.get('doc') or {}).get('records') or [])
    if not r['has_pipe']:
        issues.append((c, p, '缺 pipeline.json'))
    if not runs:
        no_runs.append((c, p))
    if not r['has_ev']:
        no_ev.append((c, p))
    elif r['ev_bytes'] < 200:
        issues.append((c, p, '证据文件仅 %d 字节' % r['ev_bytes']))
    if failed and nrec == 0:
        no_rec.append((c, p, len(failed)))
    ev = r.get('ev') or {}
    bad = ev.get('__err__')
    if bad:
        bad_ev.append((c, p, bad))
    has_bc = any(h.get('bc') is not None for h in runs)
    if not has_bc and r.get('platform') != 'github':
        no_bc.append((c, p, r.get('platform')))
print('  结构性报错：%d' % len(issues))
for x in issues:
    print('    ! %s / %s : %s' % x)
print('  当天无运行历史：%d 条' % len(no_runs))
for c, p in no_runs:
    print('    - %s / %s' % (c, p))
print('  缺证据文件：%d 条' % len(no_ev))
for c, p in no_ev:
    print('    - %s / %s' % (c, p))
print('  有失败运行但 records 为空：%d 条' % len(no_rec))
for c, p, n in no_rec:
    print('    - %s / %s（失败 %d 次）' % (c, p, n))
print('  证据文件读不出：%d 条' % len(bad_ev))
for x in bad_ev:
    print('    - %s / %s : %s' % x)
print('  非 github 平台且无任何 bc 值：%d 条' % len(no_bc))
for x in no_bc:
    print('    - %s / %s : platform=%s' % x)

print()
print('=' * 78)
print('四、%s 运行状态分布 / 平台分布' % TARGET)
from collections import Counter
st, pf = Counter(), Counter()
for (c, p), r in tgt.items():
    pf[r.get('platform') or '--'] += 1
    for h in (r.get('runs') or []):
        st[str(h.get('status'))] += 1
print('  平台：', dict(pf))
print('  状态：', dict(st))

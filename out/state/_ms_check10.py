# -*- coding: utf-8 -*-
import json
from pathlib import Path
from collections import Counter

d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
for key, v in d.items():
    if not isinstance(v, dict) or 'code' in v:
        continue
    recs = v.get('records') or []
    print('%-40s records=%d' % (key, len(recs)))
    if not recs:
        continue
    ends = Counter(str(r.get('pipelineRunEndtime'))[:10] for r in recs)
    print('   end-dist:', dict(sorted(ends.items())))

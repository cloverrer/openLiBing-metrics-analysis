"""第 7b 步 社区 Nightly 采集（openGauss / openEuler / UBS Core）。

为什么排在第 7 步之后：社区流水线产出的是与 openLiBing 侧**同一套归档 schema**
（pipeline.json + pipeline.evidence.json + 当日 _day.json 条目 + _products.json），
而 _day.json / _products.json / _index.json 都是第 7 步整体重建的产物 —— 社区数据必须
在其之后并入，才能保证「第 7 步重跑不会把社区条目冲掉」，且第 9 步出页时两份数据已齐。

取数实现与口径复用 tools/collect_community_nightly.py（不另写一份）：
  openGauss / openEuler  走 Jenkins 站点（版本可用度 = 成功天数÷有执行天数，编译成功率 = 成功次数÷构建次数）
  UBS Core               走 openLiBing 平台（N2 执行记录 + T4/T6/T5 任务取证）
  逐日版本可用度一律走 lib/va_caliber.py 的统一口径（开始日进分母、成功只记结束日）。

区间与全流程一致：run_pipeline 传入的 RCA_START / RCA_END（未传则 config.date_range，
再缺省取「前一个工作日」），与第 1~7 步取数区间完全相同。

产物：out/archive/<年>/<年-月>/<日>/<社区名>/<流水线名>/…，并并入当日 _day.json、
      out/archive/_products.json、out/archive/_index.json。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from lib.cdp_exec import load_config, normalize_date_range  # noqa: E402
import collect_community_nightly as community  # noqa: E402


def main():
    cfg = load_config()
    start, end = normalize_date_range(cfg)
    print("== 第 7b 步 社区 Nightly 采集（openGauss / openEuler / UBS Core）: %s ~ %s"
          % (start, end))
    day_entries, prod_acc = community.run(start, end)
    print("== 第 7b 步完成：更新 %d 个归档日 / %d 个社区组件（%s）"
          % (len(day_entries), len(prod_acc),
             "、".join(sorted(prod_acc)) or "无"))


if __name__ == "__main__":
    main()

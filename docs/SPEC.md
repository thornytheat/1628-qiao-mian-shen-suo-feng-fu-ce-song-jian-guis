# 桥面伸缩缝复测送检业务规格

## 输入与时点

`day` 从演练档案起始日计数，`arrived` 表示入账日，`clock` 以 15 分钟为一格。测量在发生日之后一日内到达才可进入时点样本，超过窗口的补录留在隔离证据。跨日结果通过 `available` 回读，训练使用冻结日前已确认的最后一份回执。

业务组包括快速路引桥、公交支廊、互通匝道、沿江跨线。同一 `case_id` 的同版本异值记录整笔隔离，重复记录只计一笔。

## 校尺差与时点

批次可附 `ruler_calibrations`（也兼容 `ruler_corrections`、`calibrations` 等同义列表名）。校尺记录至少包含尺编号、带符号校尺差 `correction_mm` 和确认日 `confirmed_day`；可用 `day`、`start_day/end_day` 或 `period` 标明有效时段。测量单以顶层 `ruler_id` 指明当天使用的尺。

净宽换算统一为：

```text
corrected_reading = raw_reading + correction_mm
```

训练冻结、回放参考日和当班快照分别只使用各自截止日前已确认且在测量当天有效的校尺差。截止后确认的记录对该次重算不可见，下一快照日才进入换算。缺少有效校尺差，或同一把尺在同一有效时段存在不同校尺差时，该单以 `RULER_CORRECTION_MISSING` / `RULER_CORRECTION_CONFLICT` 转人工（证据中同时给出 `RULER_CALIBRATION_*` 别名），不进入候选、不占用复测车额度。未携带 `ruler_id` 的旧单保持原流程。逐单结果和送检联 schedule ticket 附 `calibration_basis`（同份依据也以 `ruler_basis`、`校尺依据` 暴露）。

| 信号源 | 含义 | 接受范围 |
| --- | --- | --- |
| `reading` | 伸缩缝净宽 mm | 3 至 80 |
| `span_temp` | 梁底温度 ℃ | -10 至 47 |
| `design` | 设计参考净宽 mm | 24 至 60 |
| `axles` | 采样小时重轴车数 | 0 至 220 |
| `history` | 已记录伸缩差 mm | 0 至 14 |
| `lane_min` | 车道许可窗口 min | 0 至 100 |
| `occupied` | 车道是否已有占用 | 0 至 1 |

## 计算与裁决

使用Theil–Sen 稳健斜率，目标单位为 mm。数据冻结以 `as_of` 为锚点，选择截至第 `as_of-64` 日的历史，随后依次保留校准段、回放段和待裁决段。
训练样本的中位数与 MAD 用于共享缩放。组内样本数足够时，用组内中位数补齐非关键测量。以下特征按同一名次供回放和推理。

| 派生特征 | 计算 |
| --- | --- |
| `gap_deviation` | `abs(reading - (design + (span_temp - 19)*.58)) / 30` |
| `thermal_band` | `(span_temp+10)/57` |
| `load_axles` | `axles/220` |
| `prior_gap` | `history/14` |

关键测量不全、回放门限失败或组分布出现明显变化时进入人工复核。业务锁包括车道已占用或许可窗口过短。最终分派受复测车辆时段总额和组内上限约束，使用额度守恒回读工作单。

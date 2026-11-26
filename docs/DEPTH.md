# 模块与边界验证

所属领域 AI/ML，子方向 传统ML。

## 功能模块

| 序号 | 模块 | 职责 | 实现 | 测试 |
| --- | --- | --- | --- | --- |
| M1 | joint_register | 单据接入与时点裁决 | `src/jointfolio/joint_register/service.py` | `tests/test_joint_register.py` |
| M2 | thermal_alignment | 业务特征与时点档案 | `src/jointfolio/thermal_alignment/service.py` | `tests/test_thermal_alignment.py` |
| M3 | joint_sen_fit | 训练、估计与基线 | `src/jointfolio/joint_sen_fit/service.py` | `tests/test_joint_sen_fit.py` |
| M4 | bridge_residuals | 时间回放与核验 | `src/jointfolio/bridge_residuals/service.py` | `tests/test_bridge_residuals.py` |
| M5 | surface_regimes | 群组偏移与可信分派 | `src/jointfolio/surface_regimes/service.py` | `tests/test_surface_regimes.py` |
| M6 | lane_booking | 业务锁与资源分派 | `src/jointfolio/lane_booking/service.py` | `tests/test_lane_booking.py` |
| M7 | inspector_sheet | 逐单证据与资源守恒 | `src/jointfolio/inspector_sheet/service.py` | `tests/test_inspector_sheet.py` |
| M8 | measurement_register | 版本登记与追溯 | `src/jointfolio/measurement_register/service.py` | `tests/test_measurement_register.py` |

## 易错边界

| 用例 | 业务后果 | 处理位置 | 验证位置 |
| --- | --- | --- | --- |
| TRAP-14 | 同版本异值隔离，较旧修订不能复活 | `src/jointfolio/joint_register/service.py` | `tests/test_joint_register.py::test_conflicting_revision_is_quarantined` |
| TRAP-19 | 业务锁优先，未获准的单据不消耗资源 | `src/jointfolio/lane_booking/service.py` | `tests/test_lane_booking.py::test_prohibited_entries_never_spend` |
| TRAP-26 | 使用过期版本登记被拒，保留前次结果 | `src/jointfolio/measurement_register/service.py` | `tests/test_measurement_register.py::test_stale_generation_keeps_prior` |
| TRAP-32 | 零方差业务特征仍有有界尺度 | `src/jointfolio/thermal_alignment/service.py` | `tests/test_thermal_alignment.py::test_zero_variance_uses_unit_scale` |
| TRAP-42 | 训练冻结后到达的单据或回执不会回填 | `src/jointfolio/thermal_alignment/service.py` | `tests/test_thermal_alignment.py::test_future_and_late_measurements_do_not_fit` |
| TRAP-43 | 训练与独立回放的单据按时段隔离 | `src/jointfolio/bridge_residuals/service.py` | `tests/test_bridge_residuals.py::test_holdout_separates_ordered_periods` |
| TRAP-44 | 稀疏或常量参考出现越界值时拦住自动分派 | `src/jointfolio/surface_regimes/service.py` | `tests/test_surface_regimes.py::test_constant_distribution_detects_outside` |
| TRAP-53 | 同批重排仍得到相同证据和决策 | `src/jointfolio/inspector_sheet/service.py` | `tests/test_inspector_sheet.py::test_report_is_permutation_invariant` |
| TRAP-54 | 单笔推理与合并调用的结果一致 | `src/jointfolio/joint_sen_fit/service.py` | `tests/test_joint_sen_fit.py::test_score_is_batch_invariant` |

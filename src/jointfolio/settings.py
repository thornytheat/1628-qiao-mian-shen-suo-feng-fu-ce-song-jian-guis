PROJECT_NAME = "桥面伸缩缝复测送检"
ROLE = "桥面养护巡查组长"
MODEL_LABEL = "Theil–Sen 稳健斜率"
TARGET = "continuous"
UNIT = "mm"
ACTION_LABEL = "生成伸缩缝送检联"
RESERVE_LABEL = "复测车辆时段"
DEFAULT_DAY = 144
DEFAULT_BUDGET = 12
REPORT_LAG = 1
GROUPS = ("快速路引桥", "公交支廊", "互通匝道", "沿江跨线")
SIGNAL_NAMES = ("gap_deviation", "thermal_band", "load_axles", "prior_gap")
WATCH_FEATURE = "gap_deviation"
METRIC_LABEL = "平均绝对误差"
FIELD_LABELS = {
    "reading": "伸缩缝净宽 mm",
    "span_temp": "梁底温度 ℃",
    "design": "设计参考净宽 mm",
    "axles": "采样小时重轴车数",
    "history": "已记录伸缩差 mm",
    "lane_min": "车道许可窗口 min",
    "occupied": "车道是否已有占用",
}
FIELD_BOUNDS = {
    "reading": (3, 80),
    "span_temp": (-10, 47),
    "design": (24, 60),
    "axles": (0, 220),
    "history": (0, 14),
    "lane_min": (0, 100),
    "occupied": (0, 1),
}
CRITICAL_FIELDS = frozenset(("lane_min", "occupied", "reading"))

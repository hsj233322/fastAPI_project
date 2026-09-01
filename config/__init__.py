# 语义搜索阈值  services/tool_functions.py中用到
SCORE_THRESHOLD = 0.5
# 指定地点过滤时的阈值（地域是用户明确的硬性条件，语义分只用于排序，放宽避免误杀）
LOCATION_FILTER_THRESHOLD = 0.7
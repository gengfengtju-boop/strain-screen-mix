# Scripts

本目录按功能模块组织后续 Python/R 脚本。当前阶段只固定模块边界、输入和输出，不实现具体算法。

## 模块约定

每个模块后续建议包含：

- `README.md`：模块说明
- `run.*`：模块主入口
- `utils.*`：局部工具函数
- `tests/`：轻量测试数据和验证脚本

## 推荐执行顺序

1. `data_download`
2. `metadata_cleaning`
3. `feature_engineering`
4. `obesity_model`
5. `responder_model`
6. `strain_annotation`
7. `combination_recommendation`
8. `visualization`
9. `report_generation`


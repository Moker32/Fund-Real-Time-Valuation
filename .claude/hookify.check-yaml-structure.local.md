---
name: check-yaml-structure
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: (config\.yaml|fonds\.yaml|commodities\.yaml)$
---

⚠️ **YAML 配置文件修改！**

请确保配置文件结构正确：

**config.yaml 格式：**
```yaml
app:
  theme: "dark"  # 或 "light"
  refresh_interval: 30  # 秒

sources:
  fund:
    - name: "天天基金"
      enabled: true
      priority: 1
```

**funds.yaml 格式：**
```yaml
funds:
  - code: "161039"
    name: "中小板指"
    holdings:
      - shares: 1000
        cost: 1.5000
```

**commodities.yaml 格式：**
```yaml
commodities:
  - code: "SP"
    name: "S&P 500"
  - code: "GC"
    name: "黄金"
```

**提示：** 参考 `examples/` 目录下的示例文件。

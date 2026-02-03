---
name: protect-config-directory
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: ^(?!\.gitignore).*$
  - field: new_text
    operator: regex_match
    pattern: (os\.getenv\(['\"]HOME['\"]\)|Path\.home\(\)|~\/|\\$HOME)
---

⚠️ **硬编码路径检测！**

应用配置应使用 `ConfigManager` 获取路径，而非硬编码。

**检测到的模式：**
- `os.getenv('HOME')`
- `Path.home()`
- `~/` 或 `$HOME`

**正确做法：**
使用 `ConfigManager` 获取配置目录：

```python
from src.config.manager import ConfigManager

config = ConfigManager()
config_dir = config.config_dir  # ~/.fund-tui/
funds_file = config.funds_file  # ~/.fund-tui/funds.yaml
```

**配置文件：**
- 主配置：`~/.fund-tui/config.yaml`
- 基金配置：`~/.fund-tui/funds.yaml`
- 商品配置：`~/.fund-tui/commodities.yaml`

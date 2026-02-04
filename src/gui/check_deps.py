# -*- coding: UTF-8 -*-
"""依赖检查模块

启动时检查必要的依赖是否已安装。
"""

import sys
from typing import List, Tuple


# 必需依赖列表
REQUIRED_PACKAGES = [
    ("flet", "0.28.3"),
    ("httpx", "0.24.0"),
    ("pyyaml", "6.0"),
    ("beautifulsoup4", "4.12.0"),
    ("python-dateutil", "2.8.2"),
    ("matplotlib", "3.7.0"),
    ("akshare", "1.10.0"),
    ("yfinance", "0.2.0"),
]


def check_package_version(package_name: str) -> Tuple[bool, str]:
    """
    检查包是否已安装及其版本

    Returns:
        (是否已安装, 版本号或错误信息)
    """
    try:
        import importlib.metadata

        try:
            version = importlib.metadata.version(package_name)
            return True, version
        except importlib.metadata.PackageNotFoundError:
            return False, "未安装"
    except Exception as e:
        return False, f"检查失败: {e}"


def check_required_packages() -> Tuple[bool, List[str]]:
    """
    检查必需依赖是否已安装

    Returns:
        (是否全部通过, 未通过列表)
    """
    missing = []

    for package, min_version in REQUIRED_PACKAGES:
        installed, info = check_package_version(package)

        if not installed:
            missing.append(f"  - {package} (需要版本 >= {min_version})")
        else:
            # 可以添加版本检查逻辑
            print(f"✓ {package}: {info}")

    return len(missing) == 0, missing


def check_optional_packages() -> Tuple[bool, List[str]]:
    """
    检查可选依赖状态

    Returns:
        (是否全部通过, 未通过列表)
    """
    optional = []
    optional_packages = [
        "pandas",
        "numpy",
        "lxml",
    ]

    for package in optional_packages:
        installed, info = check_package_version(package)
        if installed:
            print(f"✓ {package}: {info}")
        else:
            optional.append(f"  - {package} (可选)")

    return len(optional) == 0, optional


def check_environment() -> bool:
    """
    执行完整的依赖和环境检查

    Returns:
        是否所有必需依赖都通过
    """
    print("=" * 50)
    print("依赖检查")
    print("=" * 50)
    print()

    print("检查必需依赖:")
    print("-" * 50)
    required_ok, missing = check_required_packages()
    print()

    if missing:
        print("缺少必需依赖:")
        for m in missing:
            print(m)
        print()
        print("请安装缺少的依赖:")
        print(f"  uv pip install -r requirements.txt")
        print()

    print("检查可选依赖:")
    print("-" * 50)
    optional_ok, optional = check_optional_packages()
    if optional:
        print("以下可选依赖未安装:")
        for o in optional:
            print(o)
        print()
    print()

    print("=" * 50)
    if required_ok:
        print("✓ 所有必需依赖已安装")
    else:
        print("✗ 缺少必需依赖，请先安装")
    print("=" * 50)
    print()

    return required_ok


def verify_imports() -> bool:
    """
    验证核心模块的导入

    Returns:
        是否所有导入都成功
    """
    print("验证核心模块导入:")
    print("-" * 50)

    modules_to_check = [
        ("flet", "GUI框架"),
        ("httpx", "HTTP客户端"),
        ("yaml", "YAML解析"),
        ("matplotlib", "图表绘制"),
    ]

    all_ok = True
    for module, desc in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module}: OK ({desc})")
        except ImportError as e:
            # 尝试备用导入
            if module == "yaml":
                try:
                    import yaml

                    print(f"✓ {module}: OK ({desc})")
                    continue
                except ImportError:
                    pass
            print(f"✗ {module}: FAIL ({desc}) - {e}")
            all_ok = False

    print("-" * 50)
    print()

    return all_ok


if __name__ == "__main__":
    # 单独运行时执行检查
    env_ok = check_environment()
    import_ok = verify_imports()

    if env_ok and import_ok:
        print("✓ 所有检查通过，可以启动应用")
        sys.exit(0)
    else:
        print("✗ 检查未通过，请先解决上述问题")
        sys.exit(1)

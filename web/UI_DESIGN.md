# FundVue UI 设计文档

## 概述

FundVue 采用极简金融风暗黑主题设计，强调数据可读性和交互体验。

## 色彩系统

### 背景色
| 变量 | 十六进制 | 用途 |
|------|----------|------|
| `--color-bg-primary` | #0D0D0D | 主背景，全局使用 |
| `--color-bg-secondary` | #141414 | 次级背景，侧边栏、对话框 |
| `--color-bg-tertiary` | #1A1A1A | 第三级背景 |
| `--color-bg-card` | #161616 | 卡片背景 |
| `--color-bg-card-hover` | #1C1C1C | 卡片悬停状态 |

### 文字色
| 变量 | 十六进制 | 对比度 | 用途 |
|------|----------|--------|------|
| `--color-text-primary` | #FFFFFF | 21:1 | 主文字，重要信息 |
| `--color-text-secondary` | #A0A0A0 | 4.5:1✓ | 次级文字，辅助信息 |
| `--color-text-tertiary` | #666666 | - | 禁用状态、占位符 |

### 功能色
| 变量 | 十六进制 | 用途 |
|------|----------|------|
| `--color-rise` | #FF6B6B | 上涨、正向 |
| `--color-rise-bg` | rgba(255, 107, 107, 0.1) | 涨色背景 |
| `--color-rise-alpha` | rgba(255, 107, 107, 0.15) | 涨色悬浮背景 |
| `--color-fall` | #4ADE80 | 下跌、负向 |
| `--color-fall-bg` | rgba(74, 222, 128, 0.1) | 跌色背景 |
| `--color-fall-alpha` | rgba(74, 222, 128, 0.15) | 跌色悬浮背景 |
| `--color-neutral` | #71717A | 中性、无变化 |

### 边框与分割线
| 变量 | 十六进制 | 用途 |
|------|----------|------|
| `--color-border` | #27272A | 默认边框 |
| `--color-border-light` | #2D2D30 | 浅色边框 |
| `--color-divider` | #27272A | 分割线 |

### 阴影
| 变量 | 用途 |
|------|------|
| `--shadow-sm` | 小阴影，卡片悬浮 |
| `--shadow-md` | 中阴影，对话框 |
| `--shadow-lg` | 大阴影，重要提示 |
| `--shadow-glow-rise` | 涨色发光效果 |
| `--shadow-glow-fall` | 跌色发光效果 |

## 间距系统

基于 8px 网格系统：

| 变量 | 值 | 用途 |
|------|-----|------|
| `--spacing-xs` | 4px | 图标与文字间距 |
| `--spacing-sm` | 8px | 组件内部间距 |
| `--spacing-md` | 16px | 组件之间间距 |
| `--spacing-lg` | 24px | 区块之间间距 |
| `--spacing-xl` | 32px | 页面区块间距 |
| `--spacing-2xl` | 48px | 大区块分隔 |

## 字体系统

### 字体族
```scss
--font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
--font-mono: 'SF Mono', 'Consolas', 'Monaco', monospace;
```

### 字号
| 变量 | 值 | 用途 |
|------|-----|------|
| `--font-size-xs` | 11px | 标签、徽章 |
| `--font-size-sm` | 12px | 辅助信息 |
| `--font-size-md` | 14px | 正文 |
| `--font-size-lg` | 16px | 小标题 |
| `--font-size-xl` | 20px | 页面标题 |
| `--font-size-2xl` | 24px | 大标题 |
| `--font-size-3xl` | 32px | Hero 文字 |

### 字重
| 变量 | 值 | 用途 |
|------|-----|------|
| `--font-weight-regular` | 400 | 正文 |
| `--font-weight-medium` | 500 | 按钮文字 |
| `--font-weight-semibold` | 600 | 标题 |
| `--font-weight-bold` | 700 | 强调 |

## 圆角系统

| 变量 | 值 | 用途 |
|------|-----|------|
| `--radius-sm` | 6px | 按钮、输入框 |
| `--radius-md` | 10px | 卡片 |
| `--radius-lg` | 14px | 大卡片、对话框 |
| `--radius-xl` | 20px | 特殊元素 |
| `--radius-full` | 9999px | 圆形、胶囊按钮 |

**嵌套圆角规则**: 子元素圆角 ≤ 父元素圆角 - 父元素内边距

## 动画系统

### 过渡时长
```scss
--transition-fast: 150ms ease;   // 按钮悬停、状态切换
--transition-normal: 250ms ease; // 卡片出现、消失
--transition-slow: 400ms ease;   // 页面切换、显著变化
```

### 动画关键帧
```scss
@keyframes fadeIn      { opacity: 0 → 1; }
@keyframes slideUp    { opacity: 0 + translateY(20px) → 1 + translateY(0); }
@keyframes slideInLeft { opacity: 0 + translateX(-20px) → 1 + translateX(0); }
@keyframes pulse      { opacity: 1 → 0.5 → 1; }
@keyframes shimmer    { background-position: -200% → 200%; }
@keyframes numberUpdate { opacity: 0.5 → 1; }
```

### 动画类
- `.animate-fade-in` - 淡入
- `.animate-slide-up` - 上滑进入
- `.animate-slide-left` - 左滑进入

### 动画偏好支持
```scss
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## 组件规范

### 按钮
- **最小点击区域**: 44x44px (移动端)
- **内边距**: 8px 16px
- **圆角**: 6-10px
- **状态**: default, hover, active, focus-visible, disabled

### 卡片
- **背景**: var(--color-bg-card)
- **圆角**: 10-14px
- **内边距**: 16px
- **阴影**: var(--shadow-sm)，悬停时 var(--shadow-md)
- **边框**: 1px solid var(--color-border)

### 输入框
- **高度**: 40px
- **圆角**: 6px
- **边框**: 1px solid var(--color-border)
- **聚焦**: 边框变为主色调

### 对话框
- **背景**: var(--color-bg-secondary)
- **圆角**: 14px
- **最大宽度**: 400px
- **遮罩**: rgba(0, 0, 0, 0.7)

## 可访问性规范

### 键盘导航
- 所有交互元素可通过 Tab 键聚焦
- `:focus-visible` 显示 2px 轮廓线
- 焦点顺序符合视觉逻辑

### 焦点样式
```scss
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

### ARIA 属性
- 按钮必须包含 `aria-label` 或可见文字
- 图标按钮必须包含 `aria-hidden="true"` (装饰性) 或 `aria-label` (功能性)
- 对话框必须包含 `role="dialog"`, `aria-modal="true"`, `aria-labelledby`

### 颜色对比度
- 文字与背景对比度 ≥ 4.5:1 (WCAG AA)
- UI 元素与背景对比度 ≥ 3:1

## 响应式断点

| 断点 | 宽度 | 布局 |
|------|------|------|
| mobile | < 640px | 单列，隐藏侧边栏 |
| tablet | 640px - 1024px | 侧边栏可折叠 |
| desktop | > 1024px | 完整布局 |

## 文件结构

```
web/src/
├── styles/
│   ├── global.scss      # 全局样式、设计系统变量
│   └── main.scss        # 入口文件
├── components/
│   ├── FundCard.vue     # 基金卡片
│   ├── CommodityCard.vue # 商品卡片
│   ├── ConfirmDialog.vue # 确认对话框
│   ├── AddFundDialog.vue # 添加基金对话框
│   └── MarketOverview.vue # 市场概览
├── layouts/
│   └── MainLayout.vue   # 主布局
└── views/
    ├── HomeView.vue     # 首页
    ├── FundsView.vue    # 基金页面
    └── CommoditiesView.vue # 商品页面
```

## 开发指南

### 添加新组件
1. 使用 `<script setup lang="ts">`
2. 使用 CSS 变量而非硬编码颜色
3. 添加 ARIA 属性
4. 处理所有交互状态 (hover, focus, disabled)
5. 添加 `prefers-reduced-motion` 支持

### 添加新颜色
1. 在 `global.scss` 的 `:root` 中定义变量
2. 遵循现有命名约定 (--color-{用途}-{状态})
3. 确保对比度符合 WCAG AA

### 调试样式
```bash
# 运行 lint 检查
cd web && pnpm run lint

# 运行类型检查
cd web && pnpm run typecheck
```

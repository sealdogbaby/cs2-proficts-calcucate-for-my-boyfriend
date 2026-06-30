# CS2 Steam × BUFF 价差雷达 V1

## 它能做什么

1. 从 CSQAQ API 建立一份默认顺序的 50 件测试饰品目录。
2. 自动过滤：多普勒、伽马多普勒、淬火、渐变、黑珍珠、红宝石、蓝宝石、翡翠等关键词命中的饰品。
3. 每次扫描每件饰品的 Steam 求购价、Steam 在售价、BUFF 求购价、BUFF 在售价。
4. 计算：

```text
Steam 实际现金成本 = (Steam 最高求购价 + 0.10) × 0.65
BUFF 预估到账金额 = BUFF 最低在售价 × 0.985
净利润金额 = BUFF 预估到账金额 - Steam 实际现金成本
净利润率 = 净利润金额 ÷ Steam 实际现金成本
```

5. 只展示净利润率严格大于 10% 的饰品。
6. 生成 Steam 与 BUFF 可点击链接。
7. 生成本地网页与 `data\latest_results.csv`。

## 不做什么

- 不登录 Steam 或 BUFF。
- 不自动求购、下单、上架、改价。
- 不保存 Steam/BUFF Cookie 或账号密码。
- 不判断贴纸、浮点、模板、成交量、新饰品或最终是否值得下单。

## 第一次使用顺序

### 第 1 步：准备 Python

安装 Python 3.10 或更高版本。安装界面一定勾选 `Add Python to PATH`。

### 第 2 步：运行安装脚本

双击：

```text
setup_windows.bat
```

它会创建 `.venv` 并安装依赖。

### 第 3 步：填写 Token 与绑定 IP

1. 打开 `.env`。
2. 把这一行：

```text
CSQAQ_API_TOKEN=PASTE_YOUR_CSQAQ_API_TOKEN_HERE
```

替换为你在 CSQAQ 官网复制的真实 ApiToken。
3. 在 CSQAQ 官网完成该 Token 的“自动获取”或“手动绑定白名单 IP”。
4. 保存 `.env`。

不要把 `.env` 发给任何人，因为里面有 Token。

### 第 4 步：建立测试目录

双击：

```text
init_catalog.bat
```

它会按 CSQAQ 默认目录顺序，过滤特殊款式后，保存前 50 件测试饰品到本地 SQLite 数据库。

### 第 5 步：首次扫描

双击：

```text
run_once.bat
```

约 50 件 × 1.05 秒/请求，预计约 1 分钟左右。完成后会看到日志，并生成：

```text
data\latest_results.csv
data\radar.sqlite
logs\runtime.log
```

### 第 6 步：打开网页

双击：

```text
start_dashboard.bat
```

浏览器会自动打开：

```text
http://127.0.0.1:5000
```

### 第 7 步：持续扫描（可选）

双击：

```text
start_scanner.bat
```

它会每 15 分钟扫描一次。命令行不要关闭；按 `Ctrl+C` 可以安全停止。

## 重新建立测试目录

如果你修改了 `.env` 里的 `INITIAL_SAMPLE_SIZE` 或过滤关键词，双击：

```text
rebuild_catalog.bat
```

它会清空旧测试目录、旧扫描结果，然后重新建立目录。这个操作需要你在弹窗中确认。

## 重要文件说明

| 文件 | 用途 |
|---|---|
| `.env` | API Token 和可调参数，保密 |
| `init_catalog.bat` | 首次建立测试饰品目录 |
| `run_once.bat` | 单次扫描、排错用 |
| `start_scanner.bat` | 每 15 分钟持续扫描 |
| `start_dashboard.bat` | 启动本地网页 |
| `data\latest_results.csv` | 仅包含净利润率大于 10% 的结果，Excel 可打开 |
| `logs\runtime.log` | 运行日志 |

## 常见报错

### 400 / 401：Token 验证失败

检查：

1. `.env` 中 Token 是否完整；
2. Token 后面没有空格；
3. 是否在 CSQAQ 官网绑定了当前公网 IP；
4. 当前网络是否换过宽带、热点或 VPN。

### 429 / 503：请求频率过快

不要把 `REQUEST_INTERVAL_SECONDS` 改到 1.0 以下。当前默认 1.05 秒，符合 CSQAQ 单 IP 每秒最多 1 次的公开限制。

### 网页显示没有结果

这不一定是故障。可能是最近一轮没有净利润率严格大于 10% 的饰品。先检查 `logs\runtime.log` 确认扫描是否成功。

## 数据免责声明

本工具仅按 CSQAQ 返回的公开数据执行公式计算。最终价格、链接指向、具体饰品属性、是否可成交、是否可套利和实际盈亏，均需要人工确认。

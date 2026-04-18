# 🔧 Vibe-PCB Orchestrator

**Hardware Design as Code — Compile, Check, Fabricate**

用 Python 寫電路、自動產生 PCB、靜態分析、3D 互動預覽——從程式碼到實體電路板的一條龍自動化框架。

> 🌐 **[線上 Demo (GitHub Pages)](https://yosi067.github.io/Vibe-PCB/)** — 即時預覽 PCB 2D 佈局、電路原理圖、3D 互動模型

---

## 目錄

- [專案架構](#專案架構)
- [自動化管線](#自動化管線)
- [模組總覽](#模組總覽)
- [核心功能](#核心功能)
- [快速開始](#快速開始)
- [詳細規格文件](#詳細規格文件)
- [擴展新電路](#擴展新電路)
- [License](#license)

---

## 專案架構

```
Vibe-PCB/
├── main.py                      # 主調度程式 — 雙模組管線
├── circuits/
│   ├── fan_controller.py        # 🌀 模組一：EMC2103 風扇控制器
│   └── power_monitor.py         # ⚡ 模組二：INA226 功耗監測
├── lib/
│   ├── analyzer.py              # 靜態分析引擎 (電壓守衛 + BOM + P=I²R + I2C 衝突)
│   ├── pcb_generator.py         # 風扇控制器 PCB 佈局產生器
│   ├── pcb_generator_power.py   # 功耗監測 PCB 佈局產生器
│   ├── sch_generator.py         # 風扇控制器原理圖產生器
│   ├── sch_generator_power.py   # 功耗監測原理圖產生器
│   ├── exporter.py              # KiCad CLI / Gerber / STEP 匯出
│   └── web_server.py            # 本地預覽伺服器
├── docs/
│   ├── module-fan-controller.md # 🌀 風扇控制器詳細規格（中文）
│   └── module-power-monitor.md  # ⚡ 功耗監測詳細規格（中文）
├── output/                      # 自動產出
│   ├── index.html               # 互動式預覽頁面 (KiCanvas + Three.js)
│   ├── fan_controller.kicad_pcb # 風扇控制器 PCB
│   ├── fan_controller.kicad_sch # 風扇控制器原理圖
│   ├── fan_controller.net       # 風扇控制器 Netlist
│   ├── power_monitor.kicad_pcb  # 功耗監測 PCB
│   ├── power_monitor.kicad_sch  # 功耗監測原理圖
│   └── power_monitor.net        # 功耗監測 Netlist
└── .github/workflows/deploy.yml # GitHub Pages 自動部署
```

---

## 自動化管線

```
  Step 1            Step 2           Step 3            Step 4            Step 5
[SKiDL Code] → [Netlist .net] → [Static Analysis] → [PCB + SCH] → [Web Preview]
  Python 電路       編譯產出        電壓/BOM/功耗       佈局 & 原理圖     KiCanvas +
  定義               SKiDL          P=I²R / I2C         自動生成         Three.js 3D
                                    衝突偵測
```

兩個模組 **同時平行** 執行整條管線，最終合併到同一個預覽頁面。

---

## 模組總覽

### 🌀 模組一：AI Server 風扇控制器

| 項目 | 規格 |
|------|------|
| 核心晶片 | Microchip EMC2103 (QFN-20, 4×4mm) |
| I2C 地址 | 0x2E (ADDR_SEL=GND) |
| 電壓域 | 3.3V (邏輯) + 12V (風扇供電) |
| PCB 尺寸 | 40mm × 30mm, 2 層 |
| 主要功能 | PWM 風扇轉速控制、Tach 轉速回饋、SMBALERT# 過溫通知 |
| BOM 成本 | ≈ $3.22 |

### ⚡ 模組二：Smart Power Monitor

| 項目 | 規格 |
|------|------|
| 核心晶片 | Texas Instruments INA226 (MSOP-10, 3×3mm) |
| I2C 地址 | 0x41 (A0=VCC, A1=GND) |
| 分流電阻 | 0.002Ω (2mΩ), 2512 封裝, 額定 2W |
| 設計電流 | 最大 30A (P=1.8W < 2W ✔) |
| PCB 尺寸 | 35mm × 25mm, 2 層 |
| 主要功能 | 12V 電壓/電流/功率即時監測、ALERT 過流告警 + LED |
| BOM 成本 | ≈ $5.22 |

---

## 核心功能

### ⚡ Voltage Guard — 電壓守衛
掃描 Netlist 中每個腳位的電壓域，自動偵測：
- 12V 訊號直連 3.3V IC → **ERROR**
- 跨電壓域零件缺少 Level Shift → **WARNING**

### 🔥 P=I²R 功耗檢查
自動計算每個電阻在最大電流下的功耗，比對封裝額定瓦數：
- Rs1 (0.002Ω, 2512): 1.8W < 2W → **PASS**
- 如果有人用 0402 封裝放 2mΩ → **FAIL** (超過 0.0625W)

### 🔗 I2C 位址衝突偵測
掃描所有模組的 I2C 設備，確認：
- Fan Controller: 0x2E ✔
- Power Monitor: 0x41 ✔
- 無衝突 → **PASS**

### 📦 BOM — 零件合規 & 成本估算
- 自動驗證封裝是否在已知庫中
- 根據零件類型估算 BOM 成本

### 🌐 互動式 Web 預覽
- **KiCanvas** 渲染 PCB 2D 佈局 + 電路原理圖（支援方向鍵平移、滾輪縮放）
- **Three.js** 3D 互動模型：
  - 🌀 風扇旋轉動畫 (PWM 控制轉速)
  - 🔵🟢🟠 訊號流粒子 (I2C / PWM / 12V)
  - 🔴 熱效應光暈 (Thermal 模擬)
  - 📊 即時數據顯示
- **模組切換器**：一鍵切換查看兩個模組的所有內容

---

## 快速開始

### 1. 環境準備

```bash
# Python 3.10+
pip install skidl
```

> **不需要安裝 KiCad！** 所有 .kicad_pcb / .kicad_sch 檔案由 Python 純文字產生。

### 2. 執行完整管線

```bash
python main.py
```

這會依序執行：編譯兩個電路 → 靜態分析 → 產生 PCB & 原理圖 → 啟動本地預覽伺服器

### 3. 常用選項

```bash
python main.py --analyze-only   # 僅編譯 + 靜態檢查，不啟動伺服器
python main.py --strict          # 嚴格模式（任何錯誤即中止）
python main.py --no-preview      # 跳過 Web 預覽伺服器
```

### 4. 線上預覽

無需本地執行，直接訪問 GitHub Pages：

👉 **https://yosi067.github.io/Vibe-PCB/**

---

## 詳細規格文件

> 為初學者撰寫的中文技術文件，涵蓋每個零件的選型理由、電路原理、PCB 設計要點。  
> 搭配線上 Demo 逐一對照，幫助你從零開始理解 PCB 設計。

| 文件 | 說明 |
|------|------|
| [🌀 風扇控制器詳細規格](docs/module-fan-controller.md) | EMC2103 電路結構、QFN-20 封裝、I2C 通訊、PWM 控制、去耦電容設計、3D 模型說明 |
| [⚡ 功耗監測詳細規格](docs/module-power-monitor.md) | INA226 電流量測原理 ($V=IR$)、分流電阻 P=I²R 選型計算、Kelvin 連接、Alert LED、大電流 PCB 走線 |

---

## 擴展新電路

在 `circuits/` 下新增 `.py` 檔案，參考現有模組的模式：

```python
# circuits/your_module.py
from skidl import Part, Pin, Net, POWER, TEMPLATE, SKIDL, generate_netlist, reset

def gen_your_module():
    reset()
    # 定義零件模板、網路、連接...
    generate_netlist(file_="output/your_module.net")
    return {"nets": {...}, "parts": {...}}
```

然後在 `main.py` 中加入新模組的編譯、分析、匯出步驟即可。

---

## License

MIT

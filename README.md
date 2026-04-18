# 🔧 Vibe-PCB Orchestrator

**Hardware Design as Code — Compile, Check, Fabricate**

將「硬體設計」視為「程式編譯」，從 Python 代碼輸入到 3D PCB 產出，一條龍自動化。

## 架構

```
Vibe-PCB/
├── main.py                  # 主調度程式 (Orchestrator)
├── lib/
│   ├── analyzer.py          # 電壓守衛 + BOM 合規性檢查
│   ├── exporter.py          # KiCad CLI / Freerouting 自動佈線
│   └── web_server.py        # KiCanvas 本地預覽伺服器
├── circuits/
│   └── fan_controller.py    # AI Server 風扇控制模組 (SKiDL)
└── output/                  # 產出：Netlist, PCB, STEP, Gerber
    └── index.html           # KiCanvas 嵌入式預覽頁面
```

## 自動化管線

```
[SKiDL Python Code]  →  [Netlist]  →  [Risk Report]  →  [PCB + STEP + Gerber]  →  [Web Preview]
    Step 1                Step 2          Step 3              Step 4
   編譯電路             靜態掃描       自動佈線+匯出        視覺化預覽
```

## 第一個實作：AI Server 風扇控制模組

- **EMC2103** 溫控晶片 (I2C/SMBus, QFN-20)
- **電壓域**：12V (風扇供電) / 3.3V (邏輯控制)
- **I2C** 連接 BMC，支援 SMBALERT# 過溫中斷
- 4-Pin PWM 風扇接頭 + 完整去耦電容

## 快速開始

### 1. 環境準備

```bash
# Python 3.10+
pip install skidl

# 選裝：KiCad 8.0+ (CLI 匯出), Freerouting (自動佈線)
```

### 2. 執行完整管線

```bash
python main.py
```

### 3. 常用選項

```bash
python main.py --analyze-only   # 僅編譯 + 靜態檢查
python main.py --strict          # 嚴格模式（錯誤即中止）
python main.py --no-preview      # 跳過 Web 預覽伺服器
```

## 核心功能

### ⚡ Voltage Guard (電壓守衛)
掃描 Netlist 中每個腳位的電壓域，自動偵測：
- 12V 訊號直連 3.3V IC → **ERROR**
- 跨電壓域零件缺少 Level Shift → **WARNING**

### 📦 BOM Checker (零件合規)
- 自動驗證所有封裝是否在已知庫中
- 預留 Octopart / KiCost API 庫存查詢介面

### 🌐 KiCanvas Preview
- `output/index.html` 嵌入 KiCanvas Web Component
- 即時渲染 PCB 2D 佈局 + 3D 模型

## 擴展新電路

在 `circuits/` 下建立新的 `.py` 檔案，按照 `fan_controller.py` 的模式撰寫 SKiDL 電路，然後在 `main.py` 中切換 import 即可。

```python
# circuits/gpu_power_monitor.py
from skidl import *

def gen_gpu_power_monitor():
    # 你的電路邏輯...
    generate_netlist(file_="output/gpu_power_monitor.net")
```

## License

MIT

#!/usr/bin/env python3
"""
Vibe-PCB Orchestrator — 主調度程式

將「硬體設計」視為「程式編譯」，從 Python 代碼到 3D PCB 一條龍自動化：

  [SKiDL Python Code]
       ↓  Step 1: 編譯電路邏輯
  [Netlist (.net)]
       ↓  Step 2: AI 靜態掃描
  [Risk Report]
       ↓  Step 3: 自動佈線 + 匯出
  [PCB + STEP + Gerber]
       ↓  Step 4: 視覺化預覽
  [KiCanvas Web Viewer]
"""

import argparse
import io
import sys
import time
from pathlib import Path

# Windows 終端 UTF-8 輸出支援
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 確保專案根目錄在 import path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.analyzer import PCBAnalyzer, I2C_ADDRESSES
from lib.exporter import PCBExporter
from lib.pcb_generator import generate_fan_controller_pcb
from lib.pcb_generator_power import generate_power_monitor_pcb
from lib.sch_generator import generate_fan_controller_schematic
from lib.sch_generator_power import generate_power_monitor_schematic


BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║             🔧 Vibe-PCB Orchestrator v0.1               ║
║   Hardware Design as Code — Compile, Check, Fabricate   ║
║   Modules: Fan Controller + Smart Power Monitor         ║
╚══════════════════════════════════════════════════════════╝
"""

NETLIST_OUTPUT = "output/fan_controller.net"
NETLIST_OUTPUT_PM = "output/power_monitor.net"


def step_compile_circuit() -> bool:
    """Step 1: 從 Python 代碼編譯電路 → Netlist (雙模組)"""
    print("\n📦 [1/4] 正在從 Python 代碼編譯電路邏輯...")
    Path("output").mkdir(parents=True, exist_ok=True)

    success = True

    # ── Module A: Fan Controller ──
    try:
        from circuits.fan_controller import gen_fan_controller
        result = gen_fan_controller()
        net_count = len(result.get("nets", {}))
        part_count = len(result.get("parts", {}))
        print(f"   ✅ Fan Controller 編譯成功：{net_count} 網路 / {part_count} 零件")
        # 註冊 I2C 位址
        I2C_ADDRESSES[0x2E] = "EMC2103 (Fan Controller)"
    except Exception as e:
        print(f"   ❌ Fan Controller 編譯失敗：{e}")
        success = False

    # ── Module B: Power Monitor ──
    try:
        from circuits.power_monitor import gen_power_monitor
        result_pm = gen_power_monitor()
        net_count = len(result_pm.get("nets", {}))
        part_count = len(result_pm.get("parts", {}))
        print(f"   ✅ Power Monitor 編譯成功：{net_count} 網路 / {part_count} 零件")
        # 註冊 I2C 位址
        I2C_ADDRESSES[0x41] = "INA226 (Power Monitor)"
    except Exception as e:
        print(f"   ❌ Power Monitor 編譯失敗：{e}")
        success = False

    return success


def step_analyze(strict: bool = False) -> bool:
    """Step 2: AI 靜態掃描 — 電壓守衛 + BOM 合規 + 功率檢查 + I2C 衝突"""
    print("\n🔍 [2/4] AI 靜態掃描：進行電壓、功率、I2C 合規性檢查...")

    all_passed = True

    for label, netlist in [
        ("Fan Controller", NETLIST_OUTPUT),
        ("Power Monitor", NETLIST_OUTPUT_PM),
    ]:
        print(f"\n   ── {label} ──")
        analyzer = PCBAnalyzer(netlist)
        report = analyzer.run_checks()
        print(report.summary())
        if not report.passed:
            all_passed = False

    if not all_passed:
        print("   🚨 偵測到嚴重錯誤，自動化流程中斷。")
        if strict:
            return False
        print("   ⚠️  使用 --strict 模式可在此步驟中止流程。")

    return True


def step_export() -> bool:
    """Step 3: 生成 PCB / 原理圖佈局與檔案匯出 (雙模組)"""
    print("\n🛤️  [3/4] 正在生成 PCB 佈局與檔案匯出...")

    # ── Module A: Fan Controller ──
    pcb_path = "output/fan_controller.kicad_pcb"
    sch_path = "output/fan_controller.kicad_sch"
    print("   → [Fan Controller] 生成 PCB + 原理圖...")
    try:
        generate_fan_controller_pcb(pcb_path)
        print(f"   ✅  PCB：{pcb_path}")
    except Exception as e:
        print(f"   ❌  PCB 生成失敗：{e}")

    try:
        generate_fan_controller_schematic(sch_path)
        print(f"   ✅  原理圖：{sch_path}")
    except Exception as e:
        print(f"   ❌  原理圖生成失敗：{e}")

    # ── Module B: Power Monitor ──
    pm_pcb_path = "output/power_monitor.kicad_pcb"
    pm_sch_path = "output/power_monitor.kicad_sch"
    print("   → [Power Monitor] 生成 PCB + 原理圖...")
    try:
        generate_power_monitor_pcb(pm_pcb_path)
        print(f"   ✅  PCB：{pm_pcb_path}")
    except Exception as e:
        print(f"   ❌  PCB 生成失敗：{e}")

    try:
        generate_power_monitor_schematic(pm_sch_path)
        print(f"   ✅  原理圖：{pm_sch_path}")
    except Exception as e:
        print(f"   ❌  原理圖生成失敗：{e}")

    # ── 進階匯出 (選用) ──
    exporter = PCBExporter(NETLIST_OUTPUT)

    print("   → 嘗試自動佈線 (Freerouting)...")
    result = exporter.auto_route()
    print(f"   {'✅' if result.success else '⚠️'}  {result.message}")

    print("   → 嘗試匯出 3D STEP 模型...")
    result = exporter.export_3d_model()
    print(f"   {'✅' if result.success else '⚠️'}  {result.message}")

    print("   → 嘗試匯出 Gerber 製造檔...")
    result = exporter.export_gerber()
    print(f"   {'✅' if result.success else '⚠️'}  {result.message}")

    manifest_path = exporter.generate_build_manifest()
    print(f"   📋 建構清單：{manifest_path}")

    return True


def step_preview() -> None:
    """Step 4: 啟動 KiCanvas 視覺化預覽"""
    print("\n🌐 [4/4] 啟動本地伺服器，準備 2D/3D 預覽...")

    try:
        from lib.web_server import start_preview_server
        start_preview_server(port=8000, open_browser=True)
    except KeyboardInterrupt:
        print("\n🛑 預覽伺服器已停止")
    except Exception as e:
        print(f"   ⚠️  預覽伺服器啟動失敗：{e}")


def run_pipeline(strict: bool = False, skip_preview: bool = False) -> None:
    """執行完整自動化管線"""
    print(BANNER)
    start_time = time.time()

    # Step 1
    if not step_compile_circuit():
        print("\n💀 流程中止於 Step 1（電路編譯）")
        sys.exit(1)

    # Step 2
    if not step_analyze(strict=strict):
        print("\n💀 流程中止於 Step 2（靜態檢查）")
        sys.exit(2)

    # Step 3
    step_export()

    elapsed = time.time() - start_time
    print(f"\n⏱️  總耗時：{elapsed:.1f} 秒")
    print("=" * 60)
    print("🎉 Vibe-PCB 管線執行完成！")
    print("   產出目錄：output/")
    print("=" * 60)

    # Step 4 (阻塞式，放最後)
    if not skip_preview:
        step_preview()


def main():
    parser = argparse.ArgumentParser(
        description="Vibe-PCB Orchestrator — Hardware Design as Code",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="嚴格模式：靜態檢查發現錯誤時中止流程",
    )
    parser.add_argument(
        "--no-preview", action="store_true",
        help="跳過 Web 預覽伺服器",
    )
    parser.add_argument(
        "--analyze-only", action="store_true",
        help="僅執行 Step 1 + 2（編譯 + 檢查），不匯出",
    )
    args = parser.parse_args()

    if args.analyze_only:
        print(BANNER)
        if step_compile_circuit():
            step_analyze(strict=args.strict)
    else:
        run_pipeline(strict=args.strict, skip_preview=args.no_preview)


if __name__ == "__main__":
    main()

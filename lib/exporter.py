"""
PCB Exporter — 自動佈線與檔案輸出

流程：
1. Netlist → KiCad PCB (kicad-cli)
2. PCB → Freerouting 自動佈線
3. PCB → 3D STEP 模型匯出
4. PCB → Gerber 製造檔
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ExportResult:
    success: bool
    message: str
    output_file: Optional[str] = None


class PCBExporter:
    """PCB 自動佈線與輸出管線"""

    def __init__(self, netlist_path: str, output_dir: str = "output"):
        self.netlist_path = Path(netlist_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pcb_path = self.output_dir / self.netlist_path.stem
        self.pcb_file = self.pcb_path.with_suffix(".kicad_pcb")
        self.dsn_file = self.pcb_path.with_suffix(".dsn")
        self.ses_file = self.pcb_path.with_suffix(".ses")
        self.step_file = self.pcb_path.with_suffix(".step")
        self.gerber_dir = self.output_dir / "gerber"

    # ── 工具偵測 ──

    @staticmethod
    def _find_tool(name: str) -> Optional[str]:
        """尋找外部工具路徑"""
        return shutil.which(name)

    def _check_kicad_cli(self) -> bool:
        path = self._find_tool("kicad-cli")
        if path:
            return True
        # Windows 常見安裝路徑
        for candidate in [
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\7.0\bin\kicad-cli.exe",
        ]:
            if Path(candidate).exists():
                return True
        return False

    def _get_kicad_cli(self) -> str:
        path = self._find_tool("kicad-cli")
        if path:
            return path
        for candidate in [
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\7.0\bin\kicad-cli.exe",
        ]:
            if Path(candidate).exists():
                return candidate
        return "kicad-cli"

    def _find_freerouting(self) -> Optional[str]:
        """尋找 Freerouting JAR 或執行檔"""
        jar = self._find_tool("freerouting")
        if jar:
            return jar

        # 搜尋常見位置
        search_paths = [
            Path.home() / "freerouting" / "freerouting.jar",
            Path.home() / "Downloads" / "freerouting.jar",
            Path("freerouting.jar"),
        ]
        for p in search_paths:
            if p.exists():
                return str(p)
        return None

    # ── Step 1: Netlist → KiCad PCB ──

    def import_netlist(self) -> ExportResult:
        """將 SKiDL 產出的 Netlist 匯入 KiCad 建立 PCB 專案"""
        if not self.netlist_path.exists():
            return ExportResult(False, f"Netlist 不存在：{self.netlist_path}")

        if not self._check_kicad_cli():
            # 建立最小可用的 PCB 骨架 (讓後續流程可以繼續)
            return self._create_minimal_pcb()

        kicad_cli = self._get_kicad_cli()
        try:
            subprocess.run(
                [kicad_cli, "pcb", "import", "--input", str(self.netlist_path),
                 "--output", str(self.pcb_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return ExportResult(True, "Netlist 匯入完成", str(self.pcb_file))
        except subprocess.CalledProcessError as e:
            return ExportResult(False, f"kicad-cli 匯入失敗：{e.stderr}")
        except FileNotFoundError:
            return self._create_minimal_pcb()

    def _create_minimal_pcb(self) -> ExportResult:
        """當 KiCad CLI 不可用時，建立最小佔位 PCB 檔供開發測試"""
        minimal = (
            '(kicad_pcb (version 20230121) (generator "vibe-pcb")\n'
            '  (general (thickness 1.6) (legacy_teardrops no))\n'
            '  (paper "A4")\n'
            '  (layers\n'
            '    (0 "F.Cu" signal)\n'
            '    (31 "B.Cu" signal)\n'
            '    (36 "B.SilkS" user "B.Silkscreen")\n'
            '    (37 "F.SilkS" user "F.Silkscreen")\n'
            '    (44 "Edge.Cuts" user)\n'
            '  )\n'
            '  (net 0 "")\n'
            '  (net 1 "3V3")\n'
            '  (net 2 "GND")\n'
            '  (net 3 "12V")\n'
            ')\n'
        )
        self.pcb_file.write_text(minimal, encoding="utf-8")
        return ExportResult(
            True,
            "KiCad CLI 不可用，已建立最小 PCB 骨架（需手動佈局）",
            str(self.pcb_file),
        )

    # ── Step 2: 自動佈線 (Freerouting) ──

    def auto_route(self) -> ExportResult:
        """使用 Freerouting 進行自動佈線"""
        # 先確保有 PCB 檔
        if not self.pcb_file.exists():
            result = self.import_netlist()
            if not result.success:
                return result

        freerouting = self._find_freerouting()
        if not freerouting:
            return ExportResult(
                False,
                "找不到 Freerouting。請下載 freerouting.jar 並放在 PATH 或專案目錄中。\n"
                "下載連結：https://github.com/freerouting/freerouting/releases",
            )

        # 匯出 DSN
        kicad_cli = self._get_kicad_cli()
        try:
            subprocess.run(
                [kicad_cli, "pcb", "export", "dsn",
                 "--input", str(self.pcb_file),
                 "--output", str(self.dsn_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return ExportResult(False, f"DSN 匯出失敗：{e}")

        # Freerouting 自動佈線
        try:
            cmd = (
                ["java", "-jar", freerouting, "-de", str(self.dsn_file),
                 "-do", str(self.ses_file), "-mp", "30"]
                if freerouting.endswith(".jar")
                else [freerouting, "-de", str(self.dsn_file),
                      "-do", str(self.ses_file), "-mp", "30"]
            )
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.CalledProcessError as e:
            return ExportResult(False, f"Freerouting 佈線失敗：{e.stderr}")

        # 匯入佈線結果
        try:
            subprocess.run(
                [kicad_cli, "pcb", "import", "--input", str(self.ses_file),
                 "--output", str(self.pcb_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            return ExportResult(False, f"SES 匯入失敗：{e.stderr}")

        return ExportResult(True, "自動佈線完成", str(self.pcb_file))

    # ── Step 3: 3D STEP 匯出 ──

    def export_3d_model(self) -> ExportResult:
        """匯出 3D STEP 模型"""
        if not self.pcb_file.exists():
            return ExportResult(False, "PCB 檔案不存在，無法匯出 3D 模型")

        kicad_cli = self._get_kicad_cli()
        try:
            subprocess.run(
                [kicad_cli, "pcb", "export", "step",
                 "--input", str(self.pcb_file),
                 "--output", str(self.step_file),
                 "--subst-models"],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return ExportResult(True, "3D STEP 模型已匯出", str(self.step_file))
        except subprocess.CalledProcessError as e:
            return ExportResult(False, f"STEP 匯出失敗：{e.stderr}")
        except FileNotFoundError:
            return ExportResult(
                False,
                "KiCad CLI 不可用，無法匯出 3D 模型。請安裝 KiCad 8.0+",
            )

    # ── Step 4: Gerber 製造檔 ──

    def export_gerber(self) -> ExportResult:
        """匯出 Gerber 製造檔案"""
        if not self.pcb_file.exists():
            return ExportResult(False, "PCB 檔案不存在，無法匯出 Gerber")

        self.gerber_dir.mkdir(parents=True, exist_ok=True)
        kicad_cli = self._get_kicad_cli()

        try:
            subprocess.run(
                [kicad_cli, "pcb", "export", "gerbers",
                 "--input", str(self.pcb_file),
                 "--output", str(self.gerber_dir)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return ExportResult(True, "Gerber 檔案已匯出", str(self.gerber_dir))
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return ExportResult(False, f"Gerber 匯出失敗：{e}")

    # ── 產出報表 ──

    def generate_build_manifest(self) -> str:
        """產生建構清單 JSON"""
        manifest = {
            "project": "AI Server Fan Controller",
            "tool": "Vibe-PCB Orchestrator",
            "files": {
                "netlist": str(self.netlist_path),
                "pcb": str(self.pcb_file) if self.pcb_file.exists() else None,
                "step": str(self.step_file) if self.step_file.exists() else None,
                "gerber": str(self.gerber_dir) if self.gerber_dir.exists() else None,
            },
        }
        manifest_path = self.output_dir / "build_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(manifest_path)

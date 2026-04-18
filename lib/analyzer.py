"""
PCB Analyzer — 電壓守衛 (Voltage Guard) 與零件合規性檢查 (BOM Checker)

核心邏輯：
1. 掃描 Netlist，偵測跨電壓域短路風險（例如 12V 訊號直連 3V3 IC）
2. 零件封裝與庫存可用性檢查
3. 產出風險報告供 AI 進一步分析

支援 KiCad S-expression 格式 (.net) — 由 SKiDL generate_netlist() 產出
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


# ── 常數定義 ──
VOLTAGE_NETS = {"3V3": 3.3, "12V": 12.0, "12V_INPUT": 12.0, "12V_OUTPUT": 12.0, "5V": 5.0, "1V8": 1.8}

# 封裝功率上限 (W)
PACKAGE_POWER_LIMITS = {
    "0402": 0.1, "0603": 0.1, "0805": 0.125,
    "1206": 0.25, "2512": 2.0, "1210": 0.5,
}

# 已知模組的 I2C 位址表 (hex_addr -> module_name)
I2C_ADDRESSES: dict[int, str] = {}

# EMC2103 腳位允許電壓範圍 (pin_name -> max_voltage)
EMC2103_PIN_VOLTAGE_LIMITS = {
    "VCC": 3.6,
    "VDDIO": 3.6,
    "GND": 0.0,
    "SDA": 3.6,
    "SCL": 3.6,
    "SMBALERT": 3.6,
    "ADDR_SEL": 3.6,
    "FAN_PWM": 3.6,
    "FAN_TACH": 3.6,
}

# 風扇接頭腳位允許電壓
FAN_CONNECTOR_PIN_LIMITS = {
    "1": 0.0,   # GND
    "2": 13.0,  # 12V 供電
    "3": 5.5,   # Tach (可達 5V)
    "4": 5.5,   # PWM
}


@dataclass
class CheckResult:
    """單項檢查結果"""
    severity: str          # "ERROR", "WARNING", "INFO"
    category: str          # "VOLTAGE", "BOM", "CONNECTIVITY"
    message: str
    net_name: Optional[str] = None
    component: Optional[str] = None


@dataclass
class RiskReport:
    """完整風險報告"""
    results: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self):
        return [r for r in self.results if r.severity == "ERROR"]

    @property
    def warnings(self):
        return [r for r in self.results if r.severity == "WARNING"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = ["=" * 60, "📄 Vibe-PCB 風險報告", "=" * 60]
        for r in self.results:
            icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(r.severity, "?")
            lines.append(f"  {icon} [{r.severity}][{r.category}] {r.message}")
        lines.append("-" * 60)
        lines.append(
            f"  合計：{len(self.errors)} 錯誤 / {len(self.warnings)} 警告 / "
            f"{len(self.results) - len(self.errors) - len(self.warnings)} 資訊"
        )
        status = "🟢 通過" if self.passed else "🔴 未通過 — 請修正後重試"
        lines.append(f"  狀態：{status}")
        lines.append("=" * 60)
        return "\n".join(lines)


class PCBAnalyzer:
    """Netlist 靜態分析器（支援 KiCad S-expression 格式）"""

    def __init__(self, netlist_path: str):
        self.netlist_path = Path(netlist_path)
        self.report = RiskReport()
        self._nets: dict[str, list[dict]] = {}   # net_name -> [{ref, pin, pinfunction}, ...]
        self._components: dict[str, dict] = {}    # ref -> {lib, part, footprint, value}

    # ── S-expression 解析器 ──

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """將 S-expression 文字拆分為 token 列表"""
        tokens: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c in (" ", "\t", "\n", "\r"):
                i += 1
            elif c == "(":
                tokens.append("(")
                i += 1
            elif c == ")":
                tokens.append(")")
                i += 1
            elif c == '"':
                # 帶引號的字串
                j = i + 1
                while j < n and text[j] != '"':
                    if text[j] == "\\":
                        j += 1  # 跳過轉義字元
                    j += 1
                tokens.append(text[i + 1 : j])  # 不含引號
                i = j + 1
            else:
                # 不帶引號的 atom
                j = i
                while j < n and text[j] not in (" ", "\t", "\n", "\r", "(", ")"):
                    j += 1
                tokens.append(text[i:j])
                i = j
        return tokens

    @staticmethod
    def _parse_sexpr(tokens: list[str], pos: int = 0) -> tuple[Any, int]:
        """遞迴解析 S-expression → 巢狀 list/str 結構"""
        if tokens[pos] == "(":
            lst: list[Any] = []
            pos += 1
            while tokens[pos] != ")":
                val, pos = PCBAnalyzer._parse_sexpr(tokens, pos)
                lst.append(val)
            return lst, pos + 1  # 跳過 ")"
        else:
            return tokens[pos], pos + 1

    @staticmethod
    def _find(node: list, tag: str) -> Optional[list]:
        """在 S-expression 節點中找第一個匹配 tag 的子節點"""
        if not isinstance(node, list):
            return None
        for child in node:
            if isinstance(child, list) and len(child) > 0 and child[0] == tag:
                return child
        return None

    @staticmethod
    def _find_all(node: list, tag: str) -> list[list]:
        """找所有匹配 tag 的子節點"""
        results = []
        if not isinstance(node, list):
            return results
        for child in node:
            if isinstance(child, list) and len(child) > 0 and child[0] == tag:
                results.append(child)
        return results

    @staticmethod
    def _get_value(node: list, tag: str, default: str = "") -> str:
        """取得子節點的文字值，例如 (ref "C1") → "C1" """
        found = PCBAnalyzer._find(node, tag)
        if found and len(found) > 1:
            return str(found[1])
        return default

    # ── 解析 ──

    def _parse_netlist(self):
        """解析 KiCad S-expression Netlist (.net)"""
        if not self.netlist_path.exists():
            self.report.results.append(CheckResult(
                severity="ERROR",
                category="FILE",
                message=f"找不到 Netlist 檔案：{self.netlist_path}",
            ))
            return False

        try:
            text = self.netlist_path.read_text(encoding="utf-8")
            tokens = self._tokenize(text)
            root, _ = self._parse_sexpr(tokens, 0)
        except Exception as exc:
            self.report.results.append(CheckResult(
                severity="ERROR",
                category="FILE",
                message=f"Netlist 解析失敗：{exc}",
            ))
            return False

        if not isinstance(root, list) or root[0] != "export":
            self.report.results.append(CheckResult(
                severity="ERROR",
                category="FILE",
                message="Netlist 格式錯誤：缺少 (export ...) 根節點",
            ))
            return False

        # 解析零件 (components → comp)
        components_node = self._find(root, "components")
        if components_node:
            for comp in self._find_all(components_node, "comp"):
                ref = self._get_value(comp, "ref")
                footprint = self._get_value(comp, "footprint")
                value = self._get_value(comp, "value")
                libsource = self._find(comp, "libsource")
                lib = self._get_value(libsource, "lib") if libsource else ""
                part = self._get_value(libsource, "part") if libsource else ""
                self._components[ref] = {
                    "lib": lib,
                    "part": part,
                    "footprint": footprint,
                    "value": value,
                }

        # 解析網路 (nets → net)
        nets_node = self._find(root, "nets")
        if nets_node:
            for net in self._find_all(nets_node, "net"):
                net_name = self._get_value(net, "name")
                nodes = []
                for node in self._find_all(net, "node"):
                    nodes.append({
                        "ref": self._get_value(node, "ref"),
                        "pin": self._get_value(node, "pin"),
                        "pinfunction": self._get_value(node, "pinfunction"),
                        "pintype": self._get_value(node, "pintype"),
                    })
                self._nets[net_name] = nodes

        self.report.results.append(CheckResult(
            severity="INFO",
            category="FILE",
            message=f"成功載入 Netlist：{len(self._components)} 零件 / {len(self._nets)} 網路",
        ))
        return True

    # ── 電壓守衛 (Voltage Guard) ──

    def _check_voltage_domains(self):
        """檢查跨電壓域短路風險"""
        for net_name, nodes in self._nets.items():
            # 判斷此 Net 屬於哪個電壓域
            net_voltage = VOLTAGE_NETS.get(net_name)

            if net_voltage is None:
                # 不是已知電源 Net，跳過電壓域判斷
                continue

            for node in nodes:
                ref = node["ref"]
                pin = node["pinfunction"] or node["pin"]
                comp = self._components.get(ref, {})
                part_name = comp.get("part", "")

                # EMC2103 腳位電壓檢查
                if "EMC2103" in part_name:
                    limit = EMC2103_PIN_VOLTAGE_LIMITS.get(pin)
                    if limit is not None and net_voltage > limit:
                        self.report.results.append(CheckResult(
                            severity="ERROR",
                            category="VOLTAGE",
                            message=(
                                f"電壓超限！{ref}({part_name}).{pin} 連接至 "
                                f"{net_name}({net_voltage}V)，但該腳位最高僅允許 {limit}V"
                            ),
                            net_name=net_name,
                            component=ref,
                        ))

                # 風扇接頭電壓檢查
                if "Conn_01x04" in part_name:
                    limit = FAN_CONNECTOR_PIN_LIMITS.get(node["pin"])
                    if limit is not None and net_voltage > limit:
                        self.report.results.append(CheckResult(
                            severity="ERROR",
                            category="VOLTAGE",
                            message=(
                                f"風扇接頭電壓錯誤！{ref}.Pin{node['pin']} 連接至 "
                                f"{net_name}({net_voltage}V)，但此腳位最高僅允許 {limit}V"
                            ),
                            net_name=net_name,
                            component=ref,
                        ))

        # 跨域短路偵測：同一 Net 上不應有多個不同電壓標籤
        voltage_net_names = set(VOLTAGE_NETS.keys())
        for net_name, nodes in self._nets.items():
            connected_voltage_nets = set()
            for node in nodes:
                # 檢查此零件的其他腳位是否連到不同電壓網路
                ref = node["ref"]
                for other_net, other_nodes in self._nets.items():
                    if other_net == net_name:
                        continue
                    if other_net in voltage_net_names:
                        for other_node in other_nodes:
                            if other_node["ref"] == ref:
                                connected_voltage_nets.add(other_net)

            if len(connected_voltage_nets) > 1 and net_name not in voltage_net_names:
                self.report.results.append(CheckResult(
                    severity="WARNING",
                    category="VOLTAGE",
                    message=(
                        f"Net '{net_name}' 上的零件同時連接至多個電壓域："
                        f"{', '.join(sorted(connected_voltage_nets))}，請確認是否有 Level Shift 隔離"
                    ),
                    net_name=net_name,
                ))

    # ── 零件合規性 (BOM Checker) ──

    def _check_bom_compliance(self):
        """檢查封裝可用性與基本合規"""
        KNOWN_FOOTPRINTS = {
            "C_0402_1005Metric", "C_0603_1608Metric", "C_0805_2012Metric",
            "C_1206_3216Metric", "R_0402_1005Metric", "R_0603_1608Metric",
            "QFN-20-1EP_4x4mm_P0.5mm_EP2.65x2.65mm",
            "PinHeader_1x04_P2.54mm_Vertical",
        }

        for ref, comp in self._components.items():
            fp = comp.get("footprint", "")
            # 提取封裝名稱（去掉庫前綴）
            fp_name = fp.split(":")[-1] if ":" in fp else fp

            if not fp:
                self.report.results.append(CheckResult(
                    severity="ERROR",
                    category="BOM",
                    message=f"{ref} 缺少 footprint 定義",
                    component=ref,
                ))
            elif fp_name not in KNOWN_FOOTPRINTS:
                self.report.results.append(CheckResult(
                    severity="WARNING",
                    category="BOM",
                    message=f"{ref} 使用封裝 '{fp_name}'，不在已知封裝庫中，請確認可用性",
                    component=ref,
                ))
            else:
                self.report.results.append(CheckResult(
                    severity="INFO",
                    category="BOM",
                    message=f"{ref} ({comp.get('value', '?')}) → {fp_name} ✔",
                    component=ref,
                ))

    # ── 連通性檢查 ──

    def _check_connectivity(self):
        """檢查必要的電源與接地連線"""
        has_vcc = "3V3" in self._nets
        has_gnd = "GND" in self._nets
        has_12v = "12V" in self._nets

        if not has_vcc:
            self.report.results.append(CheckResult(
                severity="ERROR", category="CONNECTIVITY",
                message="缺少 3V3 電源網路",
            ))
        if not has_gnd:
            self.report.results.append(CheckResult(
                severity="ERROR", category="CONNECTIVITY",
                message="缺少 GND 接地網路",
            ))
        if not has_12v:
            self.report.results.append(CheckResult(
                severity="WARNING", category="CONNECTIVITY",
                message="未偵測到 12V 風扇電源網路",
            ))

        # 檢查去耦電容是否連接
        decoupling_found = False
        for ref, comp in self._components.items():
            if comp.get("part") == "C" and comp.get("value") in ("100nF", "0.1uF"):
                decoupling_found = True
                break

        if not decoupling_found:
            self.report.results.append(CheckResult(
                severity="WARNING", category="CONNECTIVITY",
                message="未偵測到 VCC 去耦電容 (建議 100nF)，可能影響訊號穩定性",
            ))

    # ── 主入口 ──

    def run_checks(self) -> RiskReport:
        """執行所有靜態檢查並回傳風險報告"""
        if not self._parse_netlist():
            return self.report

        self._check_voltage_domains()
        self._check_bom_compliance()
        self._check_connectivity()
        self._check_power_dissipation()
        self._check_i2c_conflicts()

        return self.report

    # ── P = I²R 電阻功率檢查 ──

    def _check_power_dissipation(self):
        """檢查分流/功率電阻的 P = I²R 是否超過封裝額定值"""
        for ref, comp in self._components.items():
            # 只檢查電阻
            if comp.get("part") not in ("R", "R_Shunt"):
                continue

            value_str = comp.get("value", "")
            fp = comp.get("footprint", "")
            fp_name = fp.split(":")[-1] if ":" in fp else fp

            # 解析電阻值 (支援 2mΩ, 0.002, 4.7k 等)
            r_val = self._parse_resistance(value_str)
            if r_val is None:
                continue

            # 判斷封裝功率上限
            pkg_power = None
            for pkg_key, limit in PACKAGE_POWER_LIMITS.items():
                if pkg_key in fp_name:
                    pkg_power = limit
                    break

            if pkg_power is None:
                continue

            # 找此電阻連接的網路，推算最大電流
            max_current = self._estimate_max_current(ref)
            if max_current <= 0:
                continue

            power = max_current ** 2 * r_val
            margin = pkg_power - power

            if power > pkg_power:
                self.report.results.append(CheckResult(
                    severity="ERROR",
                    category="POWER",
                    message=(
                        f"功率超限！{ref} ({value_str}) P = I²R = {max_current:.1f}² × {r_val} = "
                        f"{power:.2f}W，超過 {fp_name} 額定 {pkg_power}W"
                    ),
                    component=ref,
                ))
            elif margin < pkg_power * 0.2:
                self.report.results.append(CheckResult(
                    severity="WARNING",
                    category="POWER",
                    message=(
                        f"功率接近上限！{ref} ({value_str}) P = {power:.2f}W / {pkg_power}W "
                        f"(餘量 {margin:.2f}W, {margin/pkg_power*100:.0f}%)"
                    ),
                    component=ref,
                ))
            else:
                self.report.results.append(CheckResult(
                    severity="INFO",
                    category="POWER",
                    message=(
                        f"{ref} ({value_str}) P = {power:.3f}W / {pkg_power}W ✔ "
                        f"(餘量 {margin/pkg_power*100:.0f}%)"
                    ),
                    component=ref,
                ))

    @staticmethod
    def _parse_resistance(val: str) -> Optional[float]:
        """解析電阻值字串，回傳歐姆數"""
        val = val.strip().replace("Ω", "").replace("ohm", "").replace("Ohm", "")
        # 2mΩ / 2m / 0.002
        m = re.match(r"^([\d.]+)\s*m$", val, re.IGNORECASE)
        if m:
            return float(m.group(1)) * 0.001
        # 4.7k
        m = re.match(r"^([\d.]+)\s*k$", val, re.IGNORECASE)
        if m:
            return float(m.group(1)) * 1000
        # 10M
        m = re.match(r"^([\d.]+)\s*M$", val)
        if m:
            return float(m.group(1)) * 1e6
        # plain number
        m = re.match(r"^([\d.]+)$", val)
        if m:
            return float(m.group(1))
        return None

    def _estimate_max_current(self, ref: str) -> float:
        """根據電阻連接的網路推估最大電流"""
        comp = self._components.get(ref, {})
        part = comp.get("part", "")

        # 分流電阻 (R_Shunt) 直接標定為高電流
        if part == "R_Shunt":
            return 30.0

        # 檢查是否兩端都連到 12V 相關的高電流網路
        connected_nets = set()
        for net_name, nodes in self._nets.items():
            for node in nodes:
                if node["ref"] == ref:
                    connected_nets.add(net_name)

        high_current_nets = [n for n in connected_nets if "12V" in n]
        # 只有當電阻串接在 12V 路徑上 (兩端都是 12V 相關) 才視為高電流
        if len(high_current_nets) >= 2:
            return 30.0
        # 信號電阻 (pull-up 等)
        if any("3V3" in n or "I2C" in n or "SDA" in n or "SCL" in n for n in connected_nets):
            return 0.001  # ~1mA
        return 0.0

    # ── I2C 位址衝突檢查 ──

    def _check_i2c_conflicts(self):
        """跨模組 I2C 位址衝突偵測"""
        if not I2C_ADDRESSES:
            return

        # 找出重複
        addr_modules: dict[int, list[str]] = {}
        for addr, mod in I2C_ADDRESSES.items():
            addr_modules.setdefault(addr, []).append(mod)

        for addr, modules in addr_modules.items():
            if len(modules) > 1:
                self.report.results.append(CheckResult(
                    severity="ERROR",
                    category="I2C",
                    message=(
                        f"I2C 位址衝突！0x{addr:02X} 被多個模組使用："
                        f"{', '.join(modules)}"
                    ),
                ))
            else:
                self.report.results.append(CheckResult(
                    severity="INFO",
                    category="I2C",
                    message=f"I2C 0x{addr:02X} → {modules[0]} ✔ (無衝突)",
                ))

"""
PCB Generator — 從 Netlist 直接生成 KiCad PCB 檔案 (無需 KiCad 安裝)

產出可被 KiCanvas 即時渲染的 .kicad_pcb 檔案，包含：
- 完整層疊定義
- 零件 footprint（含真實焊墊）
- 網路連線
- 板框 (Edge.Cuts)
- 銅線走線
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path


def _uuid() -> str:
    return str(uuid.uuid4())


# ────────────────────────────────────────────
#  資料結構
# ────────────────────────────────────────────

@dataclass
class Pad:
    number: str
    pad_type: str       # "smd", "thru_hole"
    shape: str          # "rect", "circle", "roundrect", "oval"
    at: tuple[float, float, float]  # x, y, rotation
    size: tuple[float, float]
    layers: list[str]
    net_num: int = 0
    net_name: str = ""
    drill: float | None = None

    def to_sexpr(self) -> str:
        rot = f" {self.at[2]}" if self.at[2] != 0 else ""
        s = f'    (pad "{self.number}" {self.pad_type} {self.shape} (at {self.at[0]} {self.at[1]}{rot}) (size {self.size[0]} {self.size[1]})'
        if self.drill is not None:
            s += f" (drill {self.drill})"
        layers = " ".join(f'"{l}"' for l in self.layers)
        s += f" (layers {layers})"
        if self.net_num > 0:
            s += f' (net {self.net_num} "{self.net_name}")'
        s += ")"
        return s


@dataclass
class Footprint:
    library: str
    ref: str
    value: str
    at: tuple[float, float, float]  # x, y, rotation
    layer: str
    pads: list[Pad] = field(default_factory=list)
    fp_lines: list[str] = field(default_factory=list)  # 額外的 silkscreen 線條
    fp_uuid: str = field(default_factory=_uuid)

    def to_sexpr(self) -> str:
        rot = f" {self.at[2]}" if self.at[2] != 0 else ""
        lines = [
            f'  (footprint "{self.library}"',
            f'    (layer "{self.layer}")',
            f"    (uuid \"{self.fp_uuid}\")",
            f'    (at {self.at[0]} {self.at[1]}{rot})',
            f'    (property "Reference" "{self.ref}" (at 0 -2.5 0) (layer "{self.layer.replace("Cu", "SilkS")}") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'    (property "Value" "{self.value}" (at 0 2.5 0) (layer "{self.layer.replace("Cu", "Fab")}") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        ]
        for fl in self.fp_lines:
            lines.append(f"    {fl}")
        for pad in self.pads:
            lines.append(pad.to_sexpr())
        lines.append("  )")
        return "\n".join(lines)


@dataclass
class Trace:
    start: tuple[float, float]
    end: tuple[float, float]
    width: float
    layer: str
    net_num: int

    def to_sexpr(self) -> str:
        return (
            f"  (segment (start {self.start[0]} {self.start[1]}) "
            f"(end {self.end[0]} {self.end[1]}) "
            f"(width {self.width}) (layer \"{self.layer}\") "
            f"(net {self.net_num}) (uuid \"{_uuid()}\"))"
        )


@dataclass
class Via:
    at: tuple[float, float]
    size: float
    drill: float
    net_num: int
    layers: tuple[str, str] = ("F.Cu", "B.Cu")

    def to_sexpr(self) -> str:
        return (
            f"  (via (at {self.at[0]} {self.at[1]}) "
            f"(size {self.size}) (drill {self.drill}) "
            f"(layers \"{self.layers[0]}\" \"{self.layers[1]}\") "
            f"(net {self.net_num}) (uuid \"{_uuid()}\"))"
        )


# ────────────────────────────────────────────
#  Footprint 工廠
# ────────────────────────────────────────────

def _make_qfn20_fp(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """QFN-20 4×4mm (EMC2103)"""
    fp = Footprint(
        library="Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.65x2.65mm",
        ref=ref, value=value, at=at, layer="F.Cu",
    )

    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    pad_size = (0.3, 0.8)

    # 底部 (pin 1-5): y=2.0, x from -1.0 to 1.0
    for i in range(5):
        fp.pads.append(Pad(
            number=str(i + 1), pad_type="smd", shape="roundrect",
            at=(-1.0 + i * 0.5, 2.0, 0), size=pad_size, layers=smd_layers,
        ))
    # 右側 (pin 6-10): x=2.0, y from 1.0 to -1.0
    for i in range(5):
        fp.pads.append(Pad(
            number=str(6 + i), pad_type="smd", shape="roundrect",
            at=(2.0, 1.0 - i * 0.5, 90), size=pad_size, layers=smd_layers,
        ))
    # 頂部 (pin 11-15): y=-2.0, x from 1.0 to -1.0
    for i in range(5):
        fp.pads.append(Pad(
            number=str(11 + i), pad_type="smd", shape="roundrect",
            at=(1.0 - i * 0.5, -2.0, 0), size=pad_size, layers=smd_layers,
        ))
    # 左側 (pin 16-20): x=-2.0, y from -1.0 to 1.0
    for i in range(5):
        fp.pads.append(Pad(
            number=str(16 + i), pad_type="smd", shape="roundrect",
            at=(-2.0, -1.0 + i * 0.5, 90), size=pad_size, layers=smd_layers,
        ))
    # Exposed pad (pin 21)
    fp.pads.append(Pad(
        number="21", pad_type="smd", shape="roundrect",
        at=(0, 0, 0), size=(2.65, 2.65), layers=["F.Cu", "F.Paste", "F.Mask"],
    ))

    # Courtyard
    fp.fp_lines.append('(fp_rect (start -2.5 -2.5) (end 2.5 2.5) (layer "F.CrtYd") (width 0.05) (fill none) (uuid "' + _uuid() + '"))')
    # Silkscreen outline
    fp.fp_lines.append('(fp_rect (start -2.1 -2.1) (end 2.1 2.1) (layer "F.SilkS") (width 0.12) (fill none) (uuid "' + _uuid() + '"))')
    # Pin 1 marker
    fp.fp_lines.append('(fp_circle (center -1.0 2.8) (end -0.85 2.8) (layer "F.SilkS") (width 0.12) (fill solid) (uuid "' + _uuid() + '"))')

    return fp


def _make_pin_header_1x04(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """1x04 Pin Header 2.54mm"""
    fp = Footprint(
        library="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        ref=ref, value=value, at=at, layer="F.Cu",
    )
    th_layers = ["*.Cu", "*.Mask"]
    for i in range(4):
        fp.pads.append(Pad(
            number=str(i + 1), pad_type="thru_hole",
            shape="oval" if i > 0 else "rect",
            at=(0, i * 2.54, 0), size=(1.7, 1.7),
            layers=th_layers, drill=1.0,
        ))
    # Silkscreen
    fp.fp_lines.append('(fp_rect (start -1.33 -1.33) (end 1.33 8.95) (layer "F.SilkS") (width 0.12) (fill none) (uuid "' + _uuid() + '"))')
    fp.fp_lines.append('(fp_rect (start -1.8 -1.8) (end 1.8 9.4) (layer "F.CrtYd") (width 0.05) (fill none) (uuid "' + _uuid() + '"))')
    return fp


def _make_smd_resistor(ref: str, value: str, at: tuple[float, float, float],
                       size_code: str = "0402") -> Footprint:
    """SMD Resistor (0402 / 0603)"""
    dims = {
        "0402": {"body": (0.5, 0.25), "pad": (0.5, 0.3), "pitch": 0.48,
                 "lib": "Resistor_SMD:R_0402_1005Metric"},
        "0603": {"body": (0.8, 0.4), "pad": (0.6, 0.5), "pitch": 0.75,
                 "lib": "Resistor_SMD:R_0603_1608Metric"},
    }
    d = dims.get(size_code, dims["0402"])
    fp = Footprint(library=d["lib"], ref=ref, value=value, at=at, layer="F.Cu")
    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    fp.pads.append(Pad(number="1", pad_type="smd", shape="roundrect",
                       at=(-d["pitch"], 0, 0), size=d["pad"], layers=smd_layers))
    fp.pads.append(Pad(number="2", pad_type="smd", shape="roundrect",
                       at=(d["pitch"], 0, 0), size=d["pad"], layers=smd_layers))
    bw, bh = d["body"]
    fp.fp_lines.append(f'(fp_rect (start {-bw} {-bh}) (end {bw} {bh}) (layer "F.Fab") (width 0.1) (fill none) (uuid "{_uuid()}"))')
    return fp


def _make_smd_capacitor(ref: str, value: str, at: tuple[float, float, float],
                        size_code: str = "0402") -> Footprint:
    """SMD Capacitor (0402 / 0603 / 0805 / 1206)"""
    dims = {
        "0402": {"pad": (0.5, 0.3), "pitch": 0.48,
                 "lib": "Capacitor_SMD:C_0402_1005Metric"},
        "0603": {"pad": (0.6, 0.5), "pitch": 0.75,
                 "lib": "Capacitor_SMD:C_0603_1608Metric"},
        "0805": {"pad": (0.7, 0.8), "pitch": 0.9,
                 "lib": "Capacitor_SMD:C_0805_2012Metric"},
        "1206": {"pad": (1.0, 1.2), "pitch": 1.5,
                 "lib": "Capacitor_SMD:C_1206_3216Metric"},
    }
    d = dims.get(size_code, dims["0402"])
    fp = Footprint(library=d["lib"], ref=ref, value=value, at=at, layer="F.Cu")
    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    fp.pads.append(Pad(number="1", pad_type="smd", shape="roundrect",
                       at=(-d["pitch"], 0, 0), size=d["pad"], layers=smd_layers))
    fp.pads.append(Pad(number="2", pad_type="smd", shape="roundrect",
                       at=(d["pitch"], 0, 0), size=d["pad"], layers=smd_layers))
    return fp


# ────────────────────────────────────────────
#  Fan Controller PCB 生成
# ────────────────────────────────────────────

# 網路名稱 → 編號對照
NETS = {
    "":           0,
    "3V3":        1,
    "GND":        2,
    "12V":        3,
    "I2C_SDA":    4,
    "I2C_SCL":    5,
    "FAN_PWM":    6,
    "FAN_TACH":   7,
    "SMBALERT_N": 8,
}


def _assign_net(pad: Pad, net_name: str):
    pad.net_num = NETS[net_name]
    pad.net_name = net_name


def generate_fan_controller_pcb(output_path: str = "output/fan_controller.kicad_pcb"):
    """生成 AI Server Fan Controller 的完整 PCB 佈局"""

    footprints: list[Footprint] = []
    traces: list[Trace] = []
    vias: list[Via] = []

    # ── 板子尺寸: 40mm × 30mm ──
    board_w, board_h = 40.0, 30.0
    ox, oy = 10.0, 10.0  # KiCad 原點偏移 (配合 60x50mm 頁面)

    # ── U1: EMC2103 (中央) ──
    u1 = _make_qfn20_fp("U1", "EMC2103", (ox + 16, oy + 14, 0))
    # EMC2103 pin mapping: 7=VCC, 8=VDDIO, 9=GND, 4=SDA, 5=SCL, 3=SMBALERT
    # 1=FAN_TACH, 2=FAN_PWM, 6=ADDR_SEL, 21=EP
    pin_net_map = {
        "1": "FAN_TACH", "2": "FAN_PWM", "3": "SMBALERT_N",
        "4": "I2C_SDA", "5": "I2C_SCL", "6": "GND",
        "7": "3V3", "8": "3V3", "9": "GND", "21": "GND",
    }
    for pad in u1.pads:
        net = pin_net_map.get(pad.number, "")
        if net:
            _assign_net(pad, net)
    footprints.append(u1)

    # ── J1: Fan Connector (右側) ──
    j1 = _make_pin_header_1x04("J1", "FAN_4PIN", (ox + 36, oy + 8, 0))
    j1_nets = {"1": "GND", "2": "12V", "3": "FAN_TACH", "4": "FAN_PWM"}
    for pad in j1.pads:
        net = j1_nets.get(pad.number, "")
        if net:
            _assign_net(pad, net)
    footprints.append(j1)

    # ── J2: BMC I2C Connector (左側) ──
    j2 = _make_pin_header_1x04("J2", "BMC_I2C", (ox + 4, oy + 8, 0))
    j2_nets = {"1": "I2C_SDA", "2": "I2C_SCL", "3": "SMBALERT_N", "4": "GND"}
    for pad in j2.pads:
        net = j2_nets.get(pad.number, "")
        if net:
            _assign_net(pad, net)
    footprints.append(j2)

    # ── R1: I2C SDA Pull-up (U1 左上) ──
    r1 = _make_smd_resistor("R1", "4.7k", (ox + 10, oy + 9, 0))
    _assign_net(r1.pads[0], "3V3")
    _assign_net(r1.pads[1], "I2C_SDA")
    footprints.append(r1)

    # ── R2: I2C SCL Pull-up ──
    r2 = _make_smd_resistor("R2", "4.7k", (ox + 10, oy + 12, 0))
    _assign_net(r2.pads[0], "3V3")
    _assign_net(r2.pads[1], "I2C_SCL")
    footprints.append(r2)

    # ── R3: SMBALERT Pull-up ──
    r3 = _make_smd_resistor("R3", "10k", (ox + 10, oy + 15, 0))
    _assign_net(r3.pads[0], "3V3")
    _assign_net(r3.pads[1], "SMBALERT_N")
    footprints.append(r3)

    # ── C1: VCC 100nF 去耦 (U1 上方) ──
    c1 = _make_smd_capacitor("C1", "100nF", (ox + 16, oy + 6, 0), "0402")
    _assign_net(c1.pads[0], "3V3")
    _assign_net(c1.pads[1], "GND")
    footprints.append(c1)

    # ── C2: VCC 10uF 大容量 ──
    c2 = _make_smd_capacitor("C2", "10uF", (ox + 20, oy + 6, 0), "0805")
    _assign_net(c2.pads[0], "3V3")
    _assign_net(c2.pads[1], "GND")
    footprints.append(c2)

    # ── C3: 12V 100nF (風扇接頭旁) ──
    c3 = _make_smd_capacitor("C3", "100nF", (ox + 30, oy + 8, 0), "0603")
    _assign_net(c3.pads[0], "12V")
    _assign_net(c3.pads[1], "GND")
    footprints.append(c3)

    # ── C4: 12V 100uF (風扇接頭旁) ──
    c4 = _make_smd_capacitor("C4", "100uF", (ox + 30, oy + 12, 0), "1206")
    _assign_net(c4.pads[0], "12V")
    _assign_net(c4.pads[1], "GND")
    footprints.append(c4)

    # ── 走線 (Traces) ──
    tw_signal = 0.2    # 訊號線寬
    tw_power = 0.4     # 電源線寬
    tw_12v = 0.6       # 12V 粗線

    # --- 3V3 電源線 ---
    # C1.1 → U1.VCC (pin7, 位於 right side 第2pin)
    traces.append(Trace((ox + 15.52, oy + 6), (ox + 15.5, oy + 12.5), tw_power, "F.Cu", NETS["3V3"]))
    traces.append(Trace((ox + 15.5, oy + 12.5), (ox + 18, oy + 12.5), tw_power, "F.Cu", NETS["3V3"]))
    # R1.1, R2.1, R3.1 → 3V3 bus
    traces.append(Trace((ox + 9.52, oy + 9), (ox + 9.52, oy + 12), tw_power, "F.Cu", NETS["3V3"]))
    traces.append(Trace((ox + 9.52, oy + 12), (ox + 9.52, oy + 15), tw_power, "F.Cu", NETS["3V3"]))
    traces.append(Trace((ox + 9.52, oy + 9), (ox + 15.52, oy + 6), tw_power, "F.Cu", NETS["3V3"]))

    # --- GND 電源線 (背面銅層) ---
    # C1.2 → GND via
    vias.append(Via((ox + 16.48, oy + 6), 0.6, 0.3, NETS["GND"]))
    vias.append(Via((ox + 20.9, oy + 6), 0.6, 0.3, NETS["GND"]))
    vias.append(Via((ox + 30.75, oy + 8), 0.6, 0.3, NETS["GND"]))
    vias.append(Via((ox + 31.5, oy + 12), 0.6, 0.3, NETS["GND"]))
    # U1 EP → GND via array
    for dx, dy in [(-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8)]:
        vias.append(Via((ox + 16 + dx, oy + 14 + dy), 0.4, 0.2, NETS["GND"]))
    # GND bus on B.Cu
    traces.append(Trace((ox + 2, oy + 28), (ox + 38, oy + 28), tw_12v, "B.Cu", NETS["GND"]))
    traces.append(Trace((ox + 16.48, oy + 6), (ox + 16.48, oy + 28), tw_power, "B.Cu", NETS["GND"]))
    traces.append(Trace((ox + 20.9, oy + 6), (ox + 20.9, oy + 28), tw_power, "B.Cu", NETS["GND"]))
    traces.append(Trace((ox + 30.75, oy + 8), (ox + 30.75, oy + 28), tw_power, "B.Cu", NETS["GND"]))

    # --- I2C_SDA: J2.1 → R1.2 → U1.SDA ---
    traces.append(Trace((ox + 4, oy + 8), (ox + 10.48, oy + 9), tw_signal, "F.Cu", NETS["I2C_SDA"]))
    traces.append(Trace((ox + 10.48, oy + 9), (ox + 14, oy + 12), tw_signal, "F.Cu", NETS["I2C_SDA"]))
    traces.append(Trace((ox + 14, oy + 12), (ox + 14, oy + 14.5), tw_signal, "F.Cu", NETS["I2C_SDA"]))

    # --- I2C_SCL: J2.2 → R2.2 → U1.SCL ---
    traces.append(Trace((ox + 4, oy + 10.54), (ox + 10.48, oy + 12), tw_signal, "F.Cu", NETS["I2C_SCL"]))
    traces.append(Trace((ox + 10.48, oy + 12), (ox + 14, oy + 15), tw_signal, "F.Cu", NETS["I2C_SCL"]))
    traces.append(Trace((ox + 14, oy + 15), (ox + 14, oy + 15.5), tw_signal, "F.Cu", NETS["I2C_SCL"]))

    # --- SMBALERT_N: J2.3 → R3.2 → U1.SMBALERT ---
    traces.append(Trace((ox + 4, oy + 13.08), (ox + 10.48, oy + 15), tw_signal, "F.Cu", NETS["SMBALERT_N"]))
    traces.append(Trace((ox + 10.48, oy + 15), (ox + 14, oy + 16), tw_signal, "F.Cu", NETS["SMBALERT_N"]))

    # --- FAN_PWM: U1.FAN_PWM → J1.4 ---
    traces.append(Trace((ox + 18, oy + 13), (ox + 26, oy + 13), tw_signal, "F.Cu", NETS["FAN_PWM"]))
    traces.append(Trace((ox + 26, oy + 13), (ox + 36, oy + 15.62), tw_signal, "F.Cu", NETS["FAN_PWM"]))

    # --- FAN_TACH: U1.FAN_TACH → J1.3 ---
    traces.append(Trace((ox + 18, oy + 14), (ox + 26, oy + 14), tw_signal, "F.Cu", NETS["FAN_TACH"]))
    traces.append(Trace((ox + 26, oy + 14), (ox + 36, oy + 13.08), tw_signal, "F.Cu", NETS["FAN_TACH"]))

    # --- 12V: J1.2 → C3.1 → C4.1 ---
    traces.append(Trace((ox + 36, oy + 10.54), (ox + 30, oy + 10.54), tw_12v, "F.Cu", NETS["12V"]))
    traces.append(Trace((ox + 30, oy + 10.54), (ox + 29.25, oy + 8), tw_12v, "F.Cu", NETS["12V"]))
    traces.append(Trace((ox + 30, oy + 10.54), (ox + 28.5, oy + 12), tw_12v, "F.Cu", NETS["12V"]))

    # ── 組合 PCB 文件 ──
    net_decls = "\n".join(f'  (net {num} "{name}")' for name, num in NETS.items())

    fp_texts = "\n".join(fp.to_sexpr() for fp in footprints)
    trace_texts = "\n".join(t.to_sexpr() for t in traces)
    via_texts = "\n".join(v.to_sexpr() for v in vias)

    # 板框座標
    bx1, by1 = ox, oy
    bx2, by2 = ox + board_w, oy + board_h

    pcb_content = f'''(kicad_pcb
  (version 20221018)
  (generator "Vibe-PCB-Orchestrator")
  (generator_version "0.1")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "User" 60 50)
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  (setup
    (pad_to_mask_clearance 0.05)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions no)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (pdf_front_fp_property_popups yes)
      (pdf_back_fp_property_popups yes)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
{net_decls}

  (gr_rect (start {bx1} {by1}) (end {bx2} {by2}) (layer "Edge.Cuts") (width 0.1) (fill none) (uuid "{_uuid()}"))

  (gr_text "AI Server Fan Controller" (at {ox + board_w / 2} {oy + board_h - 2}) (layer "F.SilkS")
    (effects (font (size 1.5 1.5) (thickness 0.2)) (justify center))
    (uuid "{_uuid()}")
  )
  (gr_text "Vibe-PCB v0.1" (at {ox + board_w / 2} {oy + 2}) (layer "F.SilkS")
    (effects (font (size 1 1) (thickness 0.15)) (justify center))
    (uuid "{_uuid()}")
  )

  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + 3} {oy + 3})
    (property "Reference" "H1" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + board_w - 3} {oy + 3})
    (property "Reference" "H2" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + 3} {oy + board_h - 3})
    (property "Reference" "H3" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + board_w - 3} {oy + board_h - 3})
    (property "Reference" "H4" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )

{fp_texts}

{trace_texts}

{via_texts}

  (zone (net {NETS["GND"]}) (net_name "GND") (layer "B.Cu") (uuid "{_uuid()}")
    (hatch edge 0.5)
    (connect_pads (clearance 0.3))
    (min_thickness 0.2)
    (filled_areas_thickness no)
    (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5))
    (polygon (pts
      (xy {bx1 + 0.5} {by1 + 0.5}) (xy {bx2 - 0.5} {by1 + 0.5})
      (xy {bx2 - 0.5} {by2 - 0.5}) (xy {bx1 + 0.5} {by2 - 0.5})
    ))
  )
)
'''

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pcb_content, encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    path = generate_fan_controller_pcb()
    print(f"✅ PCB 檔案已產出：{path}")

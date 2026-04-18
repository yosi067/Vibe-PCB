"""
PCB Generator — Smart Power Monitor Module
基於 INA226 的電源監控 PCB 佈局 (35mm × 25mm)

產出可被 KiCanvas 即時渲染的 .kicad_pcb 檔案。
"""

from __future__ import annotations
import uuid
from pathlib import Path

# 重用 fan_controller PCB 的基礎設施
from lib.pcb_generator import (
    Pad, Footprint, Trace, Via, _uuid,
    _make_smd_resistor, _make_smd_capacitor, _make_pin_header_1x04,
)


# ────────────────────────────────────────────
#  Power Monitor 專用 Footprint
# ────────────────────────────────────────────

def _make_msop10_fp(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """MSOP-10 3×3mm (INA226)"""
    fp = Footprint(
        library="Package_SO:MSOP-10_3x3mm_P0.5mm",
        ref=ref, value=value, at=at, layer="F.Cu",
    )
    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    pad_size = (0.3, 0.85)

    # Bottom pins 1-5: y = +1.5
    for i in range(5):
        fp.pads.append(Pad(
            number=str(i + 1), pad_type="smd", shape="roundrect",
            at=(-1.0 + i * 0.5, 1.5, 0), size=pad_size, layers=smd_layers,
        ))
    # Top pins 6-10: y = -1.5 (right to left)
    for i in range(5):
        fp.pads.append(Pad(
            number=str(6 + i), pad_type="smd", shape="roundrect",
            at=(1.0 - i * 0.5, -1.5, 0), size=pad_size, layers=smd_layers,
        ))

    # Courtyard
    fp.fp_lines.append(f'(fp_rect (start -2.0 -2.0) (end 2.0 2.0) (layer "F.CrtYd") (width 0.05) (fill none) (uuid "{_uuid()}"))')
    # Silkscreen
    fp.fp_lines.append(f'(fp_rect (start -1.6 -1.1) (end 1.6 1.1) (layer "F.SilkS") (width 0.12) (fill none) (uuid "{_uuid()}"))')
    # Pin 1 marker
    fp.fp_lines.append(f'(fp_circle (center -1.0 2.3) (end -0.85 2.3) (layer "F.SilkS") (width 0.12) (fill solid) (uuid "{_uuid()}"))')

    return fp


def _make_r_2512(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """2512 大功率電阻 (分流電阻)"""
    fp = Footprint(
        library="Resistor_SMD:R_2512_6332Metric",
        ref=ref, value=value, at=at, layer="F.Cu",
    )
    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    # 2512: 6.3mm × 3.2mm body, pads ~2.8mm from center
    fp.pads.append(Pad(
        number="1", pad_type="smd", shape="roundrect",
        at=(-2.8, 0, 0), size=(1.8, 3.0), layers=smd_layers,
    ))
    fp.pads.append(Pad(
        number="2", pad_type="smd", shape="roundrect",
        at=(2.8, 0, 0), size=(1.8, 3.0), layers=smd_layers,
    ))
    # Courtyard
    fp.fp_lines.append(f'(fp_rect (start -4.2 -2.0) (end 4.2 2.0) (layer "F.CrtYd") (width 0.05) (fill none) (uuid "{_uuid()}"))')
    # Fab outline
    fp.fp_lines.append(f'(fp_rect (start -3.15 -1.6) (end 3.15 1.6) (layer "F.Fab") (width 0.1) (fill none) (uuid "{_uuid()}"))')
    # Silkscreen
    fp.fp_lines.append(f'(fp_rect (start -3.3 -1.75) (end 3.3 1.75) (layer "F.SilkS") (width 0.12) (fill none) (uuid "{_uuid()}"))')
    return fp


def _make_pin_header_1x02(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """1×02 Pin Header 2.54mm"""
    fp = Footprint(
        library="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        ref=ref, value=value, at=at, layer="F.Cu",
    )
    th_layers = ["*.Cu", "*.Mask"]
    fp.pads.append(Pad(
        number="1", pad_type="thru_hole", shape="rect",
        at=(0, 0, 0), size=(1.7, 1.7), layers=th_layers, drill=1.0,
    ))
    fp.pads.append(Pad(
        number="2", pad_type="thru_hole", shape="oval",
        at=(0, 2.54, 0), size=(1.7, 1.7), layers=th_layers, drill=1.0,
    ))
    fp.fp_lines.append(f'(fp_rect (start -1.33 -1.33) (end 1.33 3.87) (layer "F.SilkS") (width 0.12) (fill none) (uuid "{_uuid()}"))')
    fp.fp_lines.append(f'(fp_rect (start -1.8 -1.8) (end 1.8 4.34) (layer "F.CrtYd") (width 0.05) (fill none) (uuid "{_uuid()}"))')
    return fp


def _make_led_0603(ref: str, value: str, at: tuple[float, float, float]) -> Footprint:
    """0603 LED"""
    fp = Footprint(
        library="LED_SMD:LED_0603_1608Metric",
        ref=ref, value=value, at=at, layer="F.Cu",
    )
    smd_layers = ["F.Cu", "F.Paste", "F.Mask"]
    fp.pads.append(Pad(
        number="1", pad_type="smd", shape="roundrect",
        at=(-0.75, 0, 0), size=(0.6, 0.5), layers=smd_layers,
    ))
    fp.pads.append(Pad(
        number="2", pad_type="smd", shape="roundrect",
        at=(0.75, 0, 0), size=(0.6, 0.5), layers=smd_layers,
    ))
    fp.fp_lines.append(f'(fp_rect (start -1.1 -0.5) (end 1.1 0.5) (layer "F.SilkS") (width 0.12) (fill none) (uuid "{_uuid()}"))')
    return fp


# ────────────────────────────────────────────
#  網路名稱 → 編號
# ────────────────────────────────────────────

PM_NETS = {
    "":             0,
    "3V3":          1,
    "GND":          2,
    "12V_INPUT":    3,
    "12V_OUTPUT":   4,
    "I2C_SDA":      5,
    "I2C_SCL":      6,
    "PWR_ALERT_N":  7,
}


def _assign(pad: Pad, net_name: str):
    pad.net_num = PM_NETS[net_name]
    pad.net_name = net_name


def generate_power_monitor_pcb(output_path: str = "output/power_monitor.kicad_pcb"):
    """生成 Smart Power Monitor 的完整 PCB 佈局"""

    footprints: list[Footprint] = []
    traces: list[Trace] = []
    vias: list[Via] = []

    # ── 板子尺寸: 35mm × 25mm ──
    board_w, board_h = 35.0, 25.0
    ox, oy = 10.0, 10.0

    # ── U2: INA226 (中央偏左) ──
    u2 = _make_msop10_fp("U2", "INA226", (ox + 14, oy + 12, 0))
    # INA226 pin mapping:
    # 1=A1, 2=A0, 3=ALERT, 4=SDA, 5=SCL
    # 6=VS, 7=GND, 8=VBUS, 9=IN-, 10=IN+
    pm_map = {
        "1": "GND",           # A1 = GND
        "2": "3V3",           # A0 = VCC → addr 0x41
        "3": "PWR_ALERT_N",
        "4": "I2C_SDA",
        "5": "I2C_SCL",
        "6": "3V3",           # VS
        "7": "GND",
        "8": "12V_OUTPUT",    # VBUS
        "9": "12V_OUTPUT",    # IN-
        "10": "12V_INPUT",    # IN+
    }
    for pad in u2.pads:
        net = pm_map.get(pad.number, "")
        if net:
            _assign(pad, net)
    footprints.append(u2)

    # ── Rs1: 分流電阻 0.002Ω (上方，電流路徑) ──
    rs1 = _make_r_2512("Rs1", "2mΩ", (ox + 14, oy + 5, 0))
    _assign(rs1.pads[0], "12V_INPUT")
    _assign(rs1.pads[1], "12V_OUTPUT")
    footprints.append(rs1)

    # ── J3: 12V 輸入接頭 (左上) ──
    j3 = _make_pin_header_1x02("J3", "12V_IN", (ox + 3, oy + 4, 0))
    _assign(j3.pads[0], "12V_INPUT")
    _assign(j3.pads[1], "GND")
    footprints.append(j3)

    # ── J4: 12V 輸出接頭 (右上) ──
    j4 = _make_pin_header_1x02("J4", "12V_OUT", (ox + 32, oy + 4, 0))
    _assign(j4.pads[0], "12V_OUTPUT")
    _assign(j4.pads[1], "GND")
    footprints.append(j4)

    # ── J5: BMC I2C 接頭 (左下) ──
    j5 = _make_pin_header_1x04("J5", "BMC_PWR", (ox + 3, oy + 14, 0))
    j5_nets = {"1": "I2C_SDA", "2": "I2C_SCL", "3": "PWR_ALERT_N", "4": "GND"}
    for pad in j5.pads:
        net = j5_nets.get(pad.number, "")
        if net:
            _assign(pad, net)
    footprints.append(j5)

    # ── R4: I2C SDA Pull-up ──
    r4 = _make_smd_resistor("R4", "4.7k", (ox + 9, oy + 14, 0))
    _assign(r4.pads[0], "3V3")
    _assign(r4.pads[1], "I2C_SDA")
    footprints.append(r4)

    # ── R5: I2C SCL Pull-up ──
    r5 = _make_smd_resistor("R5", "4.7k", (ox + 9, oy + 17, 0))
    _assign(r5.pads[0], "3V3")
    _assign(r5.pads[1], "I2C_SCL")
    footprints.append(r5)

    # ── R6: ALERT Pull-up ──
    r6 = _make_smd_resistor("R6", "10k", (ox + 22, oy + 17, 0))
    _assign(r6.pads[0], "3V3")
    _assign(r6.pads[1], "PWR_ALERT_N")
    footprints.append(r6)

    # ── R7: LED 限流電阻 ──
    r7 = _make_smd_resistor("R7", "1k", (ox + 26, oy + 17, 0))
    _assign(r7.pads[0], "PWR_ALERT_N")
    _assign(r7.pads[1], "GND")  # via LED
    footprints.append(r7)

    # ── D1: ALERT LED ──
    d1 = _make_led_0603("D1", "RED", (ox + 30, oy + 17, 0))
    _assign(d1.pads[0], "GND")  # simplify: LED in series with R7
    _assign(d1.pads[1], "GND")
    footprints.append(d1)

    # ── C5: VCC 100nF ──
    c5 = _make_smd_capacitor("C5", "100nF", (ox + 18, oy + 18, 0), "0402")
    _assign(c5.pads[0], "3V3")
    _assign(c5.pads[1], "GND")
    footprints.append(c5)

    # ── C6: VCC 10uF ──
    c6 = _make_smd_capacitor("C6", "10uF", (ox + 22, oy + 21, 0), "0805")
    _assign(c6.pads[0], "3V3")
    _assign(c6.pads[1], "GND")
    footprints.append(c6)

    # ── C7: 12V Bus 100nF (輸入端濾波) ──
    c7 = _make_smd_capacitor("C7", "100nF", (ox + 7, oy + 5, 0), "0603")
    _assign(c7.pads[0], "12V_INPUT")
    _assign(c7.pads[1], "GND")
    footprints.append(c7)

    # ── 走線 ──
    tw_signal = 0.2
    tw_power = 0.4
    tw_12v = 0.8  # 12V 大電流走線

    # 12V_INPUT: J3.1 → C7.1 → Rs1.1
    traces.append(Trace((ox + 3, oy + 4), (ox + 6.25, oy + 5), tw_12v, "F.Cu", PM_NETS["12V_INPUT"]))
    traces.append(Trace((ox + 7.75, oy + 5), (ox + 11.2, oy + 5), tw_12v, "F.Cu", PM_NETS["12V_INPUT"]))
    # 12V_OUTPUT: Rs1.2 → J4.1
    traces.append(Trace((ox + 16.8, oy + 5), (ox + 32, oy + 4), tw_12v, "F.Cu", PM_NETS["12V_OUTPUT"]))

    # 12V_INPUT → U2.IN+ (pin10, top-left)
    traces.append(Trace((ox + 11.2, oy + 5), (ox + 13, oy + 10.5), tw_signal, "F.Cu", PM_NETS["12V_INPUT"]))
    # 12V_OUTPUT → U2.IN- (pin9) and U2.VBUS (pin8)
    traces.append(Trace((ox + 16.8, oy + 5), (ox + 13.5, oy + 10.5), tw_signal, "F.Cu", PM_NETS["12V_OUTPUT"]))

    # I2C: J5.1 → R4.2 → U2.SDA
    traces.append(Trace((ox + 3, oy + 14), (ox + 9.48, oy + 14), tw_signal, "F.Cu", PM_NETS["I2C_SDA"]))
    traces.append(Trace((ox + 9.48, oy + 14), (ox + 13, oy + 13.5), tw_signal, "F.Cu", PM_NETS["I2C_SDA"]))
    # I2C: J5.2 → R5.2 → U2.SCL
    traces.append(Trace((ox + 3, oy + 16.54), (ox + 9.48, oy + 17), tw_signal, "F.Cu", PM_NETS["I2C_SCL"]))
    traces.append(Trace((ox + 9.48, oy + 17), (ox + 14, oy + 13.5), tw_signal, "F.Cu", PM_NETS["I2C_SCL"]))

    # 3V3 bus
    traces.append(Trace((ox + 8.52, oy + 14), (ox + 8.52, oy + 17), tw_power, "F.Cu", PM_NETS["3V3"]))
    traces.append(Trace((ox + 8.52, oy + 17), (ox + 17.52, oy + 18), tw_power, "F.Cu", PM_NETS["3V3"]))
    # U2.VS (pin6) → 3V3
    traces.append(Trace((ox + 15, oy + 10.5), (ox + 17.52, oy + 10.5), tw_power, "F.Cu", PM_NETS["3V3"]))
    traces.append(Trace((ox + 17.52, oy + 10.5), (ox + 17.52, oy + 18), tw_power, "F.Cu", PM_NETS["3V3"]))

    # GND vias
    vias.append(Via((ox + 18.48, oy + 18), 0.6, 0.3, PM_NETS["GND"]))
    vias.append(Via((ox + 22.9, oy + 21), 0.6, 0.3, PM_NETS["GND"]))
    vias.append(Via((ox + 7.75, oy + 5 + 1.0), 0.6, 0.3, PM_NETS["GND"]))
    vias.append(Via((ox + 14.5, oy + 10.5), 0.6, 0.3, PM_NETS["GND"]))  # U2.GND
    # GND bus on B.Cu
    traces.append(Trace((ox + 1, oy + 24), (ox + 34, oy + 24), tw_12v, "B.Cu", PM_NETS["GND"]))
    traces.append(Trace((ox + 18.48, oy + 18), (ox + 18.48, oy + 24), tw_power, "B.Cu", PM_NETS["GND"]))
    traces.append(Trace((ox + 14.5, oy + 10.5), (ox + 14.5, oy + 24), tw_power, "B.Cu", PM_NETS["GND"]))

    # ── 組合 PCB 文件 ──
    net_decls = "\n".join(f'  (net {num} "{name}")' for name, num in PM_NETS.items())
    fp_texts = "\n".join(fp.to_sexpr() for fp in footprints)
    trace_texts = "\n".join(t.to_sexpr() for t in traces)
    via_texts = "\n".join(v.to_sexpr() for v in vias)

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
  (paper "User" 55 45)
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

  (gr_text "Smart Power Monitor" (at {ox + board_w / 2} {oy + board_h - 2}) (layer "F.SilkS")
    (effects (font (size 1.2 1.2) (thickness 0.15)) (justify center))
    (uuid "{_uuid()}")
  )
  (gr_text "INA226 | 12V 30A" (at {ox + board_w / 2} {oy + 2}) (layer "F.SilkS")
    (effects (font (size 0.8 0.8) (thickness 0.12)) (justify center))
    (uuid "{_uuid()}")
  )

  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + 2.5} {oy + 2.5})
    (property "Reference" "H1" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + board_w - 2.5} {oy + 2.5})
    (property "Reference" "H2" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + 2.5} {oy + board_h - 2.5})
    (property "Reference" "H3" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uuid()}")
    (at {ox + board_w - 2.5} {oy + board_h - 2.5})
    (property "Reference" "H4" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (property "Value" "MH" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
    (pad "1" thru_hole circle (at 0 0) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))
  )

{fp_texts}

{trace_texts}

{via_texts}

  (zone (net {PM_NETS["GND"]}) (net_name "GND") (layer "B.Cu") (uuid "{_uuid()}")
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
    path = generate_power_monitor_pcb()
    print(f"✅ Power Monitor PCB: {path}")

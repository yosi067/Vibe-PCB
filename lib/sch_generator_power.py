"""
Schematic Generator — Smart Power Monitor Module
基於 INA226 的電源監控原理圖 (含設計註解)
"""

from __future__ import annotations
import uuid
from pathlib import Path


def _uuid() -> str:
    return str(uuid.uuid4())


def generate_power_monitor_schematic(output_path: str = "output/power_monitor.kicad_sch"):
    """生成 Smart Power Monitor 原理圖"""

    uid_root = _uuid()
    uid_sheet = _uuid()

    # ── 佈局座標 (mm) ──
    # U2: INA226 (中央)
    u2_x, u2_y = 152, 100
    # Rs1: 分流電阻 (U2 上方，電流路徑)
    rs1_x, rs1_y = 152, 55
    # J3: 12V 輸入 (左上)
    j3_x, j3_y = 50, 55
    # J4: 12V 輸出 (右上)
    j4_x, j4_y = 255, 55
    # J5: BMC I2C (左下)
    j5_x, j5_y = 35, 130
    # R4/R5: I2C Pull-up
    r4_x, r4_y = 82, 110
    r5_x, r5_y = 97, 110
    # R6: ALERT Pull-up
    r6_x, r6_y = 200, 130
    # R7 + D1: LED indicator
    r7_x, r7_y = 220, 130
    d1_x, d1_y = 240, 130
    # C5/C6: VCC decoupling
    c5_x, c5_y = 120, 170
    c6_x, c6_y = 140, 170
    # C7: Bus filtering
    c7_x, c7_y = 80, 55

    # ── 輔助函式 ──

    def _sym(lib_id, ref, value, x, y, pin_numbers, angle=0):
        pin_lines = "\n".join(
            f'    (pin "{pn}" (uuid "{_uuid()}"))'
            for pn in pin_numbers
        )
        return f"""  (symbol (lib_id "{lib_id}") (at {x} {y} {angle}) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid "{_uuid()}")
    (property "Reference" "{ref}" (at 0 -1.27 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{value}" (at 0 1.27 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project "power_monitor"
        (path "/{uid_sheet}" (reference "{ref}") (unit 1))
      )
    )
{pin_lines}
  )"""

    def _wire(x1, y1, x2, y2):
        return f'  (wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (uuid "{_uuid()}"))'

    def _label(name, x, y, angle=0):
        return f"""  (label "{name}" (at {x} {y} {angle}) (uuid "{_uuid()}")
    (effects (font (size 1.27 1.27)) (justify left))
  )"""

    def _pwr(lib_id, ref_tag, value, x, y, angle=0):
        return f"""  (symbol (lib_id "{lib_id}") (at {x} {y} {angle}) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid "{_uuid()}")
    (property "Reference" "{ref_tag}" (at 0 -2.54 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Value" "{value}" (at 0 2.54 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project "power_monitor"
        (path "/{uid_sheet}" (reference "{ref_tag}") (unit 1))
      )
    )
    (pin "1" (uuid "{_uuid()}"))
  )"""

    def _text(content, x, y, size=1.27, justify="left", italic=False, color=None):
        it = " italic" if italic else ""
        clr = ""
        if color:
            r, g, b = color
            clr = f" (color {r} {g} {b} 1)"
        return f"""  (text "{content}" (at {x} {y} 0)
    (effects (font (size {size} {size}){it}){clr} (justify {justify}))
    (uuid "{_uuid()}")
  )"""

    def _rect(x1, y1, x2, y2, dash=True, color=(80, 80, 80)):
        r, g, b = color
        stype = "dash" if dash else "default"
        return f"""  (rectangle (start {x1} {y1}) (end {x2} {y2})
    (stroke (width 0.1524) (type {stype}) (color {r} {g} {b} 1))
    (fill (type none))
    (uuid "{_uuid()}")
  )"""

    # ══════════════════════════════════════════════
    # 元件
    # ══════════════════════════════════════════════
    syms = []
    syms.append(_sym("Interface_Current:INA226", "U2", "INA226",
                      u2_x, u2_y,
                      ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]))
    syms.append(_sym("Device:R", "Rs1", "2mΩ", rs1_x, rs1_y, ["1", "2"], angle=90))
    syms.append(_sym("Connector:Conn_01x02_Male", "J3", "12V_IN",
                      j3_x, j3_y, ["1", "2"]))
    syms.append(_sym("Connector:Conn_01x02_Male", "J4", "12V_OUT",
                      j4_x, j4_y, ["1", "2"]))
    syms.append(_sym("Connector:Conn_01x04_Male", "J5", "BMC_PWR",
                      j5_x, j5_y, ["1", "2", "3", "4"]))
    syms.append(_sym("Device:R", "R4", "4.7k", r4_x, r4_y, ["1", "2"]))
    syms.append(_sym("Device:R", "R5", "4.7k", r5_x, r5_y, ["1", "2"]))
    syms.append(_sym("Device:R", "R6", "10k", r6_x, r6_y, ["1", "2"]))
    syms.append(_sym("Device:R", "R7", "1k", r7_x, r7_y, ["1", "2"]))
    syms.append(_sym("Device:LED", "D1", "RED", d1_x, d1_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C5", "100nF", c5_x, c5_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C6", "10uF", c6_x, c6_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C7", "100nF", c7_x, c7_y, ["1", "2"]))

    # ══════════════════════════════════════════════
    # 電源符號
    # ══════════════════════════════════════════════
    pwrs = []
    pwrs.append(_pwr("power:+3V3", "#PWR01", "+3V3", r4_x, r4_y - 12.7))
    pwrs.append(_pwr("power:+3V3", "#PWR02", "+3V3", r5_x, r5_y - 12.7))
    pwrs.append(_pwr("power:+3V3", "#PWR03", "+3V3", u2_x, u2_y - 15.24))
    pwrs.append(_pwr("power:+3V3", "#PWR04", "+3V3", c5_x, c5_y - 8.89))
    pwrs.append(_pwr("power:+3V3", "#PWR05", "+3V3", c6_x, c6_y - 8.89))
    pwrs.append(_pwr("power:+3V3", "#PWR06", "+3V3", r6_x, r6_y - 12.7))
    pwrs.append(_pwr("power:GND", "#PWR07", "GND", u2_x, u2_y + 15.24, 0))
    pwrs.append(_pwr("power:GND", "#PWR08", "GND", c5_x, c5_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR09", "GND", c6_x, c6_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR10", "GND", j3_x + 3.81, j3_y + 5.08, 0))
    pwrs.append(_pwr("power:GND", "#PWR11", "GND", j4_x + 3.81, j4_y + 5.08, 0))
    pwrs.append(_pwr("power:GND", "#PWR12", "GND", d1_x, d1_y + 7.62, 0))
    pwrs.append(_pwr("power:GND", "#PWR13", "GND", c7_x, c7_y + 8.89, 0))

    # ══════════════════════════════════════════════
    # 標籤
    # ══════════════════════════════════════════════
    lbls = []
    lbls.append(_label("I2C_SDA", u2_x - 15, u2_y - 3.81, 0))
    lbls.append(_label("I2C_SCL", u2_x - 15, u2_y - 1.27, 0))
    lbls.append(_label("PWR_ALERT_N", u2_x + 15, u2_y + 1.27, 0))
    lbls.append(_label("12V_INPUT", rs1_x - 10, rs1_y, 0))
    lbls.append(_label("12V_OUTPUT", rs1_x + 6, rs1_y, 0))
    lbls.append(_label("I2C_SDA", j5_x + 7, j5_y - 2.54, 0))
    lbls.append(_label("I2C_SCL", j5_x + 7, j5_y, 0))
    lbls.append(_label("PWR_ALERT_N", j5_x + 7, j5_y + 2.54, 0))
    lbls.append(_label("I2C_SDA", r4_x - 2, r4_y + 5, 0))
    lbls.append(_label("I2C_SCL", r5_x - 2, r5_y + 5, 0))
    lbls.append(_label("12V_INPUT", j3_x + 7, j3_y - 2.54, 0))
    lbls.append(_label("12V_OUTPUT", j4_x + 7, j4_y - 2.54, 0))
    lbls.append(_label("PWR_ALERT_N", r6_x - 3, r6_y + 5, 0))

    # ══════════════════════════════════════════════
    # 接線
    # ══════════════════════════════════════════════
    wires = []
    # R4/R5 pull-up → 3V3
    wires.append(_wire(r4_x, r4_y - 3.81, r4_x, r4_y - 12.7))
    wires.append(_wire(r5_x, r5_y - 3.81, r5_x, r5_y - 12.7))
    wires.append(_wire(r4_x, r4_y + 3.81, r4_x, r4_y + 5))
    wires.append(_wire(r5_x, r5_y + 3.81, r5_x, r5_y + 5))
    # R6 pull-up → 3V3
    wires.append(_wire(r6_x, r6_y - 3.81, r6_x, r6_y - 12.7))
    wires.append(_wire(r6_x, r6_y + 3.81, r6_x, r6_y + 5))
    # R7 → D1 → GND
    wires.append(_wire(r7_x, r7_y + 3.81, d1_x, d1_y - 3.81))
    wires.append(_wire(d1_x, d1_y + 3.81, d1_x, d1_y + 7.62))
    # U2 power
    wires.append(_wire(u2_x, u2_y - 15.24, u2_x, u2_y - 12.7))
    wires.append(_wire(u2_x, u2_y + 15.24, u2_x, u2_y + 12.7))
    # Caps
    wires.append(_wire(c5_x, c5_y - 3.81, c5_x, c5_y - 8.89))
    wires.append(_wire(c6_x, c6_y - 3.81, c6_x, c6_y - 8.89))
    wires.append(_wire(c5_x, c5_y + 3.81, c5_x, c5_y + 8.89))
    wires.append(_wire(c6_x, c6_y + 3.81, c6_x, c6_y + 8.89))
    wires.append(_wire(c7_x, c7_y - 3.81, c7_x, c7_y - 8.89))
    wires.append(_wire(c7_x, c7_y + 3.81, c7_x, c7_y + 8.89))
    # 12V bus path: J3 → C7 → Rs1 → J4
    wires.append(_wire(j3_x + 3.81, j3_y - 2.54, c7_x, c7_y - 3.81))
    wires.append(_wire(c7_x, c7_y - 3.81, rs1_x - 6, rs1_y))
    wires.append(_wire(rs1_x + 6, rs1_y, j4_x - 8, j4_y - 2.54))

    # ══════════════════════════════════════════════
    # 設計註解
    # ══════════════════════════════════════════════
    annotations = []

    # 標題
    annotations.append(_text(
        "Smart Power Monitor  -  High Precision Current/Voltage/Power Sensing",
        152, 18, size=3.0, justify="center", color=(255, 123, 114)))
    annotations.append(_text(
        "Vibe-PCB v0.1  |  INA226 MSOP-10  |  12V Bus @ 30A  |  I2C Addr: 0x41",
        152, 24, size=1.5, justify="center", italic=True, color=(139, 148, 158)))

    # ── 區塊 A: 12V 電流路徑 ──
    annotations.append(_rect(35, 38, 270, 72, color=(255, 123, 114)))
    annotations.append(_text(
        "A. 12V High-Current Path (30A Max)",
        37, 37, size=1.5, color=(255, 123, 114)))
    annotations.append(_text(
        "Rs1 = 0.002 ohm (2m ohm) 2512 package, rated 2W.",
        37, 74, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "P = I^2 x R = 30^2 x 0.002 = 1.8W < 2W (SAFE).",
        37, 77, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "PCB trace width: 2mm min for 30A (2oz copper).",
        37, 80, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Kelvin connection recommended for accurate sensing.",
        37, 83, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 B: INA226 IC ──
    annotations.append(_rect(127, 78, 180, 130, color=(88, 166, 255)))
    annotations.append(_text(
        "B. INA226 - Current/Power Monitor IC",
        129, 77, size=1.5, color=(88, 166, 255)))
    annotations.append(_text(
        "TI INA226: 16-bit ADC, 0-36V bus, +/-80mV shunt.",
        129, 132, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Resolution: 2.5uV LSB (shunt), 1.25mV LSB (bus).",
        129, 135, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Built-in power register: P = V_bus x I_shunt.",
        129, 138, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Alert pin: over-current/under-voltage programmable.",
        129, 141, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "A0=VCC, A1=GND -> I2C addr = 0x41 (no conflict w/ EMC2103 @ 0x2E).",
        129, 144, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 C: I2C Bus ──
    annotations.append(_rect(20, 95, 125, 150, color=(63, 185, 80)))
    annotations.append(_text(
        "C. I2C Bus + BMC Interface",
        22, 94, size=1.5, color=(63, 185, 80)))
    annotations.append(_text(
        "Shared I2C bus with Fan Controller module.",
        22, 152, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "R4/R5 = 4.7k pull-up (may be omitted if already",
        22, 155, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "present on fan controller board).",
        22, 158, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "INA226 supports up to 2.94MHz I2C (Fast Mode+).",
        22, 161, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 D: Alert + LED ──
    annotations.append(_rect(185, 115, 260, 150, color=(210, 153, 34)))
    annotations.append(_text(
        "D. Over-Current Alert + LED Indicator",
        187, 114, size=1.5, color=(210, 153, 34)))
    annotations.append(_text(
        "R6 = 10k pull-up for open-drain ALERT output.",
        187, 152, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "D1 (RED LED) lights when ALERT is asserted (low).",
        187, 155, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "BMC can read alert status via I2C register.",
        187, 158, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 E: Decoupling ──
    annotations.append(_rect(107, 155, 155, 190, color=(163, 113, 247)))
    annotations.append(_text(
        "E. 3.3V Decoupling",
        109, 154, size=1.5, color=(163, 113, 247)))
    annotations.append(_text(
        "C5 = 100nF + C6 = 10uF: close to U2 VS pin.",
        109, 182, size=1.0, italic=True, color=(139, 148, 158)))

    # ══════════════════════════════════════════════
    # 組合
    # ══════════════════════════════════════════════
    all_content = "\n".join(syms + pwrs + wires + lbls + annotations)

    sch_content = f"""(kicad_sch
  (version 20231120)
  (generator "Vibe-PCB-Orchestrator")
  (generator_version "0.1")
  (uuid "{uid_root}")
  (paper "User" 310 210)
  (lib_symbols
    (symbol "Interface_Current:INA226" (in_bom yes) (on_board yes)
      (property "Reference" "U" (at -7.62 13.97 0) (effects (font (size 1.27 1.27))))
      (property "Value" "INA226" (at 7.62 13.97 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_SO:MSOP-10_3x3mm_P0.5mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "INA226_0_1"
        (rectangle (start -10.16 12.7) (end 10.16 -12.7)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "INA226_1_1"
        (pin input line (at -12.7 -5.08 0) (length 2.54) (name "A1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -7.62 0) (length 2.54) (name "A0" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin open_collector line (at 12.7 2.54 180) (length 2.54) (name "ALERT" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 7.62 0) (length 2.54) (name "SDA" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 5.08 0) (length 2.54) (name "SCL" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 15.24 270) (length 2.54) (name "VS" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -15.24 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 7.62 180) (length 2.54) (name "VBUS" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 5.08 180) (length 2.54) (name "IN-" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 2.54 180) (length 2.54) (name "IN+" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Connector:Conn_01x04_Male" (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x04" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x04_Male_1_1"
        (polyline (pts (xy 1.27 -5.08) (xy 0.8636 -5.08)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 -2.54) (xy 0.8636 -2.54)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 0) (xy 0.8636 0)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 2.54) (xy 0.8636 2.54)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (rectangle (start 0.8636 -5.334) (end 0 -4.826) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (rectangle (start 0.8636 -2.794) (end 0 -2.286) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (rectangle (start 0.8636 -0.254) (end 0 0.254) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (rectangle (start 0.8636 2.286) (end 0 2.794) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (pin passive line (at 3.81 2.54 180) (length 2.54) (name "Pin_1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "Pin_2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 -2.54 180) (length 2.54) (name "Pin_3" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 -5.08 180) (length 2.54) (name "Pin_4" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Connector:Conn_01x02_Male" (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x02" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x02_Male_1_1"
        (polyline (pts (xy 1.27 -2.54) (xy 0.8636 -2.54)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 0) (xy 0.8636 0)) (stroke (width 0.1524) (type default)) (fill (type none)))
        (rectangle (start 0.8636 -2.794) (end 0 -2.286) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (rectangle (start 0.8636 -0.254) (end 0 0.254) (stroke (width 0.1524) (type default)) (fill (type outline)))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "Pin_1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 -2.54 180) (length 2.54) (name "Pin_2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:R" (in_bom yes) (on_board yes)
      (property "Reference" "R" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (at 0 0 90) (effects (font (size 1.27 1.27))))
      (symbol "R_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54)
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
      )
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:C" (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "C" (at 0 0 90) (effects (font (size 1.27 1.27))))
      (symbol "C_0_1"
        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
      )
      (symbol "C_1_1"
        (pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:LED" (in_bom yes) (on_board yes)
      (property "Reference" "D" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "LED" (at 0 0 90) (effects (font (size 1.27 1.27))))
      (symbol "LED_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -1.27 0) (xy 1.27 0)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) (xy 1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "LED_1_1"
        (pin passive line (at 0 3.81 270) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "power:+3V3" (power) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "+3V3" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
      (symbol "+3V3_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "+3V3_1_1"
        (pin power_in line (at 0 0 90) (length 0) (name "+3V3" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "power:GND" (power) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -6.35 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "GND" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (symbol "GND_0_1"
        (polyline
          (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27))
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "GND_1_1"
        (pin power_in line (at 0 0 270) (length 0) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      )
    )
  )

{all_content}

  (sheet_instances
    (path "/{uid_sheet}" (page "1"))
  )
)
"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sch_content, encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    path = generate_power_monitor_schematic()
    print(f"OK: {path}")

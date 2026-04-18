"""
Schematic Generator — 從電路定義產出 KiCad .kicad_sch 原理圖
(重新設計: 寬版佈局 + 豐富設計註解)
"""

from __future__ import annotations

import uuid
from pathlib import Path


def _uuid() -> str:
    return str(uuid.uuid4())


def generate_fan_controller_schematic(output_path: str = "output/fan_controller.kicad_sch"):
    """生成 AI Server Fan Controller 的原理圖 (寬版佈局 + 豐富註解)"""

    uid_root = _uuid()
    uid_sheet = _uuid()

    # ══════════════════════════════════════════════════════
    # 佈局設計 — 5 個功能區塊, 分散於 300×200mm 自訂頁面
    #
    #  ┌─────────────────────────────────────────────────┐
    #  │  [TITLE]  AI Server Fan Controller              │
    #  ├──────┬───────────┬───────────┬──────────────────┤
    #  │      │  R1 R2    │           │                  │
    #  │  J2  │  Pull-up  │    U1     │       J1         │
    #  │ BMC  │  +R3 addr │  EMC2103  │      FAN         │
    #  │      │           │           │                  │
    #  ├──────┴─────┬─────┴─────┬─────┴──────────────────┤
    #  │  C1+C2     │           │  C3+C4                 │
    #  │  3V3 decap │           │  12V decap             │
    #  └────────────┴───────────┴────────────────────────┘
    # ══════════════════════════════════════════════════════

    # ── 區塊中心座標 (mm) — 大間距佈局 ──

    # U1: EMC2103 (中央核心)
    u1_x, u1_y = 152, 100

    # J2: BMC I2C Connector (最左側)
    j2_x, j2_y = 35, 100

    # R1, R2: I2C Pull-up (左中), R3: ADDR_SEL
    r1_x, r1_y = 82, 75
    r2_x, r2_y = 97, 75
    r3_x, r3_y = 112, 120

    # J1: Fan 4-pin Connector (最右側)
    j1_x, j1_y = 265, 100

    # C1/C2: 3.3V Decoupling (下方左)
    c1_x, c1_y = 120, 170
    c2_x, c2_y = 140, 170

    # C3/C4: 12V Decoupling (下方右)
    c3_x, c3_y = 230, 170
    c4_x, c4_y = 250, 170

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
      (project "fan_controller"
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
      (project "fan_controller"
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
    # 元件實例
    # ══════════════════════════════════════════════
    syms = []
    syms.append(_sym("Sensor_Temperature:EMC2103", "U1", "EMC2103",
                      u1_x, u1_y,
                      ["4", "5", "3", "6", "7", "8", "9", "2", "1", "21"]))
    syms.append(_sym("Connector:Conn_01x04_Male", "J1", "FAN_4PIN",
                      j1_x, j1_y, ["1", "2", "3", "4"]))
    syms.append(_sym("Connector:Conn_01x04_Male", "J2", "BMC_I2C",
                      j2_x, j2_y, ["1", "2", "3", "4"]))
    syms.append(_sym("Device:R", "R1", "4.7k", r1_x, r1_y, ["1", "2"]))
    syms.append(_sym("Device:R", "R2", "4.7k", r2_x, r2_y, ["1", "2"]))
    syms.append(_sym("Device:R", "R3", "10k", r3_x, r3_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C1", "100nF", c1_x, c1_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C2", "10uF", c2_x, c2_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C3", "100nF", c3_x, c3_y, ["1", "2"]))
    syms.append(_sym("Device:C", "C4", "100uF", c4_x, c4_y, ["1", "2"]))

    # ══════════════════════════════════════════════
    # 電源符號
    # ══════════════════════════════════════════════
    pwrs = []
    # 3V3
    pwrs.append(_pwr("power:+3V3", "#PWR01", "+3V3", r1_x, r1_y - 12.7))
    pwrs.append(_pwr("power:+3V3", "#PWR02", "+3V3", r2_x, r2_y - 12.7))
    pwrs.append(_pwr("power:+3V3", "#PWR03", "+3V3", u1_x, u1_y - 15.24))
    pwrs.append(_pwr("power:+3V3", "#PWR04", "+3V3", c1_x, c1_y - 8.89))
    pwrs.append(_pwr("power:+3V3", "#PWR05", "+3V3", c2_x, c2_y - 8.89))
    # 12V
    pwrs.append(_pwr("power:+12V", "#PWR06", "+12V", j1_x + 3.81, j1_y - 5.08))
    pwrs.append(_pwr("power:+12V", "#PWR07", "+12V", c3_x, c3_y - 8.89))
    pwrs.append(_pwr("power:+12V", "#PWR08", "+12V", c4_x, c4_y - 8.89))
    # GND
    pwrs.append(_pwr("power:GND", "#PWR09", "GND", u1_x, u1_y + 15.24, 0))
    pwrs.append(_pwr("power:GND", "#PWR10", "GND", c1_x, c1_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR11", "GND", c2_x, c2_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR12", "GND", c3_x, c3_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR13", "GND", c4_x, c4_y + 8.89, 0))
    pwrs.append(_pwr("power:GND", "#PWR14", "GND", j1_x + 3.81, j1_y + 7.62, 0))
    pwrs.append(_pwr("power:GND", "#PWR15", "GND", r3_x, r3_y + 7.62, 0))

    # ══════════════════════════════════════════════
    # 網路標籤
    # ══════════════════════════════════════════════
    lbls = []
    # U1 左側 → 往 J2 / Pull-up
    lbls.append(_label("I2C_SDA", u1_x - 15, u1_y - 3.81, 0))
    lbls.append(_label("I2C_SCL", u1_x - 15, u1_y - 1.27, 0))
    lbls.append(_label("SMBALERT_N", u1_x - 15, u1_y + 1.27, 0))
    # U1 右側 → 往 J1
    lbls.append(_label("FAN_PWM", u1_x + 15, u1_y - 3.81, 0))
    lbls.append(_label("FAN_TACH", u1_x + 15, u1_y - 1.27, 0))
    # U1 左下 → ADDR_SEL
    lbls.append(_label("ADDR_SEL", u1_x - 15, u1_y + 3.81, 0))
    # J2 右側
    lbls.append(_label("I2C_SDA", j2_x + 7, j2_y - 2.54, 0))
    lbls.append(_label("I2C_SCL", j2_x + 7, j2_y, 0))
    lbls.append(_label("SMBALERT_N", j2_x + 7, j2_y + 2.54, 0))
    # J1 左側
    lbls.append(_label("FAN_PWM", j1_x - 12, j1_y - 2.54, 0))
    lbls.append(_label("FAN_TACH", j1_x - 12, j1_y, 0))
    # R1, R2 下方
    lbls.append(_label("I2C_SDA", r1_x - 2, r1_y + 5, 0))
    lbls.append(_label("I2C_SCL", r2_x - 2, r2_y + 5, 0))
    # R3 上方
    lbls.append(_label("ADDR_SEL", r3_x - 3, r3_y - 5, 0))

    # ══════════════════════════════════════════════
    # 接線
    # ══════════════════════════════════════════════
    wires = []
    # R1, R2 top → +3V3
    wires.append(_wire(r1_x, r1_y - 3.81, r1_x, r1_y - 12.7))
    wires.append(_wire(r2_x, r2_y - 3.81, r2_x, r2_y - 12.7))
    # R1, R2 bottom → label
    wires.append(_wire(r1_x, r1_y + 3.81, r1_x, r1_y + 5))
    wires.append(_wire(r2_x, r2_y + 3.81, r2_x, r2_y + 5))
    # R3 top → ADDR_SEL label
    wires.append(_wire(r3_x, r3_y - 3.81, r3_x, r3_y - 5))
    # R3 bottom → GND
    wires.append(_wire(r3_x, r3_y + 3.81, r3_x, r3_y + 7.62))
    # U1 VCC → +3V3
    wires.append(_wire(u1_x, u1_y - 15.24, u1_x, u1_y - 12.7))
    # U1 GND → GND
    wires.append(_wire(u1_x, u1_y + 15.24, u1_x, u1_y + 12.7))
    # C1, C2 → 3V3 / GND
    wires.append(_wire(c1_x, c1_y - 3.81, c1_x, c1_y - 8.89))
    wires.append(_wire(c2_x, c2_y - 3.81, c2_x, c2_y - 8.89))
    wires.append(_wire(c1_x, c1_y + 3.81, c1_x, c1_y + 8.89))
    wires.append(_wire(c2_x, c2_y + 3.81, c2_x, c2_y + 8.89))
    # C3, C4 → 12V / GND
    wires.append(_wire(c3_x, c3_y - 3.81, c3_x, c3_y - 8.89))
    wires.append(_wire(c4_x, c4_y - 3.81, c4_x, c4_y - 8.89))
    wires.append(_wire(c3_x, c3_y + 3.81, c3_x, c3_y + 8.89))
    wires.append(_wire(c4_x, c4_y + 3.81, c4_x, c4_y + 8.89))

    # ══════════════════════════════════════════════
    # 設計註解 + 區塊框線
    # ══════════════════════════════════════════════
    annotations = []

    # ── 總標題 ──
    annotations.append(_text(
        "AI Server Fan Controller  -  BMC PWM Temperature Control Module",
        152, 18, size=3.0, justify="center", color=(88, 166, 255)))
    annotations.append(_text(
        "Vibe-PCB Orchestrator v0.1  |  EMC2103 QFN-20  |  3.3V / 12V Dual Domain",
        152, 24, size=1.5, justify="center", italic=True, color=(139, 148, 158)))

    # ── 區塊 A: BMC I2C 介面 (J2) ──
    annotations.append(_rect(20, 85, 55, 120, color=(88, 166, 255)))
    annotations.append(_text(
        "A. BMC I2C Interface",
        22, 84, size=1.5, color=(88, 166, 255)))
    annotations.append(_text(
        "Pin1: +3.3V (BMC side power)",
        22, 122, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Pin2: SDA  Pin3: SCL",
        22, 125, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Pin4: SMBALERT# (open-drain, active low)",
        22, 128, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "BMC communicates via I2C to read temperature",
        22, 131, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "and configure fan speed target/thresholds.",
        22, 134, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 B: I2C Pull-up + ADDR_SEL ──
    annotations.append(_rect(68, 55, 125, 140, color=(63, 185, 80)))
    annotations.append(_text(
        "B. I2C Pull-ups + Address Select",
        70, 54, size=1.5, color=(63, 185, 80)))
    annotations.append(_text(
        "R1/R2 = 4.7k: Standard I2C pull-up for 100kHz.",
        70, 142, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Too low -> high power; too high -> slow edges.",
        70, 145, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "4.7k is optimal for short bus (<30cm) at 3.3V.",
        70, 148, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "R3 = 10k pull-down: sets EMC2103 I2C address",
        70, 151, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "to 0x2E (default). Float=0x2C, VCC=0x2D.",
        70, 154, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 C: EMC2103 核心 IC ──
    annotations.append(_rect(127, 70, 180, 130, color=(210, 153, 34)))
    annotations.append(_text(
        "C. EMC2103 - Fan Controller IC",
        129, 69, size=1.5, color=(210, 153, 34)))
    annotations.append(_text(
        "Microchip EMC2103: I2C fan speed controller",
        129, 132, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "with internal temp sensor + external diode input.",
        129, 135, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Auto RPM control with closed-loop PID algorithm.",
        129, 138, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "VCC + VDDIO both at 3.3V (same rail).",
        129, 141, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "EP (exposed pad) -> GND for thermal dissipation.",
        129, 144, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 D: Fan 連接器 (J1) ──
    annotations.append(_rect(245, 85, 290, 120, color=(255, 123, 114)))
    annotations.append(_text(
        "D. 4-Pin PWM Fan Connector",
        247, 84, size=1.5, color=(255, 123, 114)))
    annotations.append(_text(
        "Intel 4-wire fan standard:",
        247, 122, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Pin1: GND   Pin2: +12V (fan motor)",
        247, 125, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Pin3: TACH (2 pulses/rev, open-drain)",
        247, 128, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Pin4: PWM (25kHz target, 3.3V logic)",
        247, 131, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "12V rail is separate from 3.3V logic.",
        247, 134, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "EMC2103 drives PWM directly (push-pull).",
        247, 137, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 E: 3.3V 去耦 ──
    annotations.append(_rect(107, 155, 155, 190, color=(163, 113, 247)))
    annotations.append(_text(
        "E. 3.3V Decoupling",
        109, 154, size=1.5, color=(163, 113, 247)))
    annotations.append(_text(
        "C1 = 100nF: High-freq bypass, close to U1 VCC.",
        109, 182, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "C2 = 10uF: Bulk capacitance for transient loads.",
        109, 185, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Both MLCC, placed within 5mm of IC power pins.",
        109, 188, size=1.0, italic=True, color=(139, 148, 158)))

    # ── 區塊 F: 12V 去耦 ──
    annotations.append(_rect(217, 155, 265, 190, color=(255, 159, 28)))
    annotations.append(_text(
        "F. 12V Decoupling",
        219, 154, size=1.5, color=(255, 159, 28)))
    annotations.append(_text(
        "C3 = 100nF: Suppress high-freq noise from fan.",
        219, 182, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "C4 = 100uF: Handle fan inrush current (~2A peak).",
        219, 185, size=1.0, italic=True, color=(139, 148, 158)))
    annotations.append(_text(
        "Place close to J1 to shorten current loop.",
        219, 188, size=1.0, italic=True, color=(139, 148, 158)))

    # ══════════════════════════════════════════════
    # 組合全部內容
    # ══════════════════════════════════════════════
    all_content = "\n".join(syms + pwrs + wires + lbls + annotations)

    sch_content = f"""(kicad_sch
  (version 20231120)
  (generator "Vibe-PCB-Orchestrator")
  (generator_version "0.1")
  (uuid "{uid_root}")
  (paper "User" 310 210)
  (lib_symbols
    (symbol "Sensor_Temperature:EMC2103" (in_bom yes) (on_board yes)
      (property "Reference" "U" (at -7.62 13.97 0) (effects (font (size 1.27 1.27))))
      (property "Value" "EMC2103" (at 7.62 13.97 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.65x2.65mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "EMC2103_0_1"
        (rectangle (start -10.16 12.7) (end 10.16 -12.7)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "EMC2103_1_1"
        (pin bidirectional line (at -12.7 7.62 0) (length 2.54) (name "SDA" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 5.08 0) (length 2.54) (name "SCL" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin open_collector line (at -12.7 2.54 0) (length 2.54) (name "SMBALERT#" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -2.54 0) (length 2.54) (name "ADDR_SEL" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 15.24 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 2.54 15.24 270) (length 2.54) (name "VDDIO" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -15.24 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin output line (at 12.7 7.62 180) (length 2.54) (name "FAN_PWM" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 5.08 180) (length 2.54) (name "FAN_TACH" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -15.24 90) (length 2.54) (name "EP" (effects (font (size 1.27 1.27)))) (number "21" (effects (font (size 1.27 1.27)))))
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
    (symbol "power:+12V" (power) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "+12V" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
      (symbol "+12V_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "+12V_1_1"
        (pin power_in line (at 0 0 90) (length 0) (name "+12V" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
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
    path = generate_fan_controller_schematic()
    print(f"OK: {path}")

"""
AI Server Fan Controller - BMC 專用風扇 PWM 控制與溫控模組
使用 EMC2103 溫控晶片，支援 I2C/SMBus 介面
電壓域：12V (Fan Power) / 3.3V (Logic VCC)

所有零件使用 tool=SKIDL 內建定義，不依賴外部 KiCad 符號庫。
"""

from skidl import Part, Pin, Net, POWER, TEMPLATE, SKIDL, generate_netlist, reset


# ── 零件模板工廠（tool=SKIDL，不需要 KiCad 庫）──

def _make_emc2103():
    """EMC2103 風扇控制器 / 溫度感測 IC (QFN-20) 模板"""
    p = Part(name="EMC2103", dest=TEMPLATE, tool=SKIDL,
             footprint="Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.65x2.65mm")
    p += Pin(num=1,  name="FAN_TACH", func=Pin.types.INPUT)
    p += Pin(num=2,  name="FAN_PWM",  func=Pin.types.OUTPUT)
    p += Pin(num=3,  name="SMBALERT", func=Pin.types.OPENCOLL)
    p += Pin(num=4,  name="SDA",      func=Pin.types.BIDIR)
    p += Pin(num=5,  name="SCL",      func=Pin.types.INPUT)
    p += Pin(num=6,  name="ADDR_SEL", func=Pin.types.INPUT)
    p += Pin(num=7,  name="VCC",      func=Pin.types.PWRIN)
    p += Pin(num=8,  name="VDDIO",    func=Pin.types.PWRIN)
    p += Pin(num=9,  name="GND",      func=Pin.types.PWRIN)
    p += Pin(num=21, name="EP",       func=Pin.types.PASSIVE)
    return p


def _make_conn_1x04():
    """4-Pin 直插接頭模板"""
    p = Part(name="Conn_01x04_Male", dest=TEMPLATE, tool=SKIDL,
             footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical")
    p += Pin(num=1, name="P1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="P2", func=Pin.types.PASSIVE)
    p += Pin(num=3, name="P3", func=Pin.types.PASSIVE)
    p += Pin(num=4, name="P4", func=Pin.types.PASSIVE)
    return p


def _make_resistor():
    """通用電阻模板"""
    p = Part(name="R", dest=TEMPLATE, tool=SKIDL)
    p += Pin(num=1, name="p1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="p2", func=Pin.types.PASSIVE)
    return p


def _make_capacitor():
    """通用電容模板"""
    p = Part(name="C", dest=TEMPLATE, tool=SKIDL)
    p += Pin(num=1, name="p1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="p2", func=Pin.types.PASSIVE)
    return p


def gen_fan_controller():
    """生成 AI Server 風扇控制器電路的 Netlist。

    電路包含：
    - EMC2103 溫控晶片 (QFN-20)
    - 4-Pin PWM 風扇接頭
    - I2C 上拉電阻 (供 BMC 連接)
    - 去耦濾波電容
    - 12V 電源濾波
    """

    # 清除先前執行殘留的電路狀態
    reset()

    # 建立零件模板
    EMC2103 = _make_emc2103()
    CONN4 = _make_conn_1x04()
    RES = _make_resistor()
    CAP = _make_capacitor()

    # ── 電壓網路定義 ──
    vcc = Net("3V3")
    vcc.drive = POWER
    gnd = Net("GND")
    gnd.drive = POWER
    v_fan = Net("12V")
    v_fan.drive = POWER

    # I2C 匯流排（連往 BMC）
    sda = Net("I2C_SDA")
    scl = Net("I2C_SCL")

    # 風扇控制訊號
    fan_pwm = Net("FAN_PWM")
    fan_tach = Net("FAN_TACH")

    # SMBALERT# 中斷輸出（通知 BMC 過溫）
    smbalert = Net("SMBALERT_N")

    # ── 1. EMC2103 溫控晶片 ──
    emc = EMC2103()
    emc.ref = "U1"
    emc["VCC"] += vcc
    emc["VDDIO"] += vcc
    emc["GND"] += gnd
    emc["EP"] += gnd         # Exposed pad 接地
    emc["ADDR_SEL"] += gnd   # I2C 地址選擇：接地 = 0x2E
    emc["SDA"] += sda
    emc["SCL"] += scl
    emc["SMBALERT"] += smbalert
    emc["FAN_PWM"] += fan_pwm
    emc["FAN_TACH"] += fan_tach

    # ── 2. 4-Pin PWM 風扇接頭 ──
    fan_conn = CONN4()
    fan_conn.ref = "J1"
    fan_conn[1] += gnd       # Pin 1: GND
    fan_conn[2] += v_fan     # Pin 2: 12V 風扇供電
    fan_conn[3] += fan_tach  # Pin 3: Tach 反饋訊號
    fan_conn[4] += fan_pwm   # Pin 4: PWM 控制訊號

    # ── 3. I2C 上拉電阻 (4.7kΩ to 3V3) ──
    r_sda = RES(value="4.7k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_sda.ref = "R1"
    r_sda[1] += vcc
    r_sda[2] += sda

    r_scl = RES(value="4.7k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_scl.ref = "R2"
    r_scl[1] += vcc
    r_scl[2] += scl

    # ── 4. SMBALERT# 上拉電阻 ──
    r_alert = RES(value="10k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_alert.ref = "R3"
    r_alert[1] += vcc
    r_alert[2] += smbalert

    # ── 5. 去耦電容 (VCC 濾波) ──
    c_vcc_100n = CAP(value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_vcc_100n.ref = "C1"
    c_vcc_100n[1] += vcc
    c_vcc_100n[2] += gnd

    c_vcc_10u = CAP(value="10uF", footprint="Capacitor_SMD:C_0805_2012Metric")
    c_vcc_10u.ref = "C2"
    c_vcc_10u[1] += vcc
    c_vcc_10u[2] += gnd

    # ── 6. 12V 風扇電源濾波 ──
    c_fan_100n = CAP(value="100nF", footprint="Capacitor_SMD:C_0603_1608Metric")
    c_fan_100n.ref = "C3"
    c_fan_100n[1] += v_fan
    c_fan_100n[2] += gnd

    c_fan_100u = CAP(value="100uF", footprint="Capacitor_SMD:C_1206_3216Metric")
    c_fan_100u.ref = "C4"
    c_fan_100u[1] += v_fan
    c_fan_100u[2] += gnd

    # ── 7. BMC 連接器 (I2C + SMBALERT 輸出) ──
    bmc_conn = CONN4()
    bmc_conn.ref = "J2"
    bmc_conn[1] += sda       # SDA
    bmc_conn[2] += scl       # SCL
    bmc_conn[3] += smbalert  # SMBALERT#
    bmc_conn[4] += gnd       # GND

    # ── 產出 Netlist ──
    generate_netlist(file_="output/fan_controller.net")

    return {
        "nets": {
            "3V3": vcc,
            "GND": gnd,
            "12V": v_fan,
            "I2C_SDA": sda,
            "I2C_SCL": scl,
            "FAN_PWM": fan_pwm,
            "FAN_TACH": fan_tach,
            "SMBALERT_N": smbalert,
        },
        "parts": {
            "EMC2103": emc,
            "FAN_CONN": fan_conn,
            "BMC_CONN": bmc_conn,
        },
    }


if __name__ == "__main__":
    gen_fan_controller()
    print("✅ fan_controller.net 已產生至 output/ 目錄")

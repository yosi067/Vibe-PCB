"""
Smart Power Monitor & Diagnostic Module — 高精度功耗監測模組
基於 INA226 的伺服器 12V/54V 電源監控電路
支援 I2C/SMBus 介面，與 BMC 通訊

電壓域：12V (監測總線) / 3.3V (Logic VCC)
採樣電阻：0.002Ω (2mΩ) 2512 封裝，最大 30A

所有零件使用 tool=SKIDL 內建定義，不依賴外部 KiCad 符號庫。
"""

from skidl import Part, Pin, Net, POWER, TEMPLATE, SKIDL, generate_netlist, reset


# ── 零件模板工廠 ──

def _make_ina226():
    """INA226 高精度電流/功率監測 IC (MSOP-10) 模板"""
    p = Part(name="INA226", dest=TEMPLATE, tool=SKIDL,
             footprint="Package_SO:MSOP-10_3x3mm_P0.5mm")
    p += Pin(num=1,  name="A1",    func=Pin.types.INPUT)      # Address bit 1
    p += Pin(num=2,  name="A0",    func=Pin.types.INPUT)      # Address bit 0
    p += Pin(num=3,  name="ALERT", func=Pin.types.OPENCOLL)   # Alert output
    p += Pin(num=4,  name="SDA",   func=Pin.types.BIDIR)      # I2C Data
    p += Pin(num=5,  name="SCL",   func=Pin.types.INPUT)      # I2C Clock
    p += Pin(num=6,  name="VS",    func=Pin.types.PWRIN)      # Supply 2.7-5.5V
    p += Pin(num=7,  name="GND",   func=Pin.types.PWRIN)      # Ground
    p += Pin(num=8,  name="VBUS",  func=Pin.types.INPUT)      # Bus voltage sense
    p += Pin(num=9,  name="IN-",   func=Pin.types.INPUT)      # Shunt negative
    p += Pin(num=10, name="IN+",   func=Pin.types.INPUT)      # Shunt positive
    return p


def _make_resistor():
    """通用電阻模板"""
    p = Part(name="R", dest=TEMPLATE, tool=SKIDL)
    p += Pin(num=1, name="p1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="p2", func=Pin.types.PASSIVE)
    return p


def _make_shunt_resistor():
    """精密分流電阻模板"""
    p = Part(name="R_Shunt", dest=TEMPLATE, tool=SKIDL)
    p += Pin(num=1, name="p1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="p2", func=Pin.types.PASSIVE)
    return p


def _make_capacitor():
    """通用電容模板"""
    p = Part(name="C", dest=TEMPLATE, tool=SKIDL)
    p += Pin(num=1, name="p1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="p2", func=Pin.types.PASSIVE)
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


def _make_conn_1x02():
    """2-Pin 大電流接頭模板"""
    p = Part(name="Conn_01x02_Male", dest=TEMPLATE, tool=SKIDL,
             footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    p += Pin(num=1, name="P1", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="P2", func=Pin.types.PASSIVE)
    return p


def _make_led():
    """LED 指示燈模板"""
    p = Part(name="LED", dest=TEMPLATE, tool=SKIDL,
             footprint="LED_SMD:LED_0603_1608Metric")
    p += Pin(num=1, name="A", func=Pin.types.PASSIVE)
    p += Pin(num=2, name="K", func=Pin.types.PASSIVE)
    return p


def gen_power_monitor():
    """生成 Smart Power Monitor 電路的 Netlist。

    電路包含：
    - INA226 高精度電流/功率監測 IC (MSOP-10)
    - 0.002Ω 精密分流電阻 (2512 封裝, 2W)
    - I2C 連接器 (共用匯流排)
    - 12V 輸入/輸出大電流接頭
    - 去耦濾波電容
    - ALERT LED 指示
    """

    reset()

    # 建立零件模板
    INA226 = _make_ina226()
    RES = _make_resistor()
    SHUNT = _make_shunt_resistor()
    CAP = _make_capacitor()
    CONN4 = _make_conn_1x04()
    CONN2 = _make_conn_1x02()
    LED = _make_led()

    # ── 電壓網路定義 ──
    vcc = Net("3V3")
    vcc.drive = POWER
    gnd = Net("GND")
    gnd.drive = POWER

    # 12V 電源匯流排 (被監測的電源軌)
    v_bus_in = Net("12V_INPUT")
    v_bus_in.drive = POWER
    v_bus_out = Net("12V_OUTPUT")

    # I2C 匯流排（共用，連往 BMC）
    sda = Net("I2C_SDA")
    scl = Net("I2C_SCL")

    # Alert 中斷
    alert = Net("PWR_ALERT_N")

    # ── 1. INA226 電流/功率監測 IC ──
    ina = INA226()
    ina.ref = "U2"
    ina["VS"] += vcc
    ina["GND"] += gnd
    ina["SDA"] += sda
    ina["SCL"] += scl
    ina["ALERT"] += alert

    # I2C Address = 0x41 (A0=VCC, A1=GND)
    ina["A0"] += vcc     # A0 = 1
    ina["A1"] += gnd     # A1 = 0 → Address = 0x41

    # ── 2. 精密分流電阻 (Shunt Resistor) ──
    # 0.002Ω, 2512 封裝 (額定 2W)
    # 設計電流 30A → P = 30² × 0.002 = 1.8W < 2W ✔
    rsense = SHUNT(value="0.002", footprint="Resistor_SMD:R_2512_6332Metric")
    rsense.ref = "Rs1"
    rsense[1] += v_bus_in
    rsense[2] += v_bus_out

    # 連接至 INA226 的差分感測輸入
    ina["IN+"] += v_bus_in
    ina["IN-"] += v_bus_out
    ina["VBUS"] += v_bus_out

    # ── 3. 12V 輸入接頭 (來源端: PSU) ──
    j_in = CONN2(footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    j_in.ref = "J3"
    j_in[1] += v_bus_in
    j_in[2] += gnd

    # ── 4. 12V 輸出接頭 (負載端: GPU) ──
    j_out = CONN2(footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    j_out.ref = "J4"
    j_out[1] += v_bus_out
    j_out[2] += gnd

    # ── 5. I2C / Alert 接頭 (BMC 連接) ──
    bmc_conn = CONN4()
    bmc_conn.ref = "J5"
    bmc_conn[1] += sda
    bmc_conn[2] += scl
    bmc_conn[3] += alert
    bmc_conn[4] += gnd

    # ── 6. I2C 上拉電阻 ──
    r_sda = RES(value="4.7k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_sda.ref = "R4"
    r_sda[1] += vcc
    r_sda[2] += sda

    r_scl = RES(value="4.7k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_scl.ref = "R5"
    r_scl[1] += vcc
    r_scl[2] += scl

    # ── 7. ALERT 上拉 + LED 指示 ──
    r_alert = RES(value="10k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_alert.ref = "R6"
    r_alert[1] += vcc
    r_alert[2] += alert

    r_led = RES(value="1k", footprint="Resistor_SMD:R_0402_1005Metric")
    r_led.ref = "R7"
    led = LED()
    led.ref = "D1"
    r_led[1] += alert
    r_led[2] += led[1]  # LED Anode
    led[2] += gnd        # LED Cathode → GND

    # ── 8. 去耦電容 (VCC 濾波) ──
    c_vcc_100n = CAP(value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_vcc_100n.ref = "C5"
    c_vcc_100n[1] += vcc
    c_vcc_100n[2] += gnd

    c_vcc_10u = CAP(value="10uF", footprint="Capacitor_SMD:C_0805_2012Metric")
    c_vcc_10u.ref = "C6"
    c_vcc_10u[1] += vcc
    c_vcc_10u[2] += gnd

    # ── 9. 12V 匯流排濾波 (輸入端) ──
    c_bus_100n = CAP(value="100nF", footprint="Capacitor_SMD:C_0603_1608Metric")
    c_bus_100n.ref = "C7"
    c_bus_100n[1] += v_bus_in
    c_bus_100n[2] += gnd

    # ── 產出 Netlist ──
    generate_netlist(file_="output/power_monitor.net")

    return {
        "nets": {
            "3V3": vcc,
            "GND": gnd,
            "12V_INPUT": v_bus_in,
            "12V_OUTPUT": v_bus_out,
            "I2C_SDA": sda,
            "I2C_SCL": scl,
            "PWR_ALERT_N": alert,
        },
        "parts": {
            "INA226": ina,
            "RSENSE": rsense,
            "PWR_IN": j_in,
            "PWR_OUT": j_out,
            "BMC_CONN": bmc_conn,
        },
        "design_params": {
            "shunt_resistance": 0.002,     # Ω
            "max_current": 30,             # A
            "shunt_power": 30**2 * 0.002,  # 1.8W
            "shunt_package": "2512",       # rated 2W
            "i2c_address": 0x41,
            "bus_voltage": 12.0,
        },
    }


if __name__ == "__main__":
    gen_power_monitor()
    print("✅ power_monitor.net 已產生至 output/ 目錄")

#!/usr/bin/env python3
# =============================================================================
# fdir_node.py — Fault Detection, Isolation & Recovery (FDIR)
# =============================================================================
# KTR §3.2: Kritik düğümlerin sağlığını sürekli izleyen merkezi düğüm. Bir
# kaynak belirlenen süre boyunca "sessiz" kalırsa hata sayacı artar; kalıcı
# hata (≥ fault_limit) SAFE_MODE tetikler. Batarya voltajı kritik eşiğin altına
# düşerse de SAFE_MODE tetiklenir.
#
# Tasarım notu: KTR her düğümün 5 Hz DiagnosticArray heartbeat yaymasını öngörür.
# Burada bunun sağlam ve mevcut düğümleri değiştirmeyen eşdeğeri uygulanır:
# her kritik alt sistem için bir CANLILIK topiği izlenir (o topikte mesaj gelmesi
# = alt sistem çalışıyor). Böylece C++/Python tüm düğümler tek tip izlenir.
#
# Yayınlar:
#   /system/health     (std_msgs/Bool, latched)  — tüm kritikler taze + batarya OK
#   /system/safe_mode  (std_msgs/Bool, latched)  — kalıcı hata/kritik batarya
#   /diagnostics       (DiagnosticArray)          — telemetri/YKİ için özet
# Girdi:
#   /system/reset      (std_msgs/Bool)  — operatör: SAFE_MODE mandalını temizle
# =============================================================================

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy,
                       QoSDurabilityPolicy, qos_profile_sensor_data)

from std_msgs.msg import Bool
from sensor_msgs.msg import Image, PointCloud2, Imu, BatteryState
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from mavros_msgs.msg import State as MavState
from ida_msgs.msg import BuoyDetectionArray, MissionState


_LATCHED = QoSProfile(depth=1, history=QoSHistoryPolicy.KEEP_LAST,
                      reliability=QoSReliabilityPolicy.RELIABLE,
                      durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)


class Source:
    """İzlenen bir canlılık kaynağı."""
    def __init__(self, name, timeout, critical):
        self.name = name
        self.timeout = timeout
        self.critical = critical      # kalıcı hata SAFE_MODE tetikler mi
        self.last_t = 0.0
        self.ever_seen = False
        self.fault_count = 0


class FdirNode(Node):
    def __init__(self):
        super().__init__('fdir_node')

        self.declare_parameter('check_rate_hz', 5.0)
        self.declare_parameter('fault_limit', 3)          # ardışık kaçırma → hata
        # Batarya (8S LiFePO4 25.6V nominal): KTR'deki 10.5V hatalıydı.
        self.declare_parameter('battery_warn_v', 22.0)
        self.declare_parameter('battery_critical_v', 20.0)
        # Her kaynak için sessizlik toleransı (s)
        self.declare_parameter('timeout_mavros', 1.5)
        self.declare_parameter('timeout_camera', 2.0)
        self.declare_parameter('timeout_lidar', 2.0)
        self.declare_parameter('timeout_perception', 5.0)
        self.declare_parameter('timeout_mission', 2.0)
        self.declare_parameter('timeout_imu', 1.5)

        self._limit = int(self.get_parameter('fault_limit').value)
        self._batt_warn = self.get_parameter('battery_warn_v').value
        self._batt_crit = self.get_parameter('battery_critical_v').value

        g = lambda p: self.get_parameter(p).value
        # (name, timeout, critical)
        self._sources = {
            'mavros':     Source('mavros',     g('timeout_mavros'),     True),
            'camera':     Source('camera',     g('timeout_camera'),     True),
            'lidar':      Source('lidar',      g('timeout_lidar'),      True),
            'perception': Source('perception', g('timeout_perception'), False),
            'mission':    Source('mission',    g('timeout_mission'),    False),
            'imu':        Source('imu',        g('timeout_imu'),        True),
        }

        self._battery_v = float('nan')
        self._safe_mode = False

        # ── Abonelikler (her biri ilgili kaynağın zaman damgasını tazeler) ──
        self.create_subscription(MavState, '/mavros/state',
                                 lambda m: self._touch('mavros'), qos_profile_sensor_data)
        self.create_subscription(Image, '/camera/image_ml',
                                 lambda m: self._touch('camera'), qos_profile_sensor_data)
        self.create_subscription(PointCloud2, '/lidar/filtered',
                                 lambda m: self._touch('lidar'), qos_profile_sensor_data)
        self.create_subscription(BuoyDetectionArray, '/buoy_detections',
                                 lambda m: self._touch('perception'), qos_profile_sensor_data)
        self.create_subscription(MissionState, '/mission/state',
                                 lambda m: self._touch('mission'), 10)
        self.create_subscription(Imu, '/mavros/imu/data',
                                 lambda m: self._touch('imu'), qos_profile_sensor_data)
        self.create_subscription(BatteryState, '/mavros/battery',
                                 self._battery_cb, qos_profile_sensor_data)
        self.create_subscription(Bool, '/system/reset', self._reset_cb, 10)

        # ── Yayıncılar ──────────────────────────────────────────────────────
        self._health_pub = self.create_publisher(Bool, '/system/health', _LATCHED)
        self._safe_pub   = self.create_publisher(Bool, '/system/safe_mode', _LATCHED)
        self._diag_pub   = self.create_publisher(DiagnosticArray, '/diagnostics', 10)

        rate = float(self.get_parameter('check_rate_hz').value)
        self.create_timer(1.0 / max(rate, 1.0), self._check)
        self.get_logger().info(
            f'FDIR başlatıldı. İzlenen: {list(self._sources.keys())} + batarya '
            f'(uyarı<{self._batt_warn}V, kritik<{self._batt_crit}V).')

    # ─────────────────────────────────────────────────────────────────────────

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _touch(self, name):
        s = self._sources[name]
        s.last_t = self._now()
        s.ever_seen = True

    def _battery_cb(self, msg: BatteryState):
        self._battery_v = msg.voltage

    def _reset_cb(self, msg: Bool):
        if msg.data and self._safe_mode:
            self._safe_mode = False
            for s in self._sources.values():
                s.fault_count = 0
            self.get_logger().warn('FDIR SAFE_MODE mandalı operatörce RESET edildi.')

    def _check(self):
        now = self._now()
        all_fresh = True
        statuses = []
        critical_fault = False

        for s in self._sources.values():
            fresh = s.ever_seen and (now - s.last_t) < s.timeout
            if s.ever_seen and not fresh:
                s.fault_count += 1
                if s.critical and s.fault_count >= self._limit:
                    critical_fault = True
            else:
                s.fault_count = max(0, s.fault_count - 1)
            if not fresh:
                all_fresh = False

            lvl = DiagnosticStatus.OK if fresh else (
                DiagnosticStatus.ERROR if s.critical else DiagnosticStatus.WARN)
            st = DiagnosticStatus(name=f'ida/{s.name}', level=lvl,
                                  message='ok' if fresh else 'silent')
            st.values = [KeyValue(key='fault_count', value=str(s.fault_count))]
            statuses.append(st)

        # ── Batarya ─────────────────────────────────────────────────────────
        batt_ok = True
        batt_crit = False
        v = self._battery_v
        if v == v and v > 0.0:   # NaN değil ve geçerli
            batt_ok = v >= self._batt_warn
            batt_crit = v < self._batt_crit
            lvl = DiagnosticStatus.OK if batt_ok else (
                DiagnosticStatus.ERROR if batt_crit else DiagnosticStatus.WARN)
            statuses.append(DiagnosticStatus(
                name='ida/battery', level=lvl, message=f'{v:.1f}V',
                values=[KeyValue(key='voltage', value=f'{v:.2f}')]))

        # ── SAFE_MODE mandalı ──────────────────────────────────────────────
        if critical_fault or batt_crit:
            if not self._safe_mode:
                reason = 'kritik düğüm hatası' if critical_fault else \
                    f'kritik batarya ({v:.1f}V)'
                self.get_logger().error(f'FDIR → SAFE_MODE ({reason}).')
            self._safe_mode = True

        health_ok = all_fresh and batt_ok and not self._safe_mode

        self._health_pub.publish(Bool(data=health_ok))
        self._safe_pub.publish(Bool(data=self._safe_mode))
        da = DiagnosticArray()
        da.header.stamp = self.get_clock().now().to_msg()
        da.status = statuses
        self._diag_pub.publish(da)


def main(args=None):
    rclpy.init(args=args)
    node = FdirNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

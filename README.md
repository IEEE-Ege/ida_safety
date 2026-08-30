# ida_safety — güvenlik / FDIR

**🇹🇷 [Türkçe](#türkçe) · 🇬🇧 [English](#english)**

---

## Türkçe

### Genel Bakış
Arıza Tespit, İzolasyon ve Kurtarma (FDIR) paketi. Kritik düğümlerin canlılığını
(heartbeat) ve bataryayı izler; `/system/health` ve `/system/safe_mode` yayınlar.
Görev FSM'i (`ida_mission`) bu sinyalleri SAFE_MODE / CONNECTION_FAIL / INIT
geçişlerinde kullanır. Düğüm: `fdir_node`.

### Kurulum
> Önkoşullar: ROS 2 Humble, `colcon`, `rosdep`, Python + `pip`.

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone <REPO_URL> ida_safety   # ida_msgs'i de klonlayın
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
pip install -r src/ida_safety/requirements.txt
colcon build --packages-select ida_safety
source install/setup.bash
```

### Kullanım
```bash
ros2 run ida_safety fdir_node --ros-args --params-file \
  src/ida_safety/config/safety_params.yaml
```

### Bağımlılıklar
ROS 2: `rclpy`, `diagnostic_msgs`, `sensor_msgs`, `mavros_msgs`, `ida_msgs`.
Pip: `numpy`.

### Lisans
**MIT.** Bulaşıcı bağımlılık yoktur.

**Kullanım koşulları:** Özgürce kullanın/değiştirin/dağıtın; lisans bildirimini
koruyun. Geliştirme yaparsanız bize **PR açmanız bizi mutlu eder** (zorunlu değil).

### Özel veri
Yoktur. Parametreler genel canlılık/batarya eşikleridir.

---

## English

### Overview
Fault Detection, Isolation and Recovery (FDIR) package. Monitors the liveness
(heartbeat) of critical nodes and the battery; publishes `/system/health` and
`/system/safe_mode`. The mission FSM (`ida_mission`) uses these signals for
SAFE_MODE / CONNECTION_FAIL / INIT transitions. Node: `fdir_node`.

### Installation
> Prerequisites: ROS 2 Humble, `colcon`, `rosdep`, Python + `pip`.

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone <REPO_URL> ida_safety   # also clone ida_msgs
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
pip install -r src/ida_safety/requirements.txt
colcon build --packages-select ida_safety
source install/setup.bash
```

### Usage
```bash
ros2 run ida_safety fdir_node --ros-args --params-file \
  src/ida_safety/config/safety_params.yaml
```

### Dependencies
ROS 2: `rclpy`, `diagnostic_msgs`, `sensor_msgs`, `mavros_msgs`, `ida_msgs`.
Pip: `numpy`.

### License
**MIT.** No contagious dependency.

**Terms:** free to use/modify/distribute; preserve the license notice. If you
improve it, **a PR back to us would make us happy** (not required).

### Private data
None. The parameters are generic liveness/battery thresholds.

---

<div align="center">

💙 **Bu Repo IEEE Ege Mavi İnci İnsansız Deniz Aracı Takımı Yazılım Ekibi Tarafından Oluşturulmuştur, Yazılım Ekibimize Sevgilerle**

[@NightKnight-nx2](https://github.com/NightKnight-nx2) · [@yalinoner](https://github.com/yalinoner) · [@nilayyldz](https://github.com/nilayyldz)

</div>

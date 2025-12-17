import os
import shutil
import psutil
import ctypes
import subprocess
import pynvml # NVIDIA용
import wmi    # 인텔/기타 GPU용
import time
import pythoncom
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QHBoxLayout, QFrame, QCheckBox, QGridLayout, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from modules.ui.custom_msg import CustomMessageBox
from .system_graphs import LiveGraphWidget
from .spec_dialog import HardwareSpecDialog, SpecDataLoader

# [1] 청소 작업자 (기존 동일)
class CleanWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, int)

    def __init__(self, options):
        super().__init__()
        self.options = options

    def run(self):
        targets = []
        user_profile = os.environ.get('USERPROFILE')

        if self.options.get("temp", False):
            targets.extend([
                os.environ.get('TEMP'),
                os.path.join(os.environ.get('SystemRoot'), 'Temp'),
                os.path.join(user_profile, r"AppData\Local\Temp")
            ])

        if self.options.get("chrome", False):
            targets.extend([
                os.path.join(user_profile, r"AppData\Local\Google\Chrome\User Data\Default\Cache"),
                os.path.join(user_profile, r"AppData\Local\Google\Chrome\User Data\Default\Code Cache")
            ])
        if self.options.get("edge", False):
            targets.append(os.path.join(user_profile, r"AppData\Local\Microsoft\Edge\User Data\Default\Cache"))
        if self.options.get("firefox", False):
            firefox_base = os.path.join(user_profile, r"AppData\Local\Mozilla\Firefox\Profiles")
            if os.path.exists(firefox_base):
                try:
                    for folder in os.listdir(firefox_base):
                        targets.append(os.path.join(firefox_base, folder, "cache2"))
                except: pass

        if self.options.get("recent", False):
            targets.append(os.path.join(user_profile, r"AppData\Roaming\Microsoft\Windows\Recent"))

        files_to_delete = []
        for d in targets:
            if d and os.path.exists(d):
                try:
                    for root, _, files in os.walk(d):
                        for f in files:
                            files_to_delete.append(os.path.join(root, f))
                except: pass
        
        total_count = len(files_to_delete)
        deleted_files = 0
        reclaimed_bytes = 0

        for i, file_path in enumerate(files_to_delete):
            try:
                size = os.path.getsize(file_path)
                os.remove(file_path)
                deleted_files += 1
                reclaimed_bytes += size
            except: pass
            if i % 10 == 0: self.progress.emit(i + 1, total_count)

        if self.options.get("dns", False):
            try: subprocess.run(["ipconfig", "/flushdns"], shell=True, stdout=subprocess.DEVNULL)
            except: pass

        if self.options.get("recycle", False):
            try: ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            except: pass
            
        if self.options.get("clipboard", False):
            try:
                if ctypes.windll.user32.OpenClipboard(None):
                    ctypes.windll.user32.EmptyClipboard()
                    ctypes.windll.user32.CloseClipboard()
            except: pass

        reclaimed_mb = int(reclaimed_bytes / (1024 * 1024))
        self.finished.emit(deleted_files, reclaimed_mb)


# [2] 시스템 감시 작업자 (속도 개선)
class SystemMonitorWorker(QThread):
    stats_updated = pyqtSignal(dict)

    def __init__(self, gpu_widgets):
        super().__init__()
        self.running = True
        self.gpu_widgets = gpu_widgets
        self.last_net = psutil.net_io_counters()
        self.last_disk = psutil.disk_io_counters()

    def run(self):
        pythoncom.CoInitialize()
        try: wmi_obj = wmi.WMI()
        except: wmi_obj = None

        while self.running:
            # 1. CPU & RAM
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            # 2. Disk & Net
            curr_disk = psutil.disk_io_counters()
            curr_net = psutil.net_io_counters()
            
            disk_diff = (curr_disk.read_bytes + curr_disk.write_bytes) - (self.last_disk.read_bytes + self.last_disk.write_bytes)
            # 0.5초 기준이므로 초당 속도로 환산하려면 * 2 해줘야 함
            disk_speed_mb = (disk_diff / (1024 * 1024)) * 2
            
            net_diff = (curr_net.bytes_sent + curr_net.bytes_recv) - (self.last_net.bytes_sent + self.last_net.bytes_recv)
            net_speed_kb = (net_diff / 1024) * 2

            self.last_disk = curr_disk
            self.last_net = curr_net

            # 3. GPU
            gpu_stats = []
            
            # WMI (인텔 등)
            wmi_load = 0
            if wmi_obj:
                try:
                    results = wmi_obj.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
                    if results:
                        max_load = 0
                        for r in results:
                            try:
                                val = int(r.UtilizationPercentage)
                                if val > max_load: max_load = val
                            except: pass
                        wmi_load = max_load
                except: wmi_load = -1

            # 각 GPU 매핑
            for gpu in self.gpu_widgets:
                load = 0
                if gpu["is_nvidia"] and gpu["handle"]:
                    try:
                        util = pynvml.nvmlDeviceGetUtilizationRates(gpu["handle"])
                        load = util.gpu
                    except: load = -1
                else:
                    load = wmi_load
                gpu_stats.append(load)

            data = {
                "cpu": cpu, "ram": ram,
                "disk": disk_speed_mb, "net": net_speed_kb,
                "gpu": gpu_stats
            }
            
            self.stats_updated.emit(data)
            
            # [수정] 1.0 -> 0.5초로 단축 (훨씬 부드러움)
            time.sleep(0.5)

    def stop(self):
        self.running = False
        self.wait()


# [3] 메인 UI 클래스
class SystemCareWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.spec_data = None 
        self.gpu_widgets = []
        self.nvml_initialized = False
        
        try:
            pynvml.nvmlInit()
            self.nvml_initialized = True
        except:
            self.nvml_initialized = False

        self.init_ui()
        
        self.spec_loader = SpecDataLoader()
        self.spec_loader.data_loaded.connect(self.on_spec_loaded)
        self.spec_loader.start()
        
        # 모니터 워커 시작
        self.monitor_worker = SystemMonitorWorker(self.gpu_widgets)
        self.monitor_worker.stats_updated.connect(self.update_ui_from_worker)
        self.monitor_worker.start()

    def on_spec_loaded(self, data):
        self.spec_data = data
        self.btn_spec.setText("ℹ️ 하드웨어 초정밀 분석")
        self.btn_spec.setEnabled(True)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; } QScrollBar { background: #2b2b2b; }")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        header_layout = QHBoxLayout()
        lbl_title = QLabel("📊 실시간 시스템 성능")
        lbl_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        self.btn_spec = QPushButton("ℹ️ 데이터 분석 중...")
        self.btn_spec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_spec.setFixedSize(160, 35)
        self.btn_spec.setStyleSheet("QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #4d4d4d; border-color: #888; }")
        self.btn_spec.clicked.connect(self.show_specs)
        self.btn_spec.setEnabled(False)
        header_layout.addWidget(self.btn_spec)
        self.layout.addLayout(header_layout)
        
        self.monitor_grid = QGridLayout()
        self.monitor_grid.setSpacing(15)

        self.graph_cpu = LiveGraphWidget("#00fa9a")
        self.lbl_cpu_val = self.create_stat_label("0%")
        self.monitor_grid.addWidget(self.create_graph_box("CPU 사용량", self.lbl_cpu_val, self.graph_cpu), 0, 0)
        
        self.graph_ram = LiveGraphWidget("#9b59b6")
        self.lbl_ram_val = self.create_stat_label("0%")
        self.monitor_grid.addWidget(self.create_graph_box("메모리 (RAM)", self.lbl_ram_val, self.graph_ram), 0, 1)
        
        self.graph_disk = LiveGraphWidget("#3498db")
        self.lbl_disk_val = self.create_stat_label("0 MB/s")
        self.monitor_grid.addWidget(self.create_graph_box("디스크 속도", self.lbl_disk_val, self.graph_disk), 1, 0)
        
        self.graph_net = LiveGraphWidget("#f1c40f")
        self.lbl_net_val = self.create_stat_label("0 KB/s")
        self.monitor_grid.addWidget(self.create_graph_box("네트워크", self.lbl_net_val, self.graph_net), 1, 1)

        self.init_gpu_graphs()

        self.layout.addLayout(self.monitor_grid)

        lbl_clean = QLabel("🧹 고급 시스템 청소")
        lbl_clean.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        self.layout.addWidget(lbl_clean)
        
        clean_box = QFrame()
        clean_box.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; padding: 15px;")
        clean_layout = QVBoxLayout(clean_box)

        clean_header = QHBoxLayout()
        clean_header.addStretch()
        self.chk_all = QCheckBox("모두 선택")
        self.chk_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_all.setStyleSheet("color: #00fa9a; font-weight: bold; font-size: 14px;")
        self.chk_all.stateChanged.connect(self.toggle_all)
        clean_header.addWidget(self.chk_all)
        clean_layout.addLayout(clean_header)

        chk_layout = QGridLayout()
        chk_layout.setVerticalSpacing(15)
        
        self.chk_temp = QCheckBox("윈도우 임시 파일 (Temp)")
        self.chk_recycle = QCheckBox("휴지통 비우기")
        self.chk_recent = QCheckBox("최근 문서/실행 기록")
        self.chk_chrome = QCheckBox("Chrome 캐시")
        self.chk_edge = QCheckBox("Edge 캐시")
        self.chk_firefox = QCheckBox("Firefox 캐시")
        self.chk_dns = QCheckBox("DNS 캐시 초기화")
        self.chk_clipboard = QCheckBox("클립보드 내용 삭제")

        self.check_boxes = [
            self.chk_temp, self.chk_recycle, self.chk_recent,
            self.chk_chrome, self.chk_edge, self.chk_firefox,
            self.chk_dns, self.chk_clipboard
        ]
        self.chk_temp.setChecked(True)
        self.chk_recycle.setChecked(True)

        for i, chk in enumerate(self.check_boxes):
            chk.setStyleSheet("QCheckBox { color: #ddd; font-size: 14px; } QCheckBox::indicator { width: 18px; height: 18px; }")
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk_layout.addWidget(chk, i // 2, i % 2)
        
        clean_layout.addLayout(chk_layout)
        
        self.btn_clean = QPushButton("🚀 선택 항목 정리 시작")
        self.btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean.setFixedHeight(45)
        self.btn_clean.setStyleSheet("background-color: #e74c3c; color: white; font-size: 15px; font-weight: bold; border-radius: 8px; margin-top: 15px;")
        self.btn_clean.clicked.connect(self.start_cleaning)
        clean_layout.addWidget(self.btn_clean)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #aaa; margin-top: 5px;")
        clean_layout.addWidget(self.lbl_status)

        self.layout.addWidget(clean_box)
        self.layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def init_gpu_graphs(self):
        gpu_names = []
        try:
            cmd = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
            try: output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('cp949').strip()
            except: output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('utf-8', errors='ignore').strip()
            gpu_names = [line.strip() for line in output.split('\n') if line.strip()]
            gpu_names = sorted(list(set(gpu_names)))
        except: 
            gpu_names = ["GPU"]

        nvidia_index = 0
        current_row = 2
        current_col = 0

        for name in gpu_names:
            is_nvidia = "NVIDIA" in name.upper()
            handle = None
            if is_nvidia and self.nvml_initialized:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(nvidia_index)
                    nvidia_index += 1
                except: is_nvidia = False

            graph = LiveGraphWidget("#ff6b6b")
            val_lbl = self.create_stat_label("0%")
            short_name = name.replace("NVIDIA GeForce", "").replace("Intel(R)", "").replace("Graphics", "").strip()
            title = f"GPU: {short_name}"
            
            self.monitor_grid.addWidget(self.create_graph_box(title, val_lbl, graph), current_row, current_col)
            
            self.gpu_widgets.append({
                "graph": graph,
                "label": val_lbl,
                "is_nvidia": is_nvidia,
                "handle": handle
            })

            current_col += 1
            if current_col > 1:
                current_col = 0
                current_row += 1

    def update_ui_from_worker(self, data):
        self.graph_cpu.add_data(data['cpu'])
        self.lbl_cpu_val.setText(f"{data['cpu']}%")
        self.graph_ram.add_data(data['ram'])
        self.lbl_ram_val.setText(f"{data['ram']}%")
        self.graph_disk.add_data(data['disk']) 
        self.lbl_disk_val.setText(f"{data['disk']:.1f} MB/s")
        self.graph_net.add_data(data['net'])
        self.lbl_net_val.setText(f"{int(data['net'])} KB/s")

        for i, load in enumerate(data['gpu']):
            if i < len(self.gpu_widgets):
                widget = self.gpu_widgets[i]
                if load < 0:
                    widget["label"].setText("N/A")
                    widget["graph"].add_data(0)
                else:
                    widget["label"].setText(f"{load}%")
                    widget["graph"].add_data(load)

    def toggle_all(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        for chk in self.check_boxes:
            chk.setChecked(is_checked)

    def create_stat_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #eee; font-size: 13px; font-weight: bold;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def create_graph_box(self, title, val_lbl, graph_widget):
        frame = QFrame()
        frame.setStyleSheet("background-color: #2b2b2b; border-radius: 10px;")
        vbox = QVBoxLayout(frame)
        header = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #aaa; font-size: 14px; border: none;")
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(val_lbl)
        vbox.addLayout(header)
        vbox.addWidget(graph_widget)
        return frame

    def show_specs(self):
        if self.spec_data:
            HardwareSpecDialog(self.spec_data, self).exec()
        else:
            CustomMessageBox("알림", "아직 데이터를 분석 중입니다.", parent=self).exec()

    def start_cleaning(self):
        options = {
            "temp": self.chk_temp.isChecked(),
            "recycle": self.chk_recycle.isChecked(),
            "recent": self.chk_recent.isChecked(),
            "chrome": self.chk_chrome.isChecked(),
            "edge": self.chk_edge.isChecked(),
            "firefox": self.chk_firefox.isChecked(),
            "dns": self.chk_dns.isChecked(),
            "clipboard": self.chk_clipboard.isChecked()
        }
        
        if not any(options.values()):
            CustomMessageBox("알림", "최소 하나 이상의 항목을 선택해주세요.", parent=self).exec()
            return

        msg = CustomMessageBox("청소 시작", "선택한 항목을 정리하시겠습니까?\n(사용 중인 파일은 건너뜁니다)", is_question=True, parent=self)
        if msg.exec() == 1:
            self.btn_clean.setEnabled(False)
            self.btn_clean.setText("🧹 열심히 청소 중...")
            self.lbl_status.setText("파일을 검색하고 삭제하는 중입니다...")
            
            self.worker = CleanWorker(options)
            self.worker.progress.connect(lambda cur, tot: self.lbl_status.setText(f"진행 중: {cur}/{tot} 파일 처리"))
            self.worker.finished.connect(self.cleaning_finished)
            self.worker.start()

    def cleaning_finished(self, deleted_count, freed_mb):
        self.btn_clean.setEnabled(True)
        self.btn_clean.setText("🚀 선택 항목 정리 시작")
        self.lbl_status.setText("")
        CustomMessageBox("청소 완료", f"🎉 청소가 끝났습니다!\n\n삭제된 파일: {deleted_count}개\n확보된 용량: {freed_mb} MB", parent=self).exec()
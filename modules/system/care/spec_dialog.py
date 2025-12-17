import platform
import psutil
import subprocess
import socket
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QWidget, 
                             QPushButton, QGridLayout, QTabWidget, QScrollArea, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from modules.ui.title_bar import CustomTitleBar

# ▼ [Logic] 백그라운드 데이터 수집
class SpecDataLoader(QThread):
    data_loaded = pyqtSignal(dict) 

    def run(self):
        # 1. CPU 정보 (리스트 반환)
        cpu_data = self.get_powershell_list_data("Win32_Processor", 
            ["Name", "Manufacturer", "MaxClockSpeed", "NumberOfCores", "NumberOfLogicalProcessors", "L2CacheSize", "L3CacheSize", "SocketDesignation", "Description"])
        
        # 2. RAM 정보
        ram_data = self.get_ram_info()
        
        # 3. GPU 정보 (JSON 방식 -> 리스트 반환)
        gpu_data = self.get_gpu_info_json()
        
        # 4. Disk 정보
        disk_data = self.get_disk_info()
        
        # 5. Net 정보
        net_data = self.get_net_info()

        # 6. 요약 정보 (여기는 중복 키가 없으므로 Dict 유지)
        uname = platform.uname()
        ram_GB = round(psutil.virtual_memory().total / (1024.0 ** 3), 2)
        
        # CPU 이름 찾기 (리스트에서 검색)
        cpu_name = uname.processor
        for k, v in cpu_data:
            if k == "Name":
                cpu_name = v
                break
        
        # GPU 이름 찾기
        gpu_names_list = self.get_gpu_names_simple()
        gpu_summary = " / ".join(gpu_names_list) if gpu_names_list else "확인 불가"

        summary_data = {
            "운영체제": f"{uname.system} {uname.release} ({uname.version})",
            "PC 이름": uname.node,
            "프로세서": cpu_name,
            "메모리": f"{ram_GB} GB",
            "그래픽": gpu_summary,
            "IP 주소": socket.gethostbyname(socket.gethostname())
        }

        full_data = {
            "summary": summary_data,
            "cpu": cpu_data,
            "ram": ram_data,
            "gpu": gpu_data,
            "disk": disk_data,
            "net": net_data
        }
        
        self.data_loaded.emit(full_data)

    # --- 헬퍼 함수 ---
    def get_gpu_names_simple(self):
        names = []
        try:
            cmd = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
            try:
                output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('cp949').strip()
            except:
                output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('utf-8', errors='ignore').strip()
            
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            if lines:
                names = sorted(list(set(lines)))
        except: pass
        return names

    def parse_list_to_tuples(self, text_block):
        """텍스트 블록을 (Key, Value) 튜플 리스트로 변환"""
        data = []
        for line in text_block.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                data.append((key.strip(), val.strip()))
        return data

    def get_powershell_list_data(self, target, keys):
        try:
            select_str = ", ".join(keys)
            cmd = f"Get-CimInstance {target} | Select-Object {select_str} | Format-List"
            try:
                output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('cp949').strip()
            except:
                output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode('utf-8', errors='ignore').strip()
            return self.parse_list_to_tuples(output)
        except: return []

    def get_ram_info(self):
        info = [] # 리스트로 변경
        mem = psutil.virtual_memory()
        info.append(("--- 시스템 메모리 요약 ---", ""))
        info.append(("전체 용량", f"{round(mem.total / (1024**3), 2)} GB"))
        info.append(("사용 가능", f"{round(mem.available / (1024**3), 2)} GB"))
        
        try:
            cmd = "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, Speed, Capacity | Format-List"
            output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode(errors='ignore').strip()
            sticks = output.split("\r\n\r\n")
            for idx, stick in enumerate(sticks):
                if not stick.strip(): continue
                data_dict = dict(self.parse_list_to_tuples(stick)) # 임시 딕셔너리 변환
                
                info.append((f"--- 슬롯 #{idx+1} ---", ""))
                info.append(("제조사", data_dict.get("Manufacturer", "-")))
                
                cap_str = data_dict.get("Capacity", "0")
                if cap_str.isdigit():
                    info.append(("용량", f"{int(cap_str) // (1024**3)} GB"))
                else:
                    info.append(("용량", cap_str))
                    
                info.append(("속도", f"{data_dict.get('Speed', '?')} MHz"))
        except: pass
        return info

    def get_gpu_info_json(self):
        info = [] # 리스트로 변경
        try:
            cmd = "Get-CimInstance Win32_VideoController | Select-Object * | ConvertTo-Json -Compress"
            output_bytes = subprocess.check_output(["powershell", "-Command", cmd], shell=True)
            
            try: json_str = output_bytes.decode('utf-8')
            except: json_str = output_bytes.decode('cp949', errors='ignore')

            try: data_list = json.loads(json_str)
            except: return [("Info", "데이터 파싱 실패")]

            if isinstance(data_list, dict): data_list = [data_list]

            for idx, gpu in enumerate(data_list):
                name = gpu.get("Name", f"GPU {idx+1}")
                info.append((f"--- [{name}] ---", "")) # 구분선
                
                # 우선순위 항목
                priorities = ["DriverVersion", "VideoProcessor", "AdapterRAM", "CurrentHorizontalResolution", "CurrentVerticalResolution"]
                for p in priorities:
                    val = gpu.get(p)
                    if val is not None:
                        if p == "AdapterRAM" and isinstance(val, int):
                            if val < 0: val += 2**32
                            val = f"{val // (1024**2)} MB"
                        info.append((p, str(val)))

                # 나머지 항목
                for k, v in gpu.items():
                    if k not in priorities and v is not None and str(v).strip() != "":
                        if k.startswith("Cim") or k.startswith("Psobject") or k in ["Status", "ConfigManagerErrorCode", "CreationClassName", "SystemCreationClassName", "SystemName", "DeviceID", "PNPDeviceID", "Name"]:
                            continue
                        info.append((k, str(v)))
        except Exception as e:
            info.append(("Error", str(e)))
        return info

    def get_disk_info(self):
        info = []
        try:
            cmd = "Get-CimInstance Win32_DiskDrive | Select-Object Model, InterfaceType, Size, MediaType | Format-List"
            output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode(errors='ignore').strip()
            disks = output.split("\r\n\r\n")
            for idx, disk in enumerate(disks):
                if not disk.strip(): continue
                data_dict = dict(self.parse_list_to_tuples(disk))
                
                model = data_dict.get("Model", f"Disk {idx+1}")
                info.append((f"--- {model} ---", ""))
                
                for k, v in data_dict.items():
                    if k != "Model":
                        if k == "Size" and v.isdigit():
                            info.append((k, f"{int(v) // (1024**3)} GB"))
                        else:
                            info.append((k, v))
        except: pass
        return info

    def get_net_info(self):
        info = []
        try:
            cmd = "Get-CimInstance Win32_NetworkAdapter -Filter 'NetEnabled=True' | Select-Object Name, MACAddress, Speed | Format-List"
            output = subprocess.check_output(["powershell", "-Command", cmd], shell=True).decode(errors='ignore').strip()
            nets = output.split("\r\n\r\n")
            for idx, net in enumerate(nets):
                if not net.strip(): continue
                data_dict = dict(self.parse_list_to_tuples(net))
                
                name = data_dict.get("Name", f"Net {idx+1}")
                info.append((f"--- {name} ---", ""))
                
                for k, v in data_dict.items():
                    if k != "Name":
                        if k == "Speed" and v.isdigit():
                            info.append((k, f"{int(v) // (1000**2)} Mbps"))
                        else:
                            info.append((k, v))
        except: pass
        return info


# ▼ [UI] 다이얼로그 (데이터 렌더링 방식 수정)
class HardwareSpecDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(750, 600)
        
        if parent:
            geo = parent.geometry()
            self.move(geo.center() - self.rect().center())

        self.init_ui()

    def init_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 750, 600)
        container.setStyleSheet("""
            QWidget { background-color: #2b2b2b; border: 1px solid #555; border-radius: 10px; }
            QLabel { color: #ddd; font-size: 14px; border: none; }
            QPushButton { background-color: #0078D7; color: white; border-radius: 5px; padding: 8px; border: none; font-weight: bold;}
            QPushButton:hover { background-color: #005a9e; }
            QTabWidget::pane { border: 1px solid #444; border-radius: 5px; }
            QTabBar::tab { background: #333; color: #aaa; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
            QTabBar::tab:selected { background: #2b2b2b; color: #00fa9a; font-weight: bold; border-bottom: 2px solid #00fa9a; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #2b2b2b; width: 10px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_bar = CustomTitleBar(self, title="하드웨어 초정밀 분석", can_maximize=False)
        self.title_bar.setStyleSheet("border-bottom: 1px solid #3d3d3d; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        layout.addWidget(self.title_bar)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        
        # 탭 추가 (is_summary=True 인 경우 Dict 처리, 나머지는 List 처리)
        self.tabs.addTab(self.create_scrollable_tab(self.data['summary'], is_summary=True), "🔍 요약")
        self.tabs.addTab(self.create_scrollable_tab(self.data['cpu']), "🧠 CPU")
        self.tabs.addTab(self.create_scrollable_tab(self.data['ram']), "💾 RAM")
        self.tabs.addTab(self.create_scrollable_tab(self.data['gpu']), "🎮 GPU")
        self.tabs.addTab(self.create_scrollable_tab(self.data['disk']), "💿 Disk")
        self.tabs.addTab(self.create_scrollable_tab(self.data['net']), "🌐 Net")
        
        content_layout.addWidget(self.tabs)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        content_layout.addWidget(btn_close)

        layout.addLayout(content_layout)

    def create_scrollable_tab(self, data_source, is_summary=False):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent; border: none;")
        layout = QGridLayout(content)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setColumnStretch(1, 1)

        row = 0
        
        # [수정] Dict와 List를 모두 처리할 수 있게 변경
        # is_summary(요약) 탭은 Dict, 나머지 상세 탭은 List(Tuple) 형태임
        iterator = data_source.items() if isinstance(data_source, dict) else data_source

        for key, value in iterator:
            if "---" in key:
                line_lbl = QLabel(key)
                line_lbl.setStyleSheet("color: #0078D7; font-weight: bold; font-size: 15px; margin-top: 15px; margin-bottom: 5px;")
                layout.addWidget(line_lbl, row, 0, 1, 2)
            else:
                lbl_k = QLabel(key)
                lbl_k.setStyleSheet("color: #00fa9a; font-weight: bold;")
                if is_summary: lbl_k.setStyleSheet("color: #00fa9a; font-weight: bold; font-size: 14px;")
                
                lbl_v = QLabel(str(value))
                lbl_v.setWordWrap(True)
                lbl_v.setStyleSheet("color: #e0e0e0;")
                
                layout.addWidget(lbl_k, row, 0)
                layout.addWidget(lbl_v, row, 1)
            row += 1

        scroll.setWidget(content)
        return scroll
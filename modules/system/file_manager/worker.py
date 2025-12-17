import os
import math
import fnmatch # 와일드카드 매칭용
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen

# ==========================================
# [1] UI: 로딩 스피너 (뱅글뱅글)
# ==========================================
class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)
        self.setFixedSize(60, 60)

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        painter.translate(w / 2, h / 2)
        painter.rotate(self.angle)

        for i in range(8):
            painter.rotate(45)
            opacity = int(255 * (i + 1) / 8) 
            painter.setBrush(QColor(0, 120, 215, opacity))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(15, -4, 8, 8)

# ==========================================
# [2] UI: 로딩 다이얼로그 (팝업창)
# ==========================================
class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 150)
        
        if parent:
            # 부모 위젯 중앙에 위치
            center_point = parent.mapToGlobal(parent.rect().center())
            self.move(center_point.x() - self.width() // 2, 
                      center_point.y() - self.height() // 2)

        layout = QVBoxLayout(self)
        
        self.bg = QWidget(self)
        self.bg.setStyleSheet("background-color: rgba(40, 40, 40, 240); border-radius: 15px;")
        self.bg.setGeometry(0, 0, 200, 150)
        
        inner_layout = QVBoxLayout(self.bg)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spinner = LoadingSpinner()
        inner_layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("불러오는 중...")
        self.label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px; font-size: 14px; background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(self.label)

# ==========================================
# [3] Logic: 파일 스캔 일꾼 (필터링 포함)
# ==========================================
class FolderScanWorker(QThread):
    finished_data = pyqtSignal(dict) 

    def __init__(self, folder_path, filter_hidden=True):
        super().__init__()
        self.folder_path = folder_path
        self.filter_hidden = filter_hidden
        
        # [수정] 무시할 파일/폴더 패턴 목록 (obj, bin, .vs 추가)
        self.ignore_patterns = [
            # 파이썬/개발 관련
            'venv', '.venv', 'env', '__pycache__', 
            '*.pyc', '*.pyd', '*.pyo', 
            '.git', '.vscode', '.idea',
            'node_modules', 'dist', 'build',
            
            # Visual Studio 관련 (추가됨)
            'obj', 'bin', '.vs',
            
            # 시스템 파일
            'Desktop.ini', 'Thumbs.db',
            '$RECYCLE.BIN', 'System Volume Information'
        ]

    def run(self):
        result_data = self.scan_recursive(self.folder_path)
        self.finished_data.emit(result_data)

    def scan_recursive(self, path):
        from .utils import format_size, get_video_duration
        
        node = {
            'name': os.path.basename(path),
            'path': path,
            'type': 'folder',
            'children': []
        }
        
        try:
            items = os.listdir(path)
            items.sort() # 이름순 정렬

            for name in items:
                # [필터링 로직] 체크박스가 켜져있고, 무시 목록에 해당하면 건너뜀
                if self.filter_hidden:
                    should_skip = False
                    for pattern in self.ignore_patterns:
                        if fnmatch.fnmatch(name, pattern):
                            should_skip = True
                            break
                    if should_skip:
                        continue

                full_path = os.path.join(path, name)
                
                if os.path.isfile(full_path):
                    raw_size = os.path.getsize(full_path)
                    time_str, seconds = get_video_duration(full_path)
                    
                    file_node = {
                        'name': name,
                        'path': full_path,
                        'type': 'file',
                        'size_str': format_size(raw_size),
                        'raw_size': raw_size,
                        'duration_str': time_str,
                        'duration_sec': seconds
                    }
                    node['children'].append(file_node)
                    
                elif os.path.isdir(full_path):
                    child_node = self.scan_recursive(full_path)
                    node['children'].append(child_node)
        except:
            pass
            
        return node
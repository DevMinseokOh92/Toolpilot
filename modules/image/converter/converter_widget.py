import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QHBoxLayout, QFrame, QApplication, QSizePolicy) # QSizePolicy 추가됨
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QFileDialog

from .converter_logic import ImageConverterLogic
from modules.ui.custom_msg import CustomMessageBox

# ▼ [UI] 드래그 앤 드롭 존
class DropZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.parent_widget = parent

        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #666;
                border-radius: 10px;
                background-color: #2b2b2b;
            }
            QFrame:hover {
                border-color: #0078D7;
                background-color: #333;
            }
        """)

        layout = QVBoxLayout(self)
        self.label = QLabel("여기에 이미지를 드래그하세요")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #aaa; font-size: 16px; border: none; background: transparent;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("border: 2px dashed #00fa9a; background-color: #333; border-radius: 10px;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("border: 2px dashed #666; border-radius: 10px; background-color: #2b2b2b;")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("border: 2px dashed #666; border-radius: 10px; background-color: #2b2b2b;")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))]
        
        if image_files:
            self.parent_widget.run_conversion(image_files)
        else:
            self.parent_widget.show_message("오류", "이미지 파일만 넣어주세요!")

# ▼ [UI] 메인 변환 위젯
class ImageConverterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.logic = ImageConverterLogic()
        self.selected_format = "PNG"
        self.format_buttons = []
        
        self.descriptions = {
            "PNG": "✨ 투명 배경을 유지하며, 화질 저하가 없는 무손실 이미지입니다.",
            "JPG": "📉 용량을 줄여주지만, 투명한 배경은 흰색으로 채워집니다.",
            "ICO": "📂 폴더나 프로그램 아이콘용 파일입니다. (256x256 리사이징)",
            "WEBP": "🌐 인터넷/블로그용으로 최적화된 초경량 이미지입니다.",
            "PDF": "📄 이미지를 문서 파일로 저장합니다. (인쇄/보관용)"
        }
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # 1. 타이틀
        title_lbl = QLabel("이미지 변환기 (Image Converter)")
        title_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # 2. 포맷 선택 버튼
        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)
        
        formats = [
            ("PNG", "PNG (투명)"),
            ("JPG", "JPG (압축)"),
            ("ICO", "ICON (아이콘)"),
            ("WEBP", "WEBP (웹)"),
            ("PDF", "PDF (문서)")
        ]

        for fmt_code, fmt_desc in formats:
            btn = QPushButton(fmt_desc)
            btn.setCheckable(True)
            btn.setFixedSize(140, 50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, code=fmt_code, b=btn: self.on_format_changed(code, b))
            
            format_layout.addWidget(btn)
            self.format_buttons.append((btn, fmt_code))

        self.format_buttons[0][0].setChecked(True)
        self.update_button_styles()

        layout.addLayout(format_layout)

        # 3. 설명 라벨
        self.lbl_desc = QLabel(self.descriptions["PNG"])
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setStyleSheet("color: #bbb; font-size: 14px; margin-top: 5px; margin-bottom: 5px;")
        layout.addWidget(self.lbl_desc)

        # 4. [수정] 드래그 앤 드롭 존 (최대 크기로 확장)
        self.drop_zone = DropZone(self)
        # 고정 높이 삭제: self.drop_zone.setFixedHeight(250)
        # 정책 변경: 수직(Vertical) 방향으로 최대한 늘어나라(Expanding)
        self.drop_zone.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.drop_zone)

        # 5. 하단 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.addStretch() 

        self.btn_upload = QPushButton("📂 파일 직접 선택")
        self.btn_upload.setFixedSize(180, 45)
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton { background-color: #0078D7; color: white; font-size: 14px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #005a9e; }
        """)
        self.btn_upload.clicked.connect(self.open_file_dialog)
        btn_layout.addWidget(self.btn_upload)

        btn_layout.addSpacing(15)

        self.btn_folder = QPushButton("📁 다운로드 폴더 열기")
        self.btn_folder.setFixedSize(180, 45)
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.setStyleSheet("""
            QPushButton { background-color: #8e44ad; color: white; font-size: 14px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        self.btn_folder.clicked.connect(self.open_download_folder)
        btn_layout.addWidget(self.btn_folder)

        btn_layout.addStretch() 
        layout.addLayout(btn_layout)

        # 6. 결과 메시지
        self.lbl_result = QLabel("")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet("color: #00fa9a; font-size: 14px; margin-top: 10px; font-weight: bold;")
        layout.addWidget(self.lbl_result)

        # 하단의 빈 여백(addStretch)을 제거하여 DropZone이 바닥까지 밀고 내려오게 함
        # layout.addStretch() 
        self.setLayout(layout)

    # --- 기능 로직 ---
    def on_format_changed(self, code, clicked_btn):
        self.selected_format = code
        for btn, _ in self.format_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
        clicked_btn.setChecked(True)
        self.update_button_styles()
        self.lbl_desc.setText(self.descriptions.get(code, ""))

    def update_button_styles(self):
        for btn, _ in self.format_buttons:
            if btn.isChecked():
                btn.setStyleSheet("""
                    QPushButton { 
                        background-color: #0078D7; color: white; 
                        border: 2px solid #0078D7; border-radius: 8px; 
                        font-weight: bold; font-size: 13px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { 
                        background-color: #3d3d3d; color: #aaa; 
                        border: 2px solid #555; border-radius: 8px; 
                        font-size: 13px;
                    }
                    QPushButton:hover { 
                        background-color: #4d4d4d; border-color: #777; color: white; 
                    }
                """)

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if files:
            self.run_conversion(files)

    def open_download_folder(self):
        download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(download_path):
            os.startfile(download_path)
        else:
            self.show_message("오류", "다운로드 폴더를 찾을 수 없습니다.")

    def run_conversion(self, files):
        self.lbl_result.setText("⏳ 변환 중...")
        self.lbl_result.setStyleSheet("color: #aaa;")
        QApplication.processEvents()
        
        target_ext = self.selected_format 
        count, save_path = self.logic.convert_images(files, target_ext)
        
        if count > 0:
            self.lbl_result.setText(f"🎉 총 {count}개 파일을 {target_ext}(으)로 변환 완료!")
            self.lbl_result.setStyleSheet("color: #00fa9a; font-size: 15px; font-weight: bold;")
        else:
            self.lbl_result.setText("❌ 변환 실패")
            self.lbl_result.setStyleSheet("color: #ff6b6b;")

    def show_message(self, title, text):
        CustomMessageBox(title, text, is_question=False, parent=self).exec()
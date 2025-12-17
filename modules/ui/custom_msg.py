from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QWidget)
from PyQt6.QtCore import Qt
from .title_bar import CustomTitleBar

class CustomMessageBox(QDialog):
    def __init__(self, title, text, is_question=False, parent=None):
        super().__init__(parent)
        
        # 1. 프레임리스 설정
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 280) 

        if parent:
            self.center_on_parent(parent)

        # 2. 메인 컨테이너 (둥근 테두리 + 배경색 통일)
        container = QWidget(self)
        container.setGeometry(0, 0, 420, 280) 
        container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 10px;
            }
            QLabel { color: #ddd; font-size: 13px; border: none; }
            QPushButton { 
                background-color: #555; color: white; border: none; 
                padding: 8px 20px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #666; }
            /* '예/확인' 버튼은 파란색 포인트 */
            QPushButton#BtnYes { background-color: #0078D7; }
            QPushButton#BtnYes:hover { background-color: #005a9e; }
        """)

        layout_total = QVBoxLayout(container)
        layout_total.setContentsMargins(0, 0, 0, 0)
        layout_total.setSpacing(0)

        # 3. 커스텀 타이틀바
        self.title_bar = CustomTitleBar(self, title=title, can_maximize=False)
        layout_total.addWidget(self.title_bar)

        # 4. 내용물 (아이콘 + 텍스트)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 20, 30, 20)

        # 아이콘 (이모지로 대체)
        icon_text = "❓" if is_question else "ℹ️"
        lbl_icon = QLabel(icon_text)
        lbl_icon.setStyleSheet("font-size: 30px; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(lbl_icon)
        
        # 메시지 텍스트
        self.lbl_text = QLabel(text)
        self.lbl_text.setWordWrap(True) # 줄바꿈 허용
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_text.setStyleSheet("background: transparent; margin-top: 10px;")
        content_layout.addWidget(self.lbl_text)

        layout_total.addLayout(content_layout)

        # 5. 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 0, 20, 20)
        btn_layout.setSpacing(10)
        
        if is_question:
            self.btn_yes = QPushButton("예")
            self.btn_yes.setObjectName("BtnYes") # 파란색 스타일 적용
            self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_yes.clicked.connect(self.accept) # Ok 역할
            
            self.btn_no = QPushButton("아니요")
            self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_no.clicked.connect(self.reject)  # Cancel 역할
            
            btn_layout.addStretch()
            btn_layout.addWidget(self.btn_yes)
            btn_layout.addWidget(self.btn_no)
            btn_layout.addStretch()
        else:
            self.btn_ok = QPushButton("확인")
            self.btn_ok.setObjectName("BtnYes")
            self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_ok.clicked.connect(self.accept)
            
            btn_layout.addStretch()
            btn_layout.addWidget(self.btn_ok)
            btn_layout.addStretch()

        layout_total.addLayout(btn_layout)

    def center_on_parent(self, parent):
        parent_geo = parent.geometry()
        x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
        y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
        self.move(x, y)
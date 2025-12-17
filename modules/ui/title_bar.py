from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                             QApplication, QStyle)
from PyQt6.QtCore import Qt, QSize, QPoint

class CustomTitleBar(QWidget):
    def __init__(self, parent_window, title="TukTak", can_maximize=True):
        super().__init__()
        self.parent_window = parent_window
        self.start_pos = None # 드래그 이동용
        self.setFixedHeight(35) # 타이틀바 높이 고정
        self.setStyleSheet("""
            background-color: #2b2b2b; 
            border-bottom: 1px solid #3d3d3d;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        """)
        self.can_maximize = can_maximize # 이 변수가 필요해서 저장해둠

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(5)

        # 1. 아이콘 (선택사항, 일단 텍스트로 대체하거나 로고)
        self.icon_label = QLabel("🛠️")
        self.icon_label.setStyleSheet("border: none; font-size: 14px;")
        layout.addWidget(self.icon_label)

        # 2. 제목
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #ddd; font-weight: bold; font-size: 13px; border: none;")
        layout.addWidget(self.title_label)

        layout.addStretch() # 버튼들을 오른쪽으로 밀기

        # 공통 버튼 스타일
        btn_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #aaa;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333;
                color: white;
            }
        """
        
        # 닫기 버튼은 빨간색 호버
        close_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #aaa;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
        """

        # 3. 버튼들 (최소화, 최대화, 닫기)
        
        # [최소화]
        self.btn_min = QPushButton("─")
        self.btn_min.setFixedSize(45, 35)
        self.btn_min.setStyleSheet(btn_style)
        self.btn_min.clicked.connect(self.minimize_window)
        layout.addWidget(self.btn_min)

        # [최대화] (다이얼로그에는 보통 없음)
        if can_maximize:
            self.btn_max = QPushButton("☐")
            self.btn_max.setFixedSize(45, 35)
            self.btn_max.setStyleSheet(btn_style)
            self.btn_max.clicked.connect(self.maximize_restore_window)
            layout.addWidget(self.btn_max)

        # [닫기]
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(45, 35)
        self.btn_close.setStyleSheet(close_style)
        self.btn_close.clicked.connect(self.close_window)
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

    # --- 기능 로직 ---
    def minimize_window(self):
        self.parent_window.showMinimized()

    def maximize_restore_window(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_max.setText("☐")
        else:
            self.parent_window.showMaximized()
            self.btn_max.setText("❐") # 겹친 사각형 아이콘 느낌

    def close_window(self):
        self.parent_window.close()

    # --- 창 드래그 이동 (핵심!) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.start_pos = None
    
    # 제목 변경시 업데이트
    def setTitle(self, title):
        self.title_label.setText(title)

    def mouseDoubleClickEvent(self, event):
    # 왼쪽 버튼 더블클릭이고, 최대화 기능이 켜져있을 때만 동작
        if event.button() == Qt.MouseButton.LeftButton and self.can_maximize:
            self.maximize_restore_window()
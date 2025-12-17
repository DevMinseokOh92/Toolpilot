import sys
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QHBoxLayout, QVBoxLayout, QPushButton, 
                             QStackedWidget, QLabel, QFrame, QSizeGrip, QStyle)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QPoint
from PyQt6.QtGui import QPalette, QColor, QIcon, QCursor

# 모듈 임포트
from modules.system.file_manager.tree_widget import FolderTreeWidget
from modules.pdf.splitter.split_widget import PdfSplitWidget
from modules.pdf.merger.merge_widget import PdfMergeWidget
from modules.image.converter.converter_widget import ImageConverterWidget
from modules.image.to_pdf.img_to_pdf_widget import ImageToPdfWidget
from modules.system.care.cleaner_widget import SystemCareWidget
from modules.ui.title_bar import CustomTitleBar
from modules.system.organizer.dup_name_widget import DuplicateNameWidget
from modules.system.organizer.dup_file_widget import DuplicateFileWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 작업 표시줄 아이콘
        myappid = 'mycompany.toolpilot.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        # 윈도우 설정
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1000, 700)
        self.center_window()

        # [NEW] 리사이징을 위한 변수
        self._grip_size = 10 # 가장자리 감지 범위 (픽셀)
        self.side_grip_mode = 0 # 0: None, 1: Left, 2: Top, ... (방향)

        # 메인 컨테이너
        self.container = QWidget()
        self.container.setStyleSheet("QWidget#MainContainer { background-color: #2b2b2b; border: 1px solid #444; border-radius: 10px; }")
        self.container.setObjectName("MainContainer")
        self.setCentralWidget(self.container)
        
        # 마우스 추적 활성화 (리사이징 위해 필수)
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)

        self.layout_total = QVBoxLayout(self.container)
        self.layout_total.setContentsMargins(0, 0, 0, 0)
        self.layout_total.setSpacing(0)

        # 타이틀바
        self.title_bar = CustomTitleBar(self, title="ToolPilot - 올인원 도구 상자", can_maximize=True)
        self.layout_total.addWidget(self.title_bar)

        # 내용물
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5) # 테두리 리사이징을 위해 약간의 여백 둠
        content_layout.setSpacing(0)

        self.is_expanded = True
        self.original_texts = {} 
        self.category_btns = []

        self.sidebar = QWidget()
        self.sidebar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #333; border-bottom-left-radius: 10px;") 
        self.sidebar.setFixedWidth(220)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 20)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_box = QHBoxLayout()
        top_box.setContentsMargins(15, 0, 15, 0)

        self.btn_toggle = QPushButton("☰") 
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(30, 30)
        self.btn_toggle.setStyleSheet("color: white; border: none; font-size: 20px; font-weight: bold;")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        
        self.lbl_logo = QLabel("ToolPilot")
        self.lbl_logo.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-left: 10px;")
        
        top_box.addWidget(self.btn_toggle)
        top_box.addWidget(self.lbl_logo)
        top_box.addStretch()
        sidebar_layout.addLayout(top_box)
        sidebar_layout.addSpacing(10)

        self.buttons = [] 

        self.add_category_header(sidebar_layout, "SYSTEM")
        self.btn_tree = self.add_menu_button(sidebar_layout, "📂", "파일 관리자")
        self.btn_clean = self.add_menu_button(sidebar_layout, "🧹", "시스템 케어")

        self.btn_dup_name = self.add_menu_button(sidebar_layout, "🔤", "파일명 중복")
        self.btn_dup_file = self.add_menu_button(sidebar_layout, "👯", "파일 중복")

        self.add_category_header(sidebar_layout, "PDF TOOLS")
        self.btn_pdf_split = self.add_menu_button(sidebar_layout, "✂️", "PDF 자르기")
        self.btn_pdf_merge = self.add_menu_button(sidebar_layout, "📄", "PDF 합치기")

        self.add_category_header(sidebar_layout, "IMAGE TOOLS")
        self.btn_img_conv = self.add_menu_button(sidebar_layout, "🖼️", "이미지 변환")
        self.btn_img_pdf = self.add_menu_button(sidebar_layout, "📑", "이미지 to PDF")

        sidebar_layout.addStretch()

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("QWidget { background-color: #1e1e1e; border-bottom-right-radius: 10px; }")
        
        self.pages.addWidget(FolderTreeWidget())   # 0
        self.pages.addWidget(SystemCareWidget())   # 1
        self.pages.addWidget(PdfSplitWidget())     # 2
        self.pages.addWidget(PdfMergeWidget())     # 3
        self.pages.addWidget(ImageConverterWidget()) # 4
        self.pages.addWidget(ImageToPdfWidget())     # 5
        self.pages.addWidget(DuplicateNameWidget()) # 6
        self.pages.addWidget(DuplicateFileWidget()) # 7

        self.btn_tree.clicked.connect(lambda: self.change_page(0, self.btn_tree))
        self.btn_clean.clicked.connect(lambda: self.change_page(1, self.btn_clean))
        
        self.btn_dup_name.clicked.connect(lambda: self.change_page(6, self.btn_dup_name))
        self.btn_dup_file.clicked.connect(lambda: self.change_page(7, self.btn_dup_file))
        
        self.btn_pdf_split.clicked.connect(lambda: self.change_page(2, self.btn_pdf_split))
        self.btn_pdf_merge.clicked.connect(lambda: self.change_page(3, self.btn_pdf_merge))
        self.btn_img_conv.clicked.connect(lambda: self.change_page(4, self.btn_img_conv))
        self.btn_img_pdf.clicked.connect(lambda: self.change_page(5, self.btn_img_pdf))

        self.btn_tree.click() 

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.pages)
        self.layout_total.addWidget(content_widget)

        # 기존 SizeGrip 제거 (우리가 직접 구현함)
        
        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(300) 
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.anim.finished.connect(self.on_anim_finished)

    # ==========================================
    # [NEW] 창 크기 조절 (Resizing) 로직
    # ==========================================
    def mousePressEvent(self, event):
        self.side_grip_mode = self._check_grip(event.pos())
        if self.side_grip_mode:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 1. 마우스 모양 변경
        if not self.side_grip_mode:
            mode = self._check_grip(event.pos())
            self.set_cursor_shape(mode)
        
        # 2. 드래그로 크기 변경
        if self.side_grip_mode and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            rect = self.geometry()
            
            # 방향별 처리
            if self.side_grip_mode == 1: # Left
                rect.setLeft(rect.left() + delta.x())
            elif self.side_grip_mode == 2: # Top
                rect.setTop(rect.top() + delta.y())
            elif self.side_grip_mode == 3: # Right
                rect.setRight(rect.right() + delta.x())
            elif self.side_grip_mode == 4: # Bottom
                rect.setBottom(rect.bottom() + delta.y())
            elif self.side_grip_mode == 5: # TopLeft
                rect.setTopLeft(rect.topLeft() + delta)
            elif self.side_grip_mode == 6: # TopRight
                rect.setTopRight(rect.topRight() + delta)
            elif self.side_grip_mode == 7: # BottomLeft
                rect.setBottomLeft(rect.bottomLeft() + delta)
            elif self.side_grip_mode == 8: # BottomRight
                rect.setBottomRight(rect.bottomRight() + delta)

            # 최소 크기 제한
            if rect.width() > 600 and rect.height() > 400:
                self.setGeometry(rect)
                self._drag_pos = event.globalPosition().toPoint()
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.side_grip_mode = 0
        super().mouseReleaseEvent(event)

    def _check_grip(self, pos):
        # 마우스 위치가 어느 가장자리인지 판별
        w, h = self.width(), self.height()
        left = pos.x() < self._grip_size
        right = pos.x() > w - self._grip_size
        top = pos.y() < self._grip_size
        bottom = pos.y() > h - self._grip_size

        if top and left: return 5
        if top and right: return 6
        if bottom and left: return 7
        if bottom and right: return 8
        if left: return 1
        if top: return 2
        if right: return 3
        if bottom: return 4
        return 0

    def set_cursor_shape(self, mode):
        if mode in (1, 3): self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif mode in (2, 4): self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif mode in (5, 8): self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif mode in (6, 7): self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)

    # --- 기존 함수들 ---
    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def toggle_sidebar(self):
        if self.is_expanded:
            self.anim.setStartValue(220)
            self.anim.setEndValue(60)
            self.lbl_logo.hide()
            self.anim.start()
        else:
            self.anim.setStartValue(60)
            self.anim.setEndValue(220)
            self.lbl_logo.show()
            for header in self.category_btns: header.show()
            for btn in self.buttons:
                full_text = f"  {self.original_texts[btn][0]}   {self.original_texts[btn][1]}"
                btn.setText(full_text)
                btn.setStyleSheet(btn.styleSheet().replace("text-align: center;", "text-align: left;").replace("padding-left: 0px;", "padding-left: 20px;"))
                btn.setToolTip("")
            self.anim.start()
        self.is_expanded = not self.is_expanded

    def on_anim_finished(self):
        self.sidebar.setFixedWidth(self.anim.endValue())
        if not self.is_expanded:
            for header in self.category_btns: header.hide()
            for btn in self.buttons:
                icon_text = self.original_texts[btn][0]
                btn.setText(icon_text) 
                btn.setStyleSheet(btn.styleSheet().replace("text-align: left;", "text-align: center;").replace("padding-left: 20px;", "padding-left: 0px;"))
                btn.setToolTip(self.original_texts[btn][1])

    def add_category_header(self, layout, text):
        label = QLabel(text)
        label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; padding-left: 15px; margin-top: 10px;")
        layout.addWidget(label)
        self.category_btns.append(label)

    def add_menu_button(self, layout, icon, text):
        full_text = f"  {icon}   {text}"
        btn = QPushButton(full_text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #e0e0e0; text-align: left; padding: 12px; padding-left: 20px; font-size: 14px; border: none; border-left: 3px solid transparent; }
            QPushButton:hover { background-color: #3a3a3a; color: white; }
            QPushButton:checked { background-color: #333; color: white; border-left: 3px solid #3498db; font-weight: bold; }
        """)
        layout.addWidget(btn)
        self.buttons.append(btn)
        self.original_texts[btn] = (icon, text)
        return btn

    def change_page(self, index, active_btn):
        self.pages.setCurrentIndex(index)
        for btn in self.buttons: btn.setChecked(False)
        active_btn.setChecked(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Malgun Gothic")
    app.setFont(font)
    
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
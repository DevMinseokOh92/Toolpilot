import os
from PyPDF2 import PdfMerger
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QListWidget, QHBoxLayout, QFileDialog, QAbstractItemView, QListWidgetItem)
from PyQt6.QtCore import Qt
from modules.ui.custom_msg import CustomMessageBox
from ...ui.pdf_preview import PdfPreviewWidget

class PdfMergeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # === [좌측] 파일 목록 및 컨트롤 ===
        left_layout = QVBoxLayout()
        
        title = QLabel("PDF 합치기 (Merger)")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        left_layout.addWidget(title)

        # 리스트 위젯
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #2b2b2b; color: white; border: 1px solid #555; border-radius: 5px; font-size: 14px; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #0078D7; }
        """)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.list_widget)

        # 컨트롤 버튼들
        btn_box = QHBoxLayout()
        
        self.btn_add = QPushButton("➕ 파일 추가")
        self.btn_add.clicked.connect(self.add_files)
        
        self.btn_remove = QPushButton("➖ 제거")
        self.btn_remove.clicked.connect(self.remove_file)
        
        self.btn_folder = QPushButton("📁 폴더 열기")
        self.btn_folder.clicked.connect(self.open_current_folder)
        
        self.btn_clear = QPushButton("🗑️ 전체 삭제")
        self.btn_clear.clicked.connect(self.clear_all)

        for btn in [self.btn_add, self.btn_remove, self.btn_folder, self.btn_clear]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("background-color: #3d3d3d; color: white; padding: 8px; border-radius: 5px;")
            btn_box.addWidget(btn)
        
        left_layout.addLayout(btn_box)

        # 실행 버튼
        self.btn_run = QPushButton("📄 하나로 합치기")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setStyleSheet("background-color: #27ae60; color: white; font-size: 16px; font-weight: bold; border-radius: 8px; margin-top: 10px;")
        self.btn_run.clicked.connect(self.run_merge)
        left_layout.addWidget(self.btn_run)

        # === [우측] 미리보기 영역 ===
        right_layout = QVBoxLayout()
        lbl_preview = QLabel("선택한 파일 미리보기")
        lbl_preview.setStyleSheet("color: #aaa; font-weight: bold;")
        right_layout.addWidget(lbl_preview)

        # [수정] 세로 모드(is_vertical=True)로 생성!
        self.preview = PdfPreviewWidget(is_vertical=True)
        
        # 미리보기 영역이 꽉 차게 확장
        right_layout.addWidget(self.preview)
        
        # 전체 레이아웃 비율 1:1
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 1)
        
        self.setLayout(layout)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF Files (*.pdf)")
        if files:
            for f in files:
                item = QListWidgetItem(os.path.basename(f))
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setToolTip(f)
                self.list_widget.addItem(item)
            
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(self.list_widget.count()-1)
                self.on_item_clicked(self.list_widget.currentItem())

    def remove_file(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            self.preview.load_pdf(None)

    def clear_all(self):
        self.list_widget.clear()
        self.preview.load_pdf(None)

    def open_current_folder(self):
        path_to_open = os.path.join(os.path.expanduser("~"), "Downloads")
        current_item = self.list_widget.currentItem()
        if current_item:
            full_path = current_item.data(Qt.ItemDataRole.UserRole)
            if full_path and os.path.exists(full_path):
                path_to_open = os.path.dirname(full_path)
        os.startfile(path_to_open)

    def on_item_clicked(self, item):
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            self.preview.load_pdf(path)

    def run_merge(self):
        count = self.list_widget.count()
        if count < 2:
            CustomMessageBox("알림", "합치려면 최소 2개 이상의 파일이 필요합니다.", parent=self).exec()
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "저장할 파일명", "merged.pdf", "PDF Files (*.pdf)")
        if not save_path: return

        try:
            merger = PdfMerger()
            for i in range(count):
                item = self.list_widget.item(i)
                path = item.data(Qt.ItemDataRole.UserRole)
                merger.append(path)
            
            merger.write(save_path)
            merger.close()
            
            CustomMessageBox("성공", "성공적으로 합쳤습니다!", parent=self).exec()
            os.startfile(os.path.dirname(save_path))

        except Exception as e:
            CustomMessageBox("오류", f"병합 실패:\n{e}", parent=self).exec()
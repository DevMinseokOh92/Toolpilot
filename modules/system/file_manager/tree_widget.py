import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QFileDialog, QLabel, QApplication, 
                             QHBoxLayout, QAbstractItemView, QCheckBox, 
                             QFileIconProvider)
from PyQt6.QtCore import Qt, QFileInfo, QSize

from .rename_dialog import RenameDialog
from .tree_logic import TreeActionHandler
# [수정] SORT_TYPE_ROLE 추가 임포트
from .tree_components import SortableTreeWidgetItem, SORT_TYPE_ROLE
from .worker import LoadingDialog, FolderScanWorker

class FolderTreeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_folder = None 
        self.logic = TreeActionHandler(self)
        self.icon_provider = QFileIconProvider()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        top_layout = QHBoxLayout()
        self.label = QLabel("폴더를 선택하세요.")
        self.label.setStyleSheet("color: #aaa; font-size: 14px;")
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        
        self.chk_ignore = QCheckBox("잡동사니 숨기기 (.git, venv 등)")
        self.chk_ignore.setChecked(True)
        self.chk_ignore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_ignore.setStyleSheet("QCheckBox { color: #00fa9a; font-weight: bold; } QCheckBox::indicator { width: 18px; height: 18px; }")
        self.chk_ignore.clicked.connect(lambda: self.process_folder(self.current_folder))
        top_layout.addWidget(self.chk_ignore)
        layout.addLayout(top_layout)

        btn_layout = QHBoxLayout()
        self.btn_open = QPushButton("📂 폴더 선택")
        self.btn_open.clicked.connect(self.open_folder_dialog)
        
        self.btn_save = QPushButton("💾 목록 저장")
        self.btn_save.clicked.connect(lambda: self.logic.save_tree_to_downloads(self.tree.invisibleRootItem()))
        self.btn_save.setEnabled(False)

        self.btn_rename = QPushButton("✏️ 이름 변경")
        self.btn_rename.clicked.connect(self.open_rename_dialog)
        self.btn_rename.setEnabled(False)

        self.btn_explorer = QPushButton("📁 폴더 열기")
        self.btn_explorer.clicked.connect(lambda: self.logic.open_file_explorer(self.current_folder, self.tree.selectedItems()))
        self.btn_explorer.setEnabled(False)

        buttons = [
            (self.btn_open, "#0078D7"), 
            (self.btn_save, "#27ae60"), 
            (self.btn_rename, "#e67e22"), 
            (self.btn_explorer, "#8e44ad")
        ]

        for btn, color in buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {color}; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["이름", "크기", "재생 시간", "삭제"]) 
        self.tree.setSortingEnabled(True) 
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self.on_double_click)
        self.tree.setIconSize(QSize(20, 20)) 

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 90); self.tree.setColumnWidth(2, 90); self.tree.setColumnWidth(3, 60)
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; font-family: 'Malgun Gothic'; font-size: 13px; }
            QHeaderView::section { background-color: #2d2d2d; color: #ffffff; padding: 5px; border-left: 1px solid #3d3d3d; font-weight: bold; }
            QTreeWidget::item { padding: 5px; }
            QTreeWidget::item:hover { background-color: #333333; }
            QTreeWidget::item:selected { background-color: #0078D7; color: white; }
        """)
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def process_folder(self, folder_path):
        if not folder_path: return

        self.current_folder = folder_path
        self.label.setText(f"📂 {folder_path}")
        self.tree.clear()
        
        self.loading = LoadingDialog(self)
        self.loading.show()
        
        is_filter_on = self.chk_ignore.isChecked()
        self.worker = FolderScanWorker(folder_path, filter_hidden=is_filter_on)
        self.worker.finished_data.connect(self.on_scan_finished)
        self.worker.start()

    def on_scan_finished(self, data):
        self.loading.close()
        self.tree.setSortingEnabled(False)
        self.populate_tree(self.tree.invisibleRootItem(), data)
        self.tree.setSortingEnabled(True)
        
        self.btn_save.setEnabled(True)
        self.btn_rename.setEnabled(True)
        self.btn_explorer.setEnabled(True)

    def populate_tree(self, parent_item, data):
        # 데이터가 섞여서 오더라도 여기서 먼저 '폴더'와 '파일'을 분리해서 넣는게 안전함
        # 하지만 worker에서 이미 이름순 정렬은 되어 있음.
        # TreeWidget 정렬 로직이 Type -> Name 순이므로 순서대로 넣기만 해도 됨.
        
        for child in data.get('children', []):
            item = SortableTreeWidgetItem(parent_item)
            item.setText(0, child['name'])
            item.setData(0, Qt.ItemDataRole.UserRole, child['path'])
            
            # 시스템 아이콘
            file_info = QFileInfo(child['path'])
            icon = self.icon_provider.icon(file_info)
            item.setIcon(0, icon)
            
            if child['type'] == 'file':
                # [NEW] 파일이라는 표식 (1)
                item.setData(0, SORT_TYPE_ROLE, 1)
                
                item.setText(1, child['size_str'])
                item.setData(1, Qt.ItemDataRole.UserRole, child['raw_size'])
                item.setText(2, child['duration_str'])
                item.setData(2, Qt.ItemDataRole.UserRole, child['duration_sec'])
            else:
                # [NEW] 폴더라는 표식 (0) -> 숫자가 작으니 정렬 시 위로 감
                item.setData(0, SORT_TYPE_ROLE, 0)
                
                item.setText(1, "-"); item.setData(1, Qt.ItemDataRole.UserRole, -1)
                item.setText(2, "-"); item.setData(2, Qt.ItemDataRole.UserRole, -1)

            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            btn_widget = QWidget(); btn_widget.setStyleSheet("background-color: transparent;")
            btn_layout = QHBoxLayout(btn_widget); btn_layout.setContentsMargins(0, 0, 0, 0); btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 
            btn_del = QPushButton("❌"); btn_del.setFixedSize(20, 20); btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 10px; } QPushButton:hover { background-color: #c0392b; border-radius: 3px; }")
            btn_del.clicked.connect(lambda _, p=child['path'], i=item: self.logic.delete_item(p, i, self.tree))
            btn_layout.addWidget(btn_del)
            self.tree.setItemWidget(item, 3, btn_widget)
            
            if child['type'] == 'folder':
                self.populate_tree(item, child)

    def on_double_click(self, item, column):
        if column == 3: return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            os.startfile(path)

    def open_rename_dialog(self):
        if not self.current_folder: return
        selected_items = self.tree.selectedItems()
        target_files = []
        if selected_items:
            for item in selected_items:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path and path != self.current_folder: target_files.append(path)
        final_targets = target_files if target_files else None
        dialog = RenameDialog(self.current_folder, self, target_files=final_targets)
        if dialog.exec(): self.process_folder(self.current_folder)

    def open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder: self.process_folder(folder)
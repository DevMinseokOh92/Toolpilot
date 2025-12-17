import os
import hashlib
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QTreeWidget, QTreeWidgetItem, 
                             QFileDialog, QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt
from ...ui.custom_msg import CustomMessageBox

class DuplicateFileWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.folders = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("중복 파일(내용) 제거기")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("파일명이 달라도 내용이 완전히 똑같은 파일을 찾아냅니다.")
        desc.setStyleSheet("color: #aaa;")
        layout.addWidget(desc)

        # 1. 폴더 목록
        folder_group = QGroupBox("검사 대상 폴더")
        folder_group.setStyleSheet("QGroupBox { color: #00fa9a; font-weight: bold; border: 1px solid #555; border-radius: 5px; }")
        f_layout = QVBoxLayout(folder_group)
        
        self.list_folders = QListWidget()
        self.list_folders.setStyleSheet("background-color: #2b2b2b; color: #ddd; border: none;")
        self.list_folders.setFixedHeight(80)
        f_layout.addWidget(self.list_folders)

        btn_f_layout = QHBoxLayout()
        btn_add = QPushButton("➕ 폴더 추가")
        btn_add.clicked.connect(self.add_folder)
        btn_clear = QPushButton("🗑️ 목록 초기화")
        btn_clear.clicked.connect(self.clear_folders)
        for btn in [btn_add, btn_clear]:
            btn.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px; border-radius: 3px;")
            btn_f_layout.addWidget(btn)
        f_layout.addLayout(btn_f_layout)
        layout.addWidget(folder_group)

        # 2. 실행 버튼
        self.btn_scan = QPushButton("🔍 내용 중복 검사 시작 (시간이 걸릴 수 있음)")
        self.btn_scan.setFixedHeight(45)
        self.btn_scan.setStyleSheet("background-color: #0078D7; color: white; font-size: 14px; font-weight: bold; border-radius: 5px;")
        self.btn_scan.clicked.connect(self.scan_duplicates)
        layout.addWidget(self.btn_scan)

        # 3. 결과 트리
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["파일 정보", "경로", "삭제"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(2, 80)
        self.tree.setStyleSheet("QTreeWidget { background-color: #1e1e1e; color: #ddd; border: 1px solid #444; }")
        layout.addWidget(self.tree)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder and folder not in self.folders:
            self.folders.append(folder)
            self.list_folders.addItem(folder)

    def clear_folders(self):
        self.folders = []
        self.list_folders.clear()
        self.tree.clear()

    def get_file_hash(self, path):
        # 파일 내용을 읽어서 MD5 해시 생성 (내용이 같으면 해시값도 같음)
        h = hashlib.md5()
        try:
            with open(path, "rb") as f:
                # 큰 파일 대비 청크 단위 읽기
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest()
        except: return None

    def scan_duplicates(self):
        if not self.folders:
            CustomMessageBox("알림", "폴더를 추가해주세요.", parent=self).exec()
            return

        self.tree.clear()
        self.btn_scan.setText("검사 중...")
        self.btn_scan.setEnabled(False)
        QApplication.processEvents() # UI 갱신

        # 1차: 크기 비교 (크기가 다르면 내용도 다름 -> 속도 최적화)
        size_map = {}
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(path)
                        if sz not in size_map: size_map[sz] = []
                        size_map[sz].append(path)
                    except: pass
        
        # 2차: 해시 비교 (크기가 같은 애들끼리만 진짜 내용 비교)
        hash_map = {}
        for size, paths in size_map.items():
            if len(paths) < 2: continue # 중복 가능성 없음
            
            for path in paths:
                h = self.get_file_hash(path)
                if h:
                    if h not in hash_map: hash_map[h] = []
                    hash_map[h].append(path)

        # 결과 표시
        count = 0
        for h, paths in hash_map.items():
            if len(paths) > 1:
                count += 1
                # 그룹 헤더 (크기 정보 표시)
                size_str = f"{os.path.getsize(paths[0]) / 1024:.1f} KB"
                root_item = QTreeWidgetItem(self.tree)
                root_item.setText(0, f"중복 그룹 #{count} (크기: {size_str})")
                root_item.setExpanded(True)
                
                for p in paths:
                    child = QTreeWidgetItem(root_item)
                    child.setText(0, os.path.basename(p))
                    child.setText(1, p)
                    
                    # 삭제 버튼
                    btn_del = QPushButton("삭제")
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.setStyleSheet("background-color: #c0392b; color: white; border: none; border-radius: 3px;")
                    btn_del.clicked.connect(lambda _, fp=p, it=child: self.delete_file(fp, it))
                    
                    self.tree.setItemWidget(child, 2, btn_del)

        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 내용 중복 검사 시작")
        
        if count == 0:
            CustomMessageBox("결과", "중복된 파일이 없습니다.", parent=self).exec()
        else:
            CustomMessageBox("완료", f"총 {count}그룹의 중복 파일을 찾았습니다.", parent=self).exec()

    def delete_file(self, path, item):
        msg = CustomMessageBox("삭제 확인", f"이 파일을 영구 삭제하시겠습니까?\n{path}", is_question=True, parent=self)
        if msg.exec() == 1:
            try:
                os.remove(path)
                # UI 제거
                parent = item.parent()
                parent.removeChild(item)
                # 만약 그룹에 남은게 1개면 그룹 자체도 의미 없으니 제거? (선택사항)
            except Exception as e:
                CustomMessageBox("오류", f"삭제 실패: {e}", parent=self).exec()

# import 누락 방지
from PyQt6.QtWidgets import QApplication
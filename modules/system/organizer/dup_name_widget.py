import os
import difflib # 문자열 비교용 라이브러리
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QTreeWidget, QTreeWidgetItem, 
                             QFileDialog, QHeaderView, QLineEdit, QGroupBox, QApplication)
from PyQt6.QtCore import Qt
from ...ui.custom_msg import CustomMessageBox

class DuplicateNameWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.folders = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("파일명 공통 패턴(중복 문자열) 찾기")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("파일명에 반복적으로 등장하는 문구(예: - JAVPLAYER)를 찾아내고 일괄 변경합니다.")
        desc.setStyleSheet("color: #aaa; font-size: 13px;")
        layout.addWidget(desc)

        # 1. 검사 대상 폴더 목록
        folder_group = QGroupBox("1. 검사할 폴더 목록")
        folder_group.setStyleSheet("QGroupBox { color: #00fa9a; font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
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
        self.btn_scan = QPushButton("🔍 공통 문자열 패턴 분석 시작")
        self.btn_scan.setFixedHeight(40)
        self.btn_scan.setStyleSheet("background-color: #0078D7; color: white; font-size: 14px; font-weight: bold; border-radius: 5px;")
        self.btn_scan.clicked.connect(self.scan_duplicates)
        layout.addWidget(self.btn_scan)

        # 3. 결과 트리
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["공통된 문자열 / 파일명", "경로"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #1e1e1e; color: #ddd; border: 1px solid #444; } 
            QHeaderView::section { background-color: #333; color: white; }
            QTreeWidget::item:selected { background-color: #0078D7; color: white; }
        """)
        # [NEW] 아이템 클릭 시 입력창에 텍스트 넣기 연결
        self.tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree)

        # 4. 일괄 변경 도구
        rename_group = QGroupBox("2. 문자열 일괄 변경 (패턴 클릭 시 자동 입력)")
        rename_group.setStyleSheet("QGroupBox { color: #f1c40f; font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 10px; }")
        r_layout = QHBoxLayout(rename_group)
        
        self.input_find = QLineEdit()
        self.input_find.setPlaceholderText("찾을 문자 (위 목록에서 선택하세요)")
        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("바꿀 문자 (비워두면 삭제)")
        
        for inp in [self.input_find, self.input_replace]:
            inp.setStyleSheet("background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px;")
        
        btn_rename = QPushButton("✏️ 변경 실행")
        btn_rename.setStyleSheet("background-color: #e67e22; color: white; padding: 5px 15px; border-radius: 3px; font-weight: bold;")
        btn_rename.clicked.connect(self.run_rename)

        r_layout.addWidget(QLabel("찾기:"))
        r_layout.addWidget(self.input_find)
        r_layout.addWidget(QLabel("바꾸기:"))
        r_layout.addWidget(self.input_replace)
        r_layout.addWidget(btn_rename)
        
        layout.addWidget(rename_group)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder and folder not in self.folders:
            self.folders.append(folder)
            self.list_folders.addItem(folder)

    def clear_folders(self):
        self.folders = []
        self.list_folders.clear()
        self.tree.clear()

    # [NEW] 트리 아이템 클릭 시 '찾을 문자'에 자동 입력
    def on_item_clicked(self, item, column):
        # 최상위 아이템(패턴)인 경우에만
        if item.childCount() > 0:
            # "패턴 (N개)" 형식에서 패턴만 추출
            text = item.text(0)
            if " (" in text and text.endswith("개)"):
                pattern = text.rsplit(" (", 1)[0] # 뒤에서부터 첫번째 ' (' 로 자름
                self.input_find.setText(pattern)

    def scan_duplicates(self):
        if not self.folders:
            CustomMessageBox("알림", "검사할 폴더를 최소 하나 이상 추가해주세요.", parent=self).exec()
            return

        self.tree.clear()
        self.btn_scan.setText("분석 중... (시간이 걸릴 수 있습니다)")
        self.btn_scan.setEnabled(False)
        QApplication.processEvents()

        # 1. 모든 파일 수집
        all_files = []
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for f in files:
                    all_files.append((f, os.path.join(root, f)))

        # 2. 이름순 정렬 (비슷한 이름끼리 붙여놓기 위해)
        all_files.sort(key=lambda x: x[0])

        # 3. 인접한 파일끼리 비교하여 공통 패턴 추출
        patterns = set()
        
        # 파일이 너무 많으면 오래 걸리므로 최대 비교 갯수 제한 등은 나중에 고려
        for i in range(len(all_files) - 1):
            name1 = all_files[i][0]
            name2 = all_files[i+1][0]
            
            # 두 문자열의 공통 부분 찾기 (SequenceMatcher)
            match = difflib.SequenceMatcher(None, name1, name2).find_longest_match(0, len(name1), 0, len(name2))
            
            if match.size > 5: # 최소 5글자 이상 겹쳐야 의미 있는 패턴으로 간주
                substr = name1[match.a : match.a + match.size].strip()
                # 너무 흔한 숫자나 확장자만 있는 경우는 제외
                if substr and substr not in [".mp4", ".jpg", ".png", ".avi", ".mkv"]:
                    patterns.add(substr)

        # 4. 추출된 패턴이 실제로 몇 개의 파일에 포함되는지 카운트
        # (패턴이 긴 순서대로 정렬하여 보여줌)
        sorted_patterns = sorted(list(patterns), key=len, reverse=True)
        
        result_count = 0
        
        for pat in sorted_patterns:
            # 이미 처리된 파일은 제외하거나, 중복 허용? 일단 중복 허용
            matched_files = []
            for fname, fpath in all_files:
                if pat in fname:
                    matched_files.append((fname, fpath))
            
            # 2개 이상 파일에 포함된 패턴만 표시
            if len(matched_files) > 1:
                result_count += 1
                root_item = QTreeWidgetItem(self.tree)
                root_item.setText(0, f"{pat} ({len(matched_files)}개)")
                root_item.setExpanded(False) # 접어둠 (깔끔하게)
                # 데이터에 패턴 저장
                root_item.setData(0, Qt.ItemDataRole.UserRole, pat)

                for fname, fpath in matched_files:
                    child = QTreeWidgetItem(root_item)
                    child.setText(0, fname)
                    child.setText(1, fpath)
                    child.setData(1, Qt.ItemDataRole.UserRole, fpath)

        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 공통 문자열 패턴 분석 시작")

        if result_count == 0:
            CustomMessageBox("결과", "반복되는 문자열 패턴을 찾지 못했습니다.", parent=self).exec()
        else:
            CustomMessageBox("완료", f"총 {result_count}개의 공통 패턴을 발견했습니다.\n목록을 클릭하면 '찾을 문자'에 입력됩니다.", parent=self).exec()

    def run_rename(self):
        target = self.input_find.text()
        replace = self.input_replace.text()
        if not target: 
            CustomMessageBox("알림", "찾을 문자를 입력해주세요.", parent=self).exec()
            return

        count = 0
        # 현재 트리에 보이는 항목들이 아니라, 전체 파일 대상으로 변경 시도
        # (혹은 트리에 있는 것만? 사용자는 '전체'를 기대할 것임)
        
        # 안전하게 다시 스캔하며 변경
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for filename in files:
                    if target in filename:
                        old_path = os.path.join(root, filename)
                        new_filename = filename.replace(target, replace)
                        new_path = os.path.join(root, new_filename)
                        
                        try:
                            # 이미 같은 이름이 있으면 스킵
                            if not os.path.exists(new_path):
                                os.rename(old_path, new_path)
                                count += 1
                        except: pass
        
        CustomMessageBox("완료", f"총 {count}개의 파일 이름을 변경했습니다.", parent=self).exec()
        # 변경 후 목록 새로고침
        self.scan_duplicates()
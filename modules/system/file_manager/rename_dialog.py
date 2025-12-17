import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QProgressBar, QFormLayout, QDialogButtonBox, QApplication, QWidget)
from PyQt6.QtCore import Qt
from modules.ui.title_bar import CustomTitleBar

class RenameDialog(QDialog):
    # ▼▼▼ 이 부분(__init__)이 반드시 있어야 에러가 안 납니다! ▼▼▼
    def __init__(self, folder_path, parent=None, target_files=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.target_files = target_files
        
        # 1. 프레임리스 설정
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(450, 300)
        
        # 2. 부모 중앙 배치
        if parent:
            self.center_on_parent(parent)

        self.init_ui()
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    def center_on_parent(self, parent):
        parent_geo = parent.geometry()
        x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
        y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
        self.move(x, y)

    def init_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 450, 300)
        
        # 스타일시트 적용 (밑줄 잘 보이게 수정된 버전)
        container.setStyleSheet("""
            QWidget { 
                background-color: #2b2b2b; 
                border: 1px solid #555; 
                border-radius: 10px; 
            }
            QLabel { 
                color: #dddddd; 
                border: none; 
                font-size: 13px;
                font-weight: bold;
            }
            
            QLineEdit { 
                background-color: transparent; 
                color: white; 
                border: none;
                border-bottom: 1px solid #dddddd; /* 밑줄 색상: 텍스트와 동일 */
                border-radius: 0px; 
                padding-bottom: 5px;
                font-size: 14px;
            }
            
            QLineEdit:focus {
                border-bottom: 2px solid #0078D7; 
            }

            QPushButton { 
                background-color: #0078D7; 
                color: white; 
                border-radius: 5px; 
                padding: 6px; 
                border: none; 
            }
            QPushButton:hover { background-color: #005a9e; }
        """)

        layout_total = QVBoxLayout(container)
        layout_total.setContentsMargins(0, 0, 0, 0)
        
        self.title_bar = CustomTitleBar(self, title="파일 이름 일괄 변경", can_maximize=False)
        self.title_bar.setStyleSheet("border-bottom: 1px solid #3d3d3d; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        layout_total.addWidget(self.title_bar)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent; border: none;")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        info_text = "폴더 내 모든 파일을 변경합니다."
        if self.target_files:
            info_text = f"선택된 {len(self.target_files)}개의 파일만 변경합니다."
        
        lbl_info = QLabel(info_text)
        lbl_info.setStyleSheet("color: #aaa; margin-bottom: 10px; font-weight: normal;")
        layout.addWidget(lbl_info)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.input_find = QLineEdit()
        self.input_replace = QLineEdit()
        
        form_layout.addRow("찾을 문자:", self.input_find)
        form_layout.addRow("바꿀 문자:", self.input_replace)
        layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #00fa9a; font-size: 12px; margin-top: 10px; font-weight: normal;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; background-color: #3d3d3d; color: white; }
            QProgressBar::chunk { background-color: #0078D7; width: 10px; }
        """)
        layout.addWidget(self.progress_bar)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("변경 시작")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        self.buttons.accepted.connect(self.run_rename)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        layout_total.addWidget(content_widget)
        
        self.input_find.setFocus()

    def run_rename(self):
        target = self.input_find.text()
        replace = self.input_replace.text()
        
        if not target:
            self.status_label.setText("⚠️ 찾을 문자를 입력해주세요!")
            return

        files_to_work = []
        if self.target_files:
            for full_path in self.target_files:
                filename = os.path.basename(full_path)
                root = os.path.dirname(full_path)
                if target in filename:
                    files_to_work.append((root, filename))
        else:
            for root, dirs, files in os.walk(self.folder_path):
                for filename in files:
                    if target in filename:
                        files_to_work.append((root, filename))

        total_count = len(files_to_work)
        if total_count == 0:
            self.status_label.setText("⚠️ 조건에 맞는 파일이 없습니다.")
            return

        self.input_find.setEnabled(False)
        self.input_replace.setEnabled(False)
        self.buttons.setEnabled(False)
        self.progress_bar.setMaximum(total_count)
        self.progress_bar.show()

        success_count = 0
        for i, (root, filename) in enumerate(files_to_work):
            old_path = os.path.join(root, filename)
            new_filename = filename.replace(target, replace)
            new_path = os.path.join(root, new_filename)
            try:
                os.rename(old_path, new_path)
                success_count += 1
                self.status_label.setText(f"[{new_filename}] 완료 ({i+1}/{total_count})")
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()
            except Exception as e:
                print(f"Error: {e}")

        self.status_label.setText(f"🎉 총 {success_count}개 변경 완료!")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("닫기")
        self.buttons.setEnabled(True)
        self.buttons.accepted.disconnect()
        self.buttons.accepted.connect(self.accept)
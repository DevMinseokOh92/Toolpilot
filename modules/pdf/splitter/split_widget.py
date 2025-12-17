import os
from PyPDF2 import PdfReader, PdfWriter
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QFileDialog, QHBoxLayout, QRadioButton, 
                             QLineEdit, QSpinBox, QButtonGroup)
from PyQt6.QtCore import Qt
from modules.ui.custom_msg import CustomMessageBox
from ...ui.pdf_preview import PdfPreviewWidget

class PdfSplitWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_pdf = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("PDF 자르기 (Splitter)")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        file_layout = QHBoxLayout()
        self.btn_load = QPushButton("📄 PDF 불러오기")
        self.btn_load.setFixedSize(150, 40)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setStyleSheet("background-color: #0078D7; color: white; border-radius: 5px; font-weight: bold;")
        self.btn_load.clicked.connect(self.load_pdf)
        
        self.lbl_path = QLabel("선택된 파일 없음")
        self.lbl_path.setStyleSheet("color: #aaa; margin-left: 10px;")
        
        file_layout.addWidget(self.btn_load)
        file_layout.addWidget(self.lbl_path)
        layout.addLayout(file_layout)

        self.preview = PdfPreviewWidget()
        layout.addWidget(self.preview)

        # --- 옵션 영역 (스타일링 적용) ---
        opt_group_box = QWidget()
        opt_group_box.setStyleSheet("""
            QWidget { background-color: #2b2b2b; border-radius: 10px; padding: 10px; }
            /* [수정] 라디오 버튼 스타일: 크기 키우고 선택 안되면 흐리게 */
            QRadioButton { 
                color: #777; font-size: 15px; padding: 5px; 
            }
            QRadioButton::indicator { width: 18px; height: 18px; }
            QRadioButton:checked { 
                color: white; font-weight: bold; 
            }
        """)
        opt_layout = QVBoxLayout(opt_group_box)
        
        # 1. 전체 분리
        self.radio_all = QRadioButton("모든 페이지를 1장씩 분리")
        self.radio_all.setChecked(True)
        opt_layout.addWidget(self.radio_all)

        # 2. 범위 지정
        range_layout = QHBoxLayout()
        self.radio_range = QRadioButton("범위 지정 (예: 1-3, 5, 7-9)")
        self.input_range = QLineEdit()
        self.input_range.setPlaceholderText("예: 1-5, 8")
        self.input_range.setStyleSheet("background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 5px; border-radius: 4px;")
        range_layout.addWidget(self.radio_range)
        range_layout.addWidget(self.input_range)
        opt_layout.addLayout(range_layout)

        # 3. N장씩
        split_layout = QHBoxLayout()
        self.radio_split = QRadioButton("간격 자르기 (N장씩 묶음)")
        self.spin_split = QSpinBox()
        self.spin_split.setRange(2, 100)
        self.spin_split.setValue(2)
        self.spin_split.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px; border: 1px solid #555;")
        split_layout.addWidget(self.radio_split)
        split_layout.addWidget(self.spin_split)
        split_layout.addStretch()
        opt_layout.addLayout(split_layout)

        # 그룹핑 및 이벤트 연결
        self.bg_group = QButtonGroup(self)
        self.bg_group.addButton(self.radio_all)
        self.bg_group.addButton(self.radio_range)
        self.bg_group.addButton(self.radio_split)
        
        # [수정] 라디오 버튼 클릭 시 UI 상태 업데이트 연결
        self.bg_group.buttonToggled.connect(self.update_ui_state)

        layout.addWidget(opt_group_box)

        self.btn_run = QPushButton("✂️ 자르기 실행")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setStyleSheet("background-color: #e74c3c; color: white; font-size: 16px; font-weight: bold; border-radius: 8px;")
        self.btn_run.clicked.connect(self.run_split)
        self.btn_run.setEnabled(False)
        layout.addWidget(self.btn_run)

        layout.addStretch()
        self.setLayout(layout)
        
        # 초기 상태 적용
        self.update_ui_state()

    # [NEW] UI 활성화/비활성화 및 스타일 처리
    def update_ui_state(self):
        # 1. 범위 지정
        if self.radio_range.isChecked():
            self.input_range.setEnabled(True)
            self.input_range.setStyleSheet("background-color: #3d3d3d; color: white; border: 1px solid #0078D7; padding: 5px;")
        else:
            self.input_range.setEnabled(False)
            self.input_range.setStyleSheet("background-color: #222; color: #555; border: 1px solid #333; padding: 5px;") # 어둡게

        # 2. 스핀박스
        if self.radio_split.isChecked():
            self.spin_split.setEnabled(True)
            self.spin_split.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px; border: 1px solid #0078D7;")
        else:
            self.spin_split.setEnabled(False)
            self.spin_split.setStyleSheet("background-color: #222; color: #555; padding: 5px; border: 1px solid #333;")

    def load_pdf(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'PDF 선택', '', 'PDF Files (*.pdf)')
        if fname:
            self.current_pdf = fname
            self.lbl_path.setText(os.path.basename(fname))
            self.btn_run.setEnabled(True)
            self.preview.load_pdf(fname)

    def run_split(self):
        if not self.current_pdf: return

        save_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
        if not save_dir: return

        try:
            reader = PdfReader(self.current_pdf)
            total_pages = len(reader.pages)
            base_name = os.path.splitext(os.path.basename(self.current_pdf))[0]

            if self.radio_all.isChecked():
                for i in range(total_pages):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    self.save_pdf(writer, save_dir, f"{base_name}_p{i+1}.pdf")

            elif self.radio_range.isChecked():
                txt = self.input_range.text()
                if not txt:
                    raise Exception("범위를 입력해주세요.")
                ranges = txt.replace(" ", "").split(",")
                writer = PdfWriter()
                for part in ranges:
                    if "-" in part: 
                        start, end = map(int, part.split("-"))
                        for i in range(start-1, end):
                            if 0 <= i < total_pages: writer.add_page(reader.pages[i])
                    else: 
                        idx = int(part) - 1
                        if 0 <= idx < total_pages: writer.add_page(reader.pages[idx])
                
                if len(writer.pages) > 0:
                    self.save_pdf(writer, save_dir, f"{base_name}_extracted.pdf")
                else:
                    raise Exception("선택된 페이지가 없습니다.")

            elif self.radio_split.isChecked():
                step = self.spin_split.value()
                for i in range(0, total_pages, step):
                    writer = PdfWriter()
                    end = min(i + step, total_pages)
                    for page_idx in range(i, end):
                        writer.add_page(reader.pages[page_idx])
                    self.save_pdf(writer, save_dir, f"{base_name}_part{i//step + 1}.pdf")

            CustomMessageBox("성공", "작업이 완료되었습니다!", parent=self).exec()
            os.startfile(save_dir)

        except Exception as e:
            CustomMessageBox("오류", f"작업 중 오류 발생:\n{e}", parent=self).exec()

    def save_pdf(self, writer, folder, filename):
        with open(os.path.join(folder, filename), "wb") as f:
            writer.write(f)
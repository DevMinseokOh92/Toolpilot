import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

class PdfPreviewWidget(QWidget):
    # [NEW] is_vertical 인자 추가 (기본값 False: 가로)
    def __init__(self, parent=None, is_vertical=False):
        super().__init__(parent)
        self.is_vertical = is_vertical
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        # [수정] 모드에 따른 스타일 설정
        if self.is_vertical:
            # 세로 모드: 높이 제한 없음 (부모 레이아웃에 맞춰 늘어남)
            pass 
        else:
            # 가로 모드: 높이 고정 (자르기 화면용)
            self.scroll.setFixedHeight(350)

        self.scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #444; background-color: #222; border-radius: 5px; }
            QScrollBar:horizontal, QScrollBar:vertical { background: #2b2b2b; }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical { background: #555; border-radius: 6px; }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #222;")
        
        # [수정] 모드에 따라 레이아웃 방향 결정
        if self.is_vertical:
            self.thumb_layout = QVBoxLayout(self.content_widget)
            self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter) # 위에서부터 중앙 정렬
        else:
            self.thumb_layout = QHBoxLayout(self.content_widget)
            self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.thumb_layout.setSpacing(15)
        self.thumb_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_pdf(self, file_path):
        # 기존 썸네일 지우기
        for i in reversed(range(self.thumb_layout.count())): 
            widget = self.thumb_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        if not file_path: return

        try:
            doc = fitz.open(file_path)
            # 합치기(세로)일 때는 좀 더 많이 보여줘도 됨 (예: 100페이지)
            max_pages = 100 if self.is_vertical else 50

            for i in range(min(len(doc), max_pages)):
                page = doc.load_page(i)
                # 해상도 설정 (세로는 조금 더 크게 보여줘도 좋음)
                zoom = 0.35 if self.is_vertical else 0.25
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)) 
                
                img_data = pix.samples
                qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)

                # 카드 위젯
                card = QWidget()
                # 세로 모드일 땐 꽉 차지 않게 적당히
                card.setFixedSize(pix.width + 20, pix.height + 30)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(0,0,0,0)
                card_layout.setSpacing(2)

                img_lbl = QLabel()
                img_lbl.setPixmap(pixmap)
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_lbl.setStyleSheet("border: 1px solid #555;")
                
                num_lbl = QLabel(f"- {i+1} -")
                num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                num_lbl.setStyleSheet("color: #aaa; font-size: 12px; font-weight: bold;")

                card_layout.addWidget(img_lbl)
                card_layout.addWidget(num_lbl)
                
                self.thumb_layout.addWidget(card)
            
            # 페이지가 더 남았으면 표시
            if len(doc) > max_pages:
                more_lbl = QLabel(f"... 총 {len(doc)} 페이지 ...")
                more_lbl.setStyleSheet("color: #777; font-size: 14px; font-weight: bold; margin: 10px;")
                more_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.thumb_layout.addWidget(more_lbl)
            
            doc.close()

        except Exception as e:
            print(f"Preview Error: {e}")
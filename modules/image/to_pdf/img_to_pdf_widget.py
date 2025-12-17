import os
import datetime
from PIL import Image
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QListWidget, QHBoxLayout, QFileDialog, QAbstractItemView, 
                             QListWidgetItem, QStyledItemDelegate, QStyle)
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QPainter, QColor, QPen, QFontMetrics
from modules.ui.custom_msg import CustomMessageBox

# Delegate (그리기 담당) - 크기를 동적으로 받기 위해 수정 안 함, 로직에서 처리
class ImageCardDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if not index.isValid(): return
        
        file_path = index.data(Qt.ItemDataRole.UserRole)
        file_name = os.path.basename(file_path)
        seq_num = f"#{index.row() + 1}"
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        pixmap = icon.pixmap(80, 80) if icon else QPixmap()

        rect = option.rect
        painter.save()
        
        # 배경
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setBrush(QColor("#3d3d3d"))
            painter.setPen(QPen(QColor("#0078D7"), 2))
        else:
            painter.setBrush(QColor("#2b2b2b"))
            painter.setPen(QPen(QColor("#555"), 1))
        
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)
        
        # 텍스트 & 이미지
        painter.setPen(QColor("white"))
        
        # 파일명
        name_rect = QRect(rect.left() + 5, rect.top() + 5, rect.width() - 10, 20)
        elided_name = QFontMetrics(painter.font()).elidedText(file_name, Qt.TextElideMode.ElideMiddle, name_rect.width())
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, elided_name)
        
        # 이미지
        if not pixmap.isNull():
            img_x = rect.left() + (rect.width() - pixmap.width()) // 2
            img_y = rect.top() + 30
            painter.drawPixmap(img_x, img_y, pixmap)

        # 순번
        num_rect = QRect(rect.left(), rect.bottom() - 25, rect.width(), 20)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#00fa9a"))
        painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, seq_num)

        painter.restore()

    def sizeHint(self, option, index):
        # 기본 사이즈 (초기값)
        return QSize(140, 150)

class ImageToPdfWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("이미지 합쳐서 PDF 만들기")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("이미지를 드래그하여 순서를 조정하세요. (창 크기에 맞춰 5열로 정렬됩니다)")
        desc.setStyleSheet("color: #aaa; font-size: 14px;")
        layout.addWidget(desc)

        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(ImageCardDelegate())
        self.list_widget.setViewMode(QListWidget.ViewMode.ListMode)
        self.list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.list_widget.setWrapping(True)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        
        # [NEW] 더블 클릭 연결
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: 2px dashed #555; border-radius: 10px; outline: none; }
        """)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ 이미지 추가")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_remove = QPushButton("➖ 선택 제거")
        self.btn_remove.clicked.connect(self.remove_file)
        self.btn_clear = QPushButton("🗑️ 전체 삭제")
        self.btn_clear.clicked.connect(self.clear_all)

        for btn in [self.btn_add, self.btn_remove, self.btn_clear]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(120, 40)
            btn.setStyleSheet("QPushButton { background-color: #3d3d3d; color: white; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #4d4d4d; }")
            btn_layout.addWidget(btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.btn_run = QPushButton("📄 PDF로 변환하기 (다운로드 폴더 저장)")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-size: 16px; font-weight: bold; border-radius: 8px; margin-top: 10px; } QPushButton:hover { background-color: #c0392b; }")
        self.btn_run.clicked.connect(self.run_convert)
        layout.addWidget(self.btn_run)

        self.setLayout(layout)

    # [NEW] 창 크기가 바뀔 때마다 5열로 맞추기
    def resizeEvent(self, event):
        # 전체 너비에서 스크롤바와 여백을 뺀 값
        width = self.list_widget.viewport().width() - 20
        # 5등분 (최소 100px은 유지)
        item_width = max(100, width // 5)
        # 높이는 고정 (150px)
        self.list_widget.setGridSize(QSize(item_width, 150))
        super().resizeEvent(event)

    # [NEW] 더블 클릭 시 이미지 실행
    def on_item_double_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.exists(file_path):
            os.startfile(file_path)

    # ... (드래그 앤 드롭 등 나머지 로직은 기존과 동일) ...
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.list_widget.setStyleSheet(self.list_widget.styleSheet().replace("border: 2px dashed #555;", "border: 2px dashed #00fa9a;"))
        else: event.ignore()

    def dragLeaveEvent(self, event):
        self.list_widget.setStyleSheet(self.list_widget.styleSheet().replace("border: 2px dashed #00fa9a;", "border: 2px dashed #555;"))

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            self.list_widget.setStyleSheet(self.list_widget.styleSheet().replace("border: 2px dashed #00fa9a;", "border: 2px dashed #555;"))
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            self.add_images_to_list(files)
            event.accept()
        else:
            super().dropEvent(event)
            self.list_widget.viewport().update()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if files: self.add_images_to_list(files)

    def add_images_to_list(self, files):
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')
        for f in files:
            if f.lower().endswith(valid_exts):
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setToolTip(f)
                pixmap = QPixmap(f)
                if not pixmap.isNull():
                    scaled_pix = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    item.setData(Qt.ItemDataRole.DecorationRole, QIcon(scaled_pix))
                self.list_widget.addItem(item)

    def remove_file(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.list_widget.viewport().update()

    def clear_all(self):
        self.list_widget.clear()

    def run_convert(self):
        count = self.list_widget.count()
        if count < 1:
            CustomMessageBox("알림", "변환할 이미지를 추가해주세요.", parent=self).exec()
            return

        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Merged_Images_{timestamp}.pdf"
        save_path = os.path.join(download_dir, filename)

        try:
            image_list = []
            first_image = None
            for i in range(count):
                path = self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                img = Image.open(path)
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else: img = img.convert("RGB")

                if i == 0: first_image = img
                else: image_list.append(img)

            if first_image:
                first_image.save(save_path, save_all=True, append_images=image_list)
                CustomMessageBox("성공", f"다운로드 폴더에 저장되었습니다!\n\n파일명: {filename}", parent=self).exec()
                os.startfile(download_dir)
        except Exception as e:
            CustomMessageBox("오류", f"변환 중 오류 발생:\n{e}", parent=self).exec()
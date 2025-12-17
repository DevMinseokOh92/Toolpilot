from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QLinearGradient, QPolygonF
from PyQt6.QtCore import QPointF

class LiveGraphWidget(QWidget):
    def __init__(self, color="#00fa9a", parent=None):
        super().__init__(parent)
        self.line_color = QColor(color)
        self.data_points = [0.0] * 60 # 60초치 데이터 저장
        self.max_value = 100.0
        self.setStyleSheet("background-color: #222; border: 1px solid #444; border-radius: 5px;")
        self.setMinimumHeight(100)

    def add_data(self, value):
        self.data_points.pop(0) # 맨 앞 삭제
        self.data_points.append(float(value)) # 뒤에 추가
        
        # 최대값 자동 조정 (그래프 스케일링)
        current_max = max(self.data_points)
        if current_max > self.max_value:
            self.max_value = current_max
        elif current_max < 50 and self.max_value > 100: 
            self.max_value = 100 # 기본 100 유지
            
        self.update() # 다시 그리기

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        
        # 1. 그리드 그리기 (작업관리자 느낌)
        painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.PenStyle.DotLine))
        for i in range(1, 4):
            y = i * (h / 4)
            painter.drawLine(0, int(y), w, int(y))
        for i in range(1, 6):
            x = i * (w / 6)
            painter.drawLine(int(x), 0, int(x), h)

        # 2. 그래프 경로 생성
        points = []
        step_x = w / (len(self.data_points) - 1)
        
        for i, val in enumerate(self.data_points):
            x = i * step_x
            # 값에 비례하여 높이 계산 (아래가 0이므로 h에서 빼줌)
            normalized_val = val / self.max_value if self.max_value > 0 else 0
            y = h - (normalized_val * h)
            points.append(QPointF(x, y))

        # 3. 그라데이션 채우기 (선 아래 영역)
        if points:
            fill_path = QPolygonF(points)
            fill_path.append(QPointF(w, h)) # 오른쪽 아래
            fill_path.append(QPointF(0, h)) # 왼쪽 아래
            
            grad = QLinearGradient(0, 0, 0, h)
            c = self.line_color
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 100)) # 위쪽 (투명도 100)
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))   # 아래쪽 (투명)
            
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(fill_path)

        # 4. 선 그리기
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)
        painter.drawPolyline(points)
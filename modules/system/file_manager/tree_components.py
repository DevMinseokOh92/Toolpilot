from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

# 정렬을 위한 구분자 (폴더=0, 파일=1)를 저장할 키값
SORT_TYPE_ROLE = Qt.ItemDataRole.UserRole + 1

class SortableTreeWidgetItem(QTreeWidgetItem):
    """
    1순위: 폴더 vs 파일 (폴더가 무조건 위)
    2순위: 선택된 컬럼의 값 (이름, 크기 등)
    """
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        
        # 1. 폴더 vs 파일 구분 (저장해둔 값을 꺼내옴)
        type1 = self.data(0, SORT_TYPE_ROLE)
        type2 = other.data(0, SORT_TYPE_ROLE)
        
        # 값이 없으면(None) 기본값 0 처리
        if type1 is None: type1 = 0
        if type2 is None: type2 = 0

        # 타입이 다르면 (하나는 폴더, 하나는 파일이면)
        if type1 != type2:
            # 0(폴더)이 1(파일)보다 작으므로, 오름차순일 때 폴더가 먼저 옴
            return type1 < type2

        # 2. 타입이 같으면 (둘 다 폴더거나 둘 다 파일이면) -> 기존 컬럼 정렬 로직 수행
        if column == 1 or column == 2: # 크기(1)나 시간(2)은 숫자로 비교
            val1 = self.data(column, Qt.ItemDataRole.UserRole)
            val2 = other.data(column, Qt.ItemDataRole.UserRole)
            if val1 is None: val1 = 0
            if val2 is None: val2 = 0
            return val1 < val2
        
        # 이름(0)이나 삭제(3)는 문자열로 비교
        return super().__lt__(other)
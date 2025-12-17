import os
import shutil
import subprocess
from PyQt6.QtCore import Qt
# 절대 경로로 UI 모듈 불러오기
from modules.ui.custom_msg import CustomMessageBox

class TreeActionHandler:
    def __init__(self, parent_widget):
        self.parent = parent_widget

    def open_file_explorer(self, current_folder, selected_items):
        if not current_folder:
            return

        target_path = current_folder
        
        if selected_items:
            # 첫 번째 선택된 아이템 기준
            item_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            
            if item_path and os.path.isfile(item_path):
                # 파일이면: 탐색기를 열어서 해당 파일을 '선택'한 상태로 보여줌
                subprocess.run(['explorer', '/select,', os.path.normpath(item_path)])
                return
            elif item_path and os.path.isdir(item_path):
                # 폴더면: 해당 폴더로 진입
                target_path = item_path

        # 선택된 게 없거나 폴더인 경우 그냥 연다
        if os.path.exists(target_path):
            os.startfile(target_path)

    def delete_item(self, path, item, tree_widget):
        # 삭제 확인
        msg = CustomMessageBox('삭제 확인', f"정말로 삭제하시겠습니까?\n\n대상: {os.path.basename(path)}", is_question=True, parent=self.parent)
        if msg.exec() == 1:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                
                # UI에서 제거
                parent_item = item.parent() or tree_widget.invisibleRootItem()
                parent_item.removeChild(item)
                return True
            except Exception as e:
                self.show_error(f"삭제 실패:\n{e}")
        return False

    def save_tree_to_downloads(self, tree_root_item):
        content = self._tree_to_text(tree_root_item)
        try:
            download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            file_path = os.path.join(download_path, "FolderTree_List.txt")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            self.show_success(f"저장 완료", f"경로: {file_path}")
            os.startfile(download_path)
        except Exception as e:
            self.show_error(f"저장 실패:\n{e}")

    def _tree_to_text(self, parent, prefix=""):
        text = ""
        count = parent.childCount()
        for i in range(count):
            item = parent.child(i)
            name = item.text(0)
            size = item.text(1)
            duration = item.text(2)
            connector = "└── " if i == count - 1 else "├── "
            text += f"{prefix}{connector}{name}   ({size}, {duration})\n"
            if item.childCount() > 0:
                extension = "    " if i == count - 1 else "│   "
                text += self._tree_to_text(item, prefix + extension)
        return text

    # --- 헬퍼 함수 ---
    def show_error(self, text):
        msg = CustomMessageBox("오류", text, is_question=False, parent=self.parent)
        msg.exec()

    def show_success(self, title, text):
        msg = CustomMessageBox(title, text, is_question=False, parent=self.parent)
        msg.exec()
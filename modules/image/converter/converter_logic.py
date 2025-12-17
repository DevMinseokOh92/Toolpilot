import os
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal

class ImageConverterLogic(QObject):
    progress_signal = pyqtSignal(int, int)

    def convert_images(self, file_paths, target_ext):
        # target_ext: "PNG", "ICO" 등 깔끔한 문자열이 들어옴
        target_ext = target_ext.lower() # 소문자로 변환 (png, ico)
        
        download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        success_count = 0
        total_count = len(file_paths)

        for i, file_path in enumerate(file_paths):
            try:
                img = Image.open(file_path)
                filename = os.path.splitext(os.path.basename(file_path))[0]
                save_path = os.path.join(download_path, f"{filename}.{target_ext}")

                if target_ext == "ico":
                    # ICO는 256x256 리사이징 권장
                    img.save(save_path, format='ICO', sizes=[(256, 256)])

                elif target_ext in ["jpg", "pdf"]:
                    # 투명 배경(RGBA)을 흰색으로 변경
                    if img.mode in ("RGBA", "LA"):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    else:
                        img = img.convert("RGB")
                    
                    img.save(save_path, quality=90)

                elif target_ext == "webp":
                    img.save(save_path, format='WEBP', quality=90)

                else:
                    # PNG 등
                    img.save(save_path)

                success_count += 1
                self.progress_signal.emit(i + 1, total_count)

            except Exception as e:
                print(f"Error converting {file_path}: {e}")

        return success_count, download_path
import os
from tinytag import TinyTag
import cv2  # [NEW] OpenCV 추가 (강력한 영상 처리 도구)

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def get_video_duration(file_path):
    video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mpg', '.mpeg', '.3gp', '.m2ts']
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext not in video_exts:
        return "-", -1

    seconds = 0
    
    # 1차 시도: 가벼운 TinyTag 사용
    try:
        tag = TinyTag.get(file_path)
        if tag.duration is not None and float(tag.duration) > 0:
            seconds = int(round(tag.duration))
    except:
        pass

    # 2차 시도: TinyTag가 실패했거나 0초로 나오면 -> OpenCV 사용 (확실함)
    if seconds == 0:
        try:
            video = cv2.VideoCapture(file_path)
            if video.isOpened():
                fps = video.get(cv2.CAP_PROP_FPS)
                frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps > 0 and frame_count > 0:
                    seconds = int(round(frame_count / fps))
            video.release() # 파일 놓아주기
        except:
            pass

    # 결과 포맷팅
    if seconds > 0:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        time_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        return time_str, seconds

    return "-", -1
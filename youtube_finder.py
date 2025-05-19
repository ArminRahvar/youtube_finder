import sys
import datetime
import math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox
)
from googleapiclient.discovery import build


class YouTubeAdvancedSearcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("جستجوگر یوتیوب")
        self.setGeometry(100, 100, 700, 600)

        layout = QVBoxLayout()

        # API Key input
        api_layout = QHBoxLayout()
        api_label = QLabel("🔑 YouTube API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("کلید API خود را وارد کنید...")
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_input)
        layout.addLayout(api_layout)


        # Keyword
        layout.addWidget(QLabel("🔍 کلمه کلیدی:"))
        self.keyword_input = QLineEdit()
        layout.addWidget(self.keyword_input)

        # Max Views
        layout.addWidget(QLabel("👁 حداکثر بازدید (مثلاً 10000):"))
        self.max_views_input = QLineEdit()
        self.max_views_input.setPlaceholderText("مثلاً 10000")
        layout.addWidget(self.max_views_input)

        # Max Days Old
        layout.addWidget(QLabel("🗓 حداکثر سن ویدیو (روز):"))
        self.max_days_input = QLineEdit()
        self.max_days_input.setPlaceholderText("مثلاً 365")
        layout.addWidget(self.max_days_input)

        # Duration Selector
        layout.addWidget(QLabel("⏱ حداقل زمان ویدیو:"))
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["حداقل 20 دقیقه", "حداقل 1 ساعت", "حداقل 2 ساعت"])
        layout.addWidget(self.duration_combo)

        # Search Button
        self.search_button = QPushButton("🔎 جستجو")
        self.search_button.clicked.connect(self.search_videos)
        layout.addWidget(self.search_button)

        # Results
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        layout.addWidget(self.result_area)

        self.setLayout(layout)

    def get_duration_filter(self):
        selected = self.duration_combo.currentText()
        if "1 ساعت" in selected:
            return 60
        elif "2 ساعت" in selected:
            return 120
        else:
            return 20

    def search_videos(self):
        query = self.keyword_input.text().strip()
        max_views = self.max_views_input.text().strip()
        max_days = self.max_days_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "خطا", "لطفاً یک YouTube API Key معتبر وارد کنید.")
            return
        
        global youtube
        youtube = build("youtube", "v3", developerKey=api_key)

        if not query or not max_views or not max_days:
            QMessageBox.warning(self, "خطا", "لطفاً همه فیلدها را پر کنید.")
            return

        try:
            max_views = int(max_views)
            max_days = int(max_days)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مقادیر بازدید و سن ویدیو باید عدد باشند.")
            return

        self.result_area.setText("در حال جستجو...")

        try:
            duration_limit = self.get_duration_filter()
            video_ids = self.get_video_ids(query, max_pages=3)  # می‌تونی عدد رو بیشتر هم بذاری

            videos = self.get_video_details(video_ids, max_views, max_days, duration_limit)

            if not videos:
                self.result_area.setText("هیچ ویدیویی مطابق فیلترها یافت نشد.")
                return

            result_text = ""
            for i, video in enumerate(videos, 1):
                result_text += (
                    f"{i}. 🎬 عنوان: {video['title']}\n"
                    f"   👁 بازدید: {video['views']}\n"
                    f"   📅 تاریخ آپلود: {video['upload_date']}\n"
                    f"   🔗 لینک: {video['link']}\n\n"
                    )


            self.result_area.setText(result_text)

        except Exception as e:
            self.result_area.setText(f"❌ خطا: {str(e)}")

    def get_video_ids(self, query, max_pages=3):
        video_ids = []
        next_page_token = None

        for _ in range(max_pages):
            response = youtube.search().list(
                q=query,
                part="id",
                type="video",
                videoDuration="long",
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in response['items']:
                video_ids.append(item['id']['videoId'])

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return video_ids

    def get_video_details(self, video_ids, max_views, max_days, min_duration_minutes):

        videos = []
        if not video_ids:
            return videos

        # تقسیم لیست به بخش‌های ۵۰تایی
        chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]

        for chunk in chunks:
            details_response = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(chunk)
            ).execute()

            for item in details_response['items']:
                title = item['snippet']['title']
                views = int(item['statistics'].get('viewCount', 0))
                upload_date = item['snippet']['publishedAt']
                duration_iso = item['contentDetails']['duration']
                video_id = item['id']

                # فیلتر مدت زمان
                duration_minutes = self.parse_iso_duration_to_minutes(duration_iso)
                if duration_minutes < min_duration_minutes:
                    continue

                # فیلتر بازدید
                if views > max_views:
                    continue

                # فیلتر سن ویدیو
                upload_dt = datetime.datetime.strptime(upload_date, "%Y-%m-%dT%H:%M:%SZ")
                if (datetime.datetime.utcnow() - upload_dt).days > max_days:
                    continue

                videos.append({
                    "title": title,
                    "views": views,
                    "upload_date": upload_dt.strftime("%Y-%m-%d"),
                    "link": f"https://www.youtube.com/watch?v={video_id}"
                })

        return videos


    def parse_iso_duration_to_minutes(self, duration):
        import isodate
        try:
            parsed = isodate.parse_duration(duration)
            return parsed.total_seconds() / 60
        except:
            return 0


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeAdvancedSearcher()
    window.show()
    sys.exit(app.exec_())

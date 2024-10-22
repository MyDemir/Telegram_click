import sys
import os
import pyautogui
import numpy as np
import cv2
import keyboard
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QComboBox, QVBoxLayout, QWidget, 
                             QTextEdit, QHBoxLayout, QMessageBox, QRubberBand, QSlider, QGroupBox, QTabWidget, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal, QObject, QPoint, QUrl
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QImage, QIcon, QDesktopServices
import logging
import platform
import psutil
from datetime import datetime

# Log dosyası ayarları
def setup_logging():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_filename = f"bot_log_{current_time}.txt"
    logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Sistem bilgilerini logla
    system_info = f"""
    Sistem Bilgileri:
    OS: {platform.system()} {platform.version()}
    Python Sürümü: {platform.python_version()}
    İşlemci: {platform.processor()}
    RAM: {psutil.virtual_memory().total / (1024.0 ** 3):.2f} GB
    Disk Kullanımı: {psutil.disk_usage('/').percent}%
    """
    logging.info(system_info)

# Global değişkenler
SCAN_AREA = (500, 500)
MIN_OBJECT_SIZE = 10
MAX_SIMULTANEOUS_CLICKS = 20
clicked_areas = deque(maxlen=100)

# Renk temaları
THEMES = {
    'Normal': {
        'GREEN': (np.array([40, 50, 50]), np.array([80, 255, 255]))
    },
    'Hack': {
        'PINK': (np.array([140, 50, 50]), np.array([170, 255, 255])),
        'BLUE': (np.array([100, 50, 50]), np.array([130, 255, 255])),
        'GRAY': (np.array([0, 0, 50]), np.array([250, 50, 250]))
    }
}

class BotSignals(QObject):
    update_status = pyqtSignal(str, QColor)
    update_log = pyqtSignal(str)
    update_click_count = pyqtSignal(int)

class BotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MASADAKRİPTO - BLUMBOT V1.3")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # İkon ayarla
        if getattr(sys, 'frozen', False):
            # Exe için ikon yolu
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            # Normal çalışma için ikon yolu
            icon_path = 'icon.ico'
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Sol panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel)

        # Sağ panel (Log ve İstatistikler için)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel)

        # Tema ve Bölge Seçimi
        settings_group = QGroupBox("Ayarlar")
        settings_layout = QVBoxLayout(settings_group)
        left_layout.addWidget(settings_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText("Normal")
        settings_layout.addWidget(QLabel("Tema Seçin:"))
        settings_layout.addWidget(self.theme_combo)

        region_layout = QHBoxLayout()
        self.select_region_button = QPushButton("Bölge Seç")
        self.select_region_button.clicked.connect(self.select_region)
        region_layout.addWidget(self.select_region_button)
        self.region_label = QLabel("Seçili Bölge: Yok")
        region_layout.addWidget(self.region_label)
        settings_layout.addLayout(region_layout)

        # Max Eş Zamanlı Tıklama Sayısı
        self.max_clicks_slider = QSlider(Qt.Horizontal)
        self.max_clicks_slider.setMinimum(1)
        self.max_clicks_slider.setMaximum(50)
        self.max_clicks_slider.setValue(MAX_SIMULTANEOUS_CLICKS)
        self.max_clicks_slider.setTickPosition(QSlider.TicksBelow)
        self.max_clicks_slider.setTickInterval(5)
        self.max_clicks_label = QLabel(f"Max Eş Zamanlı Tıklama: {MAX_SIMULTANEOUS_CLICKS}")
        self.max_clicks_slider.valueChanged.connect(self.update_max_clicks)
        settings_layout.addWidget(self.max_clicks_label)
        settings_layout.addWidget(self.max_clicks_slider)

        # Tıklama Gecikmesi
        self.click_delay_slider = QSlider(Qt.Horizontal)
        self.click_delay_slider.setMinimum(0)
        self.click_delay_slider.setMaximum(1000)
        self.click_delay_slider.setValue(0)
        self.click_delay_slider.setTickPosition(QSlider.TicksBelow)
        self.click_delay_slider.setTickInterval(100)
        self.click_delay_label = QLabel("Tıklama Gecikmesi: 0 ms")
        self.click_delay_slider.valueChanged.connect(self.update_click_delay)
        settings_layout.addWidget(self.click_delay_label)
        settings_layout.addWidget(self.click_delay_slider)

        # Durum ve Kontrol
        control_group = QGroupBox("Kontrol")
        control_layout = QVBoxLayout(control_group)
        left_layout.addWidget(control_group)

        self.status_label = QLabel("Bot Durumu: Beklemede")
        font = QFont()
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.status_label)

        control_layout.addWidget(QLabel("Botu çalıştırmak için boşluk tuşuna basılı tutun"))

        self.exit_button = QPushButton("Çıkış")
        self.exit_button.clicked.connect(self.close_application)
        control_layout.addWidget(self.exit_button)

        # İletişim Bilgileri
        contact_group = QGroupBox("İletişim Bilgileri")
        contact_layout = QVBoxLayout(contact_group)
        left_layout.addWidget(contact_group)

        contact_info = [
            ("Yapımcı: MASADAKRİPTO - PENGU", None),
            ("Telegram", "https://t.me/masadakripto"),
            ("Telegram Sohbet", "https://t.me/masadakriptosohbet")
        ]

        for text, link in contact_info:
            label = QLabel(f'<a href="{link}">{text}</a>')
            label.setOpenExternalLinks(True)
            contact_layout.addWidget(label)

        # İstatistikler
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QVBoxLayout(stats_group)
        right_layout.addWidget(stats_group)

        self.total_clicks_label = QLabel("Toplam Tıklama: 0")
        stats_layout.addWidget(self.total_clicks_label)

        self.avg_clicks_label = QLabel("Ortalama Tıklama/sn: 0")
        stats_layout.addWidget(self.avg_clicks_label)

        self.runtime_label = QLabel("Çalışma Süresi: 00:00:00")
        stats_layout.addWidget(self.runtime_label)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        right_layout.addWidget(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Önizleme
        self.screenshot_label = QLabel()
        left_layout.addWidget(self.screenshot_label)

        # Diğer özellikler
        self.bot_active = False
        self.search_region = None
        self.total_clicks = 0
        self.start_time = None
        self.click_delay = 0
        self.rubberBand = None  # Bu satırı ekleyin

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # Her saniye güncelle

        self.signals = BotSignals()
        self.signals.update_status.connect(self.update_status_label)
        self.signals.update_log.connect(self.update_log_text)
        self.signals.update_click_count.connect(self.update_click_count)

    def update_max_clicks(self, value):
        global MAX_SIMULTANEOUS_CLICKS
        MAX_SIMULTANEOUS_CLICKS = value
        self.max_clicks_label.setText(f"Max Eş Zamanlı Tıklama: {value}")

    def update_click_delay(self, value):
        self.click_delay = value
        self.click_delay_label.setText(f"Tıklama Gecikmesi: {value} ms")

    def update_stats(self):
        if self.bot_active and self.start_time:
            runtime = time.time() - self.start_time
            hours, rem = divmod(runtime, 3600)
            minutes, seconds = divmod(rem, 60)
            self.runtime_label.setText(f"Çalışma Süresi: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
            
            if runtime > 0:
                avg_clicks = self.total_clicks / runtime
                self.avg_clicks_label.setText(f"Ortalama Tıklama/sn: {avg_clicks:.2f}")

    def update_status_label(self, status, color):
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"background-color: {color.name()}; color: black;")

    def update_log_text(self, message):
        self.log_text.append(message)

    def update_click_count(self, count):
        self.total_clicks = count
        self.total_clicks_label.setText(f"Toplam Tıklama: {self.total_clicks}")

    def close_application(self):
        reply = QMessageBox.question(self, 'Çıkış', 'Programı kapatmak istediğinizden emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()

    def select_region(self):
        try:
            self.signals.update_log.emit("Lütfen arama bölgesini seçmek için ekran görüntüsü üzerinde sürükleyerek bir alan belirleyin.")
            screen = QApplication.primaryScreen()
            if screen is None:
                raise Exception("Ekran bulunamadı.")
            
            screenshot = screen.grabWindow(0)
            if screenshot.isNull():
                raise Exception("Ekran görüntüsü alınamadı.")
            
            # Ekran görüntüsünü daha büyük bir boyuta ölçeklendiriyoruz
            scaled_screenshot = screenshot.scaled(700, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            if self.screenshot_label is None:
                self.screenshot_label = QLabel(self)
                self.layout().addWidget(self.screenshot_label)
            
            self.screenshot_label.setPixmap(scaled_screenshot)
            self.screenshot_label.mousePressEvent = self.start_selection
            self.screenshot_label.mouseMoveEvent = self.drawing_selection
            self.screenshot_label.mouseReleaseEvent = self.end_selection
            
            self.signals.update_log.emit("Ekran görüntüsü başarıyla yüklendi. Lütfen bir bölge seçin.")
        except Exception as e:
            error_message = f"Bölge seçimi sırasında hata oluştu: {str(e)}"
            self.signals.update_log.emit(error_message)
            logging.error(error_message)
            QMessageBox.critical(self, "Hata", error_message)

    def start_selection(self, event):
        self.origin = event.pos()
        if self.rubberBand is None:
            self.rubberBand = QRubberBand(QRubberBand.Rectangle, self.screenshot_label)
        self.rubberBand.setGeometry(QRect(self.origin, QPoint()))
        self.rubberBand.show()

    def drawing_selection(self, event):
        if self.rubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def end_selection(self, event):
        if self.rubberBand:
            self.rubberBand.hide()
            selected_rect = self.rubberBand.geometry()
            screen_width = QApplication.primaryScreen().size().width()
            screen_height = QApplication.primaryScreen().size().height()
            
            # Ölçeklendirme faktörlerini güncelliyoruz
            scale_x = screen_width / self.screenshot_label.pixmap().width()
            scale_y = screen_height / self.screenshot_label.pixmap().height()
            
            x = int(selected_rect.x() * scale_x)
            y = int(selected_rect.y() * scale_y)
            width = int(selected_rect.width() * scale_x)
            height = int(selected_rect.height() * scale_y)
            
            self.search_region = (x, y, width, height)
            self.signals.update_log.emit(f"Arama bölgesi seçildi: {self.search_region}")
            self.region_label.setText(f"Seçili Bölge: {self.search_region}")
            
            self.screenshot_label.mousePressEvent = None
            self.screenshot_label.mouseMoveEvent = None
            self.screenshot_label.mouseReleaseEvent = None
            self.screenshot_label.clear()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Çıkış', 'Programı kapatmak istediğinizden emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def is_recently_clicked(x, y, current_time, area_threshold=30, time_threshold=0.3):
    for cx, cy, click_time in clicked_areas:
        if abs(x - cx) < area_threshold and abs(y - cy) < area_threshold and current_time - click_time < time_threshold:
            return True
    return False

def process_contour(contour, start_x, start_y, current_time):
    area = cv2.contourArea(contour)
    if area < MIN_OBJECT_SIZE * MIN_OBJECT_SIZE:
        return None

    bottom_most = tuple(contour[contour[:, :, 1].argmax()][0])
    if not is_recently_clicked(bottom_most[0], bottom_most[1], current_time):
        return (start_x + bottom_most[0], start_y + bottom_most[1])
    return None

def click_objects(window):
    try:
        if window.search_region:
            start_x, start_y, width, height = window.search_region
        else:
            screen_width, screen_height = pyautogui.size()
            center_x, center_y = screen_width // 2, screen_height // 2
            start_x, start_y = center_x - SCAN_AREA[0] // 2, center_y - SCAN_AREA[1] // 2
            width, height = SCAN_AREA

        screenshot = np.array(pyautogui.screenshot(region=(start_x, start_y, width, height)))
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_RGB2HSV)

        theme = window.theme_combo.currentText()
        colors = THEMES[theme]

        combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for color_name, (lower, upper) in colors.items():
            mask = cv2.inRange(hsv, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, mask)

        kernel = np.ones((3, 3), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        current_time = time.time()
        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            results = list(executor.map(lambda c: process_contour(c, start_x, start_y, current_time), contours))

        click_points = [r for r in results if r is not None]

        for x, y in click_points[:MAX_SIMULTANEOUS_CLICKS]:
            pyautogui.click(x, y)
            clicked_areas.append((x - start_x, y - start_y, current_time))
            window.total_clicks += 1
            window.signals.update_click_count.emit(window.total_clicks)
            log_message = f"Tıklama: ({x}, {y})"
            logging.info(log_message)
            window.signals.update_log.emit(log_message)
            time.sleep(window.click_delay / 1000)  # Tıklama gecikmesi

    except Exception as e:
        error_message = f"Hata oluştu: {str(e)}"
        logging.error(error_message)
        window.signals.update_log.emit(error_message)

def main():
    multiprocessing.freeze_support()  # Windows'ta multiprocessing için gerekli
    setup_logging()  # Log dosyasını oluştur ve sistem bilgilerini logla
    app = QApplication(sys.argv)
    window = BotWindow()
    window.show()

    stop_event = threading.Event()

    def run_bot():
        while not stop_event.is_set():
            if keyboard.is_pressed('space'):
                if not window.bot_active:
                    window.bot_active = True
                    window.signals.update_status.emit("Bot Durumu: Çalışıyor", QColor(0, 255, 0))
                    window.start_time = time.time()
                click_objects(window)
            else:
                if window.bot_active:
                    window.bot_active = False
                    window.signals.update_status.emit("Bot Durumu: Beklemede", QColor(255, 255, 0))
            time.sleep(0.01)

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    exit_code = app.exec_()
    stop_event.set()
    bot_thread.join()
    sys.exit(exit_code)

if __name__ == "__main__":
    pyautogui.PAUSE = 0
    main()
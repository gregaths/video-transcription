import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout,
    QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap


class TranscriptionWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        try:
            audio_path = self.extract_audio(self.video_path)
            text = self.transcribe(audio_path)

            if os.path.exists(audio_path):
                os.remove(audio_path)

            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))

    def extract_audio(self, video_path):
        self.status_update.emit("Κατάσταση: Εξαγωγή ήχου από το βίντεο...")
        audio_path = "temp_audio.wav"

        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", audio_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return audio_path

    def transcribe(self, audio_path):
        self.status_update.emit("Κατάσταση: Φόρτωση μοντέλου Whisper...")
        from faster_whisper import WhisperModel

        model = WhisperModel("medium", device="cpu", compute_type="int8")

        self.status_update.emit("Κατάσταση: Απομαγνητοφώνηση σε εξέλιξη...")
        segments, info = model.transcribe(audio_path, language="el")

        full_text = "\n".join(seg.text.strip() for seg in segments)
        return full_text


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Απομαγνητοφώνηση Βίντεο")
        self.setGeometry(100, 100, 800, 600)

        self.video_path = None
        self.worker = None

        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "/Users/grigoris/transcriptionstopsadasfdas/policegreek.jpg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale με διατήρηση αναλογιών, μέγιστο πλάτος 200px
            pixmap = pixmap.scaledToWidth(500, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("[Δεν βρέθηκε policegreek.jpg]")
        self.logo_label.setAlignment(Qt.AlignCenter)


        self.select_button = QPushButton("Επιλογή Βίντεο")
        self.file_label = QLabel("Δεν έχει επιλεγεί αρχείο")

        self.start_button = QPushButton("Έναρξη Απομαγνητοφώνησης")
        self.status_label = QLabel("Κατάσταση: Αναμονή")

        self.start_button.setEnabled(False)

        # Μεγαλύτερη γραμματοσειρά για τα κουμπιά (πιο "desktop app" feel)
        self.select_button.setMinimumHeight(40)
        self.start_button.setMinimumHeight(40)

        self.select_button.clicked.connect(self.select_video)
        self.start_button.clicked.connect(self.start_transcription)


        # ---- Footer με στοιχεία developer ----
        self.developer_label = QLabel("Developer: Grigoris Athanasiadis |  Email: g.athanasiadis@astynomia.gr")
        self.developer_label.setAlignment(Qt.AlignCenter)
        self.developer_label.setStyleSheet("color: gray; font-size: 11px;")

        layout = QVBoxLayout()
        layout.addWidget(self.select_button)
        layout.addWidget(self.file_label)
        layout.addSpacing(10)
        layout.addWidget(self.start_button)
        layout.addWidget(self.status_label)
        layout.addSpacing(20)
        layout.addWidget(self.logo_label)
        layout.addStretch()  # σπρώχνει το footer στο κάτω μέρος
        layout.addWidget(self.developer_label)

        layout.setContentsMargins(40, 30, 40, 20)
        self.setLayout(layout)

    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Επιλέξτε βίντεο",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv)"
        )
        if file_path:
            self.video_path = file_path
            self.file_label.setText(file_path)
            self.start_button.setEnabled(True)
            self.status_label.setText("Κατάσταση: Έτοιμο για επεξεργασία")

    def start_transcription(self):
        self.start_button.setEnabled(False)
        self.select_button.setEnabled(False)

        self.worker = TranscriptionWorker(self.video_path)
        self.worker.status_update.connect(self.update_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_status(self, message):
        self.status_label.setText(message)

    def on_finished(self, text):
        self.status_label.setText("Κατάσταση: Ολοκληρώθηκε! Επιλέξτε πού θα αποθηκευτεί.")

        # Προτεινόμενο όνομα αρχείου: ίδιο με το βίντεο, αλλά .txt
        base_name = os.path.splitext(os.path.basename(self.video_path))[0]
        suggested_name = f"{base_name}.txt"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Αποθήκευση Απομαγνητοφώνησης",
            suggested_name,
            "Text Files (*.txt)"
        )

        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.status_label.setText(f"Κατάσταση: Αποθηκεύτηκε στο {save_path}")
                QMessageBox.information(self, "Επιτυχία", "Η απομαγνητοφώνηση αποθηκεύτηκε επιτυχώς!")
            except Exception as e:
                self.status_label.setText("Κατάσταση: Σφάλμα αποθήκευσης")
                QMessageBox.critical(self, "Σφάλμα", f"Δεν ήταν δυνατή η αποθήκευση: {e}")
        else:
            self.status_label.setText("Κατάσταση: Ολοκληρώθηκε, αλλά δεν αποθηκεύτηκε")

        self.start_button.setEnabled(True)
        self.select_button.setEnabled(True)

    def on_error(self, error_message):
        self.status_label.setText(f"Κατάσταση: Σφάλμα - {error_message}")
        self.start_button.setEnabled(True)
        self.select_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
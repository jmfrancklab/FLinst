"""Qt front-end that exposes the gds_for_tune workflow as an flinst subcommand."""

import sys
import numpy as np
import SpinCore_pp
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QTabWidget,
    QComboBox,
)
import matplotlib.backends.backend_qt5agg as mplqt5
from matplotlib.figure import Figure
from Instruments.gds_tune import (
    load_active_config,
    list_serial_instruments,
    run_frequency_sweep,
    reflection_metrics,
    jump_series_default,
    analytic_signal,
)


class SweepWorker(QObject):
    """Background worker that runs the hardware sweep without blocking Qt."""

    progress = pyqtSignal(object, int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object, object)
    failed = pyqtSignal(str)
    ready = pyqtSignal()
    ready_cleared = pyqtSignal()

    def __init__(self, parser_dict, jump_series, control_channel, reflection_channel):
        super().__init__()
        self.parser_dict = parser_dict
        self.jump_series = jump_series
        self._stop = False
        self.control_channel = control_channel
        self.reflection_channel = reflection_channel

    def request_stop(self):
        """Flag the worker so the acquisition loop exits gracefully."""
        self._stop = True

    def run(self):
        """Execute the hardware sweep and emit progress/completion signals."""
        try:
            d_all, flat_slice = run_frequency_sweep(
                self.parser_dict,
                jump_series=self.jump_series,
                waveform_callback=lambda data, idx: self.progress.emit(data, idx),
                status_callback=lambda text: self.status.emit(text),
                stop_requested=lambda: self._stop,
                control_channel=self.control_channel,
                reflection_channel=self.reflection_channel,
                ready_callback=lambda: self.ready.emit(),
                ready_clear_callback=lambda: self.ready_cleared.emit(),
            )
            self.finished.emit(d_all, flat_slice)
        except Exception as exc:
            self.failed.emit(str(exc))


class GdsTuneWindow(QMainWindow):
    """Main window that wraps the waveform sweep inside a Qt + Matplotlib GUI."""

    def __init__(self, parser_dict):
        """Store the parser configuration and initialize the window shell."""
        super().__init__()
        self.parser_dict = parser_dict
        self.setWindowTitle("GDS tune controller")
        self.setGeometry(50, 50, 1600, 900)
        self.worker_thread = None
        self.worker = None
        self.latest_data = None
        self.latest_slice = None
        self.waveform_lines = {}
        self.sweep_lines = {}
        # Enable the GUI-controlled pause logic so tune() waits for READY.
        SpinCore_pp.gui_pause_enabled = True
        SpinCore_pp.gui_pause_ready = False

        self.build_ui()

    def build_ui(self):
        """Create the split layout with controls on the left and plots on the right."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        control_panel = self.build_controls()
        main_layout.addWidget(control_panel)

        plots_widget = self.build_plots()
        main_layout.addWidget(plots_widget, 1)

    def build_controls(self):
        """Return the control column with jump offsets, status text, and buttons."""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        form = QFormLayout()
        self.jump_input = QLineEdit(
            ",".join(["%g" % value for value in jump_series_default])
        )
        form.addRow("Jump offsets (MHz)", self.jump_input)
        self.file_path_edit = QLineEdit("201020_sol_probe_1.h5")
        form.addRow("HDF5 file", self.file_path_edit)
        self.dataset_name_edit = QLineEdit("capture1")
        form.addRow("Dataset name", self.dataset_name_edit)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("Start sweep")
        self.start_button.clicked.connect(self.start_or_stop_sweep)
        button_row.addWidget(self.start_button)
        self.save_button = QPushButton("Save data")
        self.save_button.clicked.connect(self.save_capture)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

        self.status_label = QLabel("Idle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.result_label = QLabel("Reflection results will appear here.")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        self.control_label = QLabel("control waveform:")
        layout.addWidget(self.control_label)
        self.control_channel_box = QComboBox()
        for channel in range(1, 5):
            self.control_channel_box.addItem("CH%d" % channel)
        self.control_channel_box.setCurrentText("CH2")
        layout.addWidget(self.control_channel_box)

        self.reflection_label = QLabel("reflection waveform:")
        layout.addWidget(self.reflection_label)
        self.reflection_channel_box = QComboBox()
        for channel in range(1, 5):
            self.reflection_channel_box.addItem("CH%d" % channel)
        self.reflection_channel_box.setCurrentText("CH3")
        layout.addWidget(self.reflection_channel_box)
        self.ready_button = QPushButton("READY")
        self.ready_button.setStyleSheet(
            "background-color: red; color: white; font-weight: bold;"
        )
        self.ready_button.clicked.connect(self.ready_clicked)
        self.ready_button.hide()
        layout.addWidget(self.ready_button)
        layout.addStretch(1)
        return panel

    def ready_clicked(self):
        """Set the SpinCore flag so tune() continues after the READY press."""
        SpinCore_pp.gui_pause_ready = True
        self.ready_button.setEnabled(False)
        self.ready_button.setText("Waiting...")

    def show_ready_prompt(self):
        """Display the red READY button when tune() is about to pause."""
        self.ready_button.setText("READY")
        self.ready_button.setEnabled(True)
        self.ready_button.show()

    def hide_ready_prompt(self):
        """Hide the READY button once tune() has finished pausing."""
        self.ready_button.hide()
        self.ready_button.setEnabled(True)
        self.ready_button.setText("READY")

    def build_plots(self):
        """Create the waveform/sweep tab widget and keep references to each tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        self.tabs = QTabWidget()
        self.waveform_canvas, self.waveform_axes = self.create_canvas("Waveforms")
        self.waveform_tab = QWidget()
        waveform_layout = QVBoxLayout()
        waveform_layout.addWidget(self.waveform_canvas)
        self.waveform_tab.setLayout(waveform_layout)
        self.tabs.addTab(self.waveform_tab, "Waveforms")

        self.sweep_canvas, self.sweep_axes = self.create_canvas("Frequency sweep")
        self.sweep_tab = QWidget()
        sweep_layout = QVBoxLayout()
        sweep_layout.addWidget(self.sweep_canvas)
        self.sweep_tab.setLayout(sweep_layout)
        self.tabs.addTab(self.sweep_tab, "Frequency sweep")

        layout.addWidget(self.tabs)
        return widget

    def create_canvas(self, title):
        """Return a Matplotlib canvas configured to mimic the transparent NMR GUI."""
        figure = Figure()
        figure.set_facecolor("none")
        axes = figure.add_subplot(111)
        axes.set_title(title)
        canvas = mplqt5.FigureCanvasQTAgg(figure)
        canvas.setStyleSheet("background-color:transparent;")
        return canvas, axes

    def start_or_stop_sweep(self):
        """Handle the start button, double-functioning as a stop button mid-sweep."""
        if self.worker_thread is not None:
            self.request_stop()
            return
        if not self.confirm_connections():
            return
        control_channel = self.selected_channel(self.control_channel_box)
        reflection_channel = self.selected_channel(self.reflection_channel_box)
        if control_channel == reflection_channel:
            QMessageBox.warning(
                self,
                "Invalid channel selection",
                "Choose different scope channels for control and reflection.",
            )
            return
        self.reset_plots()
        self.hide_ready_prompt()
        self.status_label.setText("Listing instruments...")
        list_serial_instruments()
        self.status_label.setText("Starting sweep...")
        jump_series = self.parse_jump_series()
        self.worker = SweepWorker(
            self.parser_dict,
            jump_series,
            control_channel,
            reflection_channel,
        )
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_plots_from_worker)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.sweep_finished)
        self.worker.failed.connect(self.sweep_failed)
        self.worker.ready.connect(self.show_ready_prompt)
        self.worker.ready_cleared.connect(self.hide_ready_prompt)
        self.worker.finished.connect(self.cleanup_worker)
        self.worker.failed.connect(self.cleanup_worker)
        self.worker_thread.start()
        self.start_button.setText("Stop sweep")

    def request_stop(self):
        """Signal the worker thread to halt the sweep as soon as possible."""
        if self.worker is not None:
            self.worker.request_stop()
            self.status_label.setText("Stopping...")
            SpinCore_pp.gui_pause_ready = True
            self.hide_ready_prompt()

    def cleanup_worker(self):
        """Tear down the worker thread state once the sweep finishes or fails."""
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
        self.worker = None
        self.start_button.setText("Start sweep")
        self.hide_ready_prompt()

    def confirm_connections(self):
        """Show the modal wiring confirmation in place of the legacy input() call."""
        control_channel = self.selected_channel(self.control_channel_box)
        reflection_channel = self.selected_channel(self.reflection_channel_box)
        message = (
            "I'm going to assume the control is on CH%d and the reflection is on CH%d"
            " of the GDS. Is that correct?"
            % (control_channel, reflection_channel)
        )
        reply = QMessageBox.question(
            self,
            "Verify scope wiring",
            message,
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        return reply == QMessageBox.Yes

    def parse_jump_series(self):
        """Return the user-supplied jump offsets or fall back to the defaults."""
        text = self.jump_input.text().strip()
        if not text:
            return jump_series_default
        try:
            values = [float(item) for item in text.split(",") if item.strip()]
            if not values:
                return jump_series_default
            return np.array(values)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid jump list",
                "Could not parse the jump offsets, using the default list instead.",
            )
            return jump_series_default

    def reset_plots(self):
        """Clear both tabs so the new sweep draws fresh lines."""
        self.waveform_axes.clear()
        self.waveform_axes.set_title("Waveforms")
        self.waveform_lines = {}
        self.waveform_canvas.draw_idle()
        self.sweep_axes.clear()
        self.sweep_axes.set_title("Frequency sweep")
        self.sweep_lines = {}
        self.sweep_canvas.draw_idle()
        self.latest_data = None
        self.latest_slice = None
        self.result_label.setText("Reflection results will appear here.")

    def update_status(self, text):
        """Update the status text area from worker callbacks."""
        self.status_label.setText(text)

    def update_plots_from_worker(self, data, offset_index):
        """Refresh both tabs each time the worker posts a newly acquired trace."""
        self.latest_data = data
        self.update_waveform_plot(data)
        analytic_preview = analytic_signal(data.C, self.parser_dict)
        self.update_frequency_plot(analytic_preview, offset_index)

    def update_waveform_plot(self, data):
        """Keep the raw zero-offset control/reflection overlay up to date."""
        try:
            zero_offset = data["offset":0]
        except Exception:
            return
        control = zero_offset["ch", 0]
        reflection = zero_offset["ch", 1]
        time_axis = control.getaxis("t")
        if "control" not in self.waveform_lines:
            (self.waveform_lines["control"],) = self.waveform_axes.plot(
                time_axis, control.data, alpha=0.3, label="Control"
            )
            (self.waveform_lines["reflection"],) = self.waveform_axes.plot(
                time_axis, reflection.data, alpha=0.3, label="Reflection"
            )
            magnitude = np.abs(reflection.data)
            (self.waveform_lines["magnitude"],) = self.waveform_axes.plot(
                time_axis, magnitude, linewidth=2, label="|reflection|"
            )
            self.waveform_axes.legend(loc="best")
        else:
            self.waveform_lines["control"].set_data(time_axis, control.data)
            self.waveform_lines["reflection"].set_data(time_axis, reflection.data)
            magnitude = np.abs(reflection.data)
            self.waveform_lines["magnitude"].set_data(time_axis, magnitude)
        self.waveform_axes.relim()
        self.waveform_axes.autoscale_view()
        self.waveform_canvas.draw_idle()

    def update_frequency_plot(self, data, offset_index):
        """Plot the analytic reflection magnitude and raise the sweep tab."""
        reflection_slice = data["ch", 1]["offset", offset_index]
        time_axis = reflection_slice.getaxis("t")
        magnitude = np.abs(reflection_slice.data)
        offset_value = data.getaxis("offset")[offset_index]
        label = "%s %+0.3f MHz" % (
            self.parser_dict["carrierFreq_MHz"],
            offset_value,
        )
        if offset_value not in self.sweep_lines:
            (line,) = self.sweep_axes.plot(time_axis, magnitude, label=label)
            self.sweep_lines[offset_value] = line
            self.sweep_axes.legend(loc="best")
        else:
            self.sweep_lines[offset_value].set_data(time_axis, magnitude)
        self.sweep_axes.relim()
        self.sweep_axes.autoscale_view()
        self.sweep_canvas.draw_idle()
        self.tabs.setCurrentWidget(self.sweep_tab)

    def selected_channel(self, combo_box):
        """Return the numeric scope channel selected by the supplied combo box."""
        text = combo_box.currentText().strip()
        return int(text.replace("CH", ""))

    def sweep_finished(self, data, flat_slice):
        """Summarize the reflection metric once the sweep completes."""
        self.latest_data = data
        self.latest_slice = flat_slice
        ratio, tuning_dB = reflection_metrics(flat_slice)
        message = (
            "Reflection ratio %0.1f dB (ratio=%0.4f)."
            % (tuning_dB, ratio)
        )
        if tuning_dB < -25:
            message += " Congratulations!"
        else:
            message += " Try to improve the match."
        self.result_label.setText(message)
        self.status_label.setText("Sweep complete")

    def sweep_failed(self, error_text):
        """Display the error that aborted the sweep."""
        if error_text == "Sweep cancelled":
            self.status_label.setText("Sweep cancelled")
        else:
            QMessageBox.critical(self, "Sweep failed", error_text)
            self.status_label.setText("Error: %s" % error_text)

    def save_capture(self):
        """Persist the most recent analytic dataset to disk via hdf5_write."""
        if self.latest_data is None:
            QMessageBox.warning(self, "No data", "Run a sweep before saving.")
            return
        dataset_name = self.dataset_name_edit.text().strip() or "capture1"
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(
                self,
                "Missing path",
                "Enter the destination HDF5 filename before saving.",
            )
            return
        try:
            self.latest_data["offset":0].name(dataset_name)
            self.latest_data["offset":0].hdf5_write(file_path)
            self.status_label.setText("Saved %s to %s" % (dataset_name, file_path))
        except Exception as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def closeEvent(self, event):
        """Reset the SpinCore pause flags when the GUI closes."""
        SpinCore_pp.gui_pause_enabled = False
        SpinCore_pp.gui_pause_ready = False
        super().closeEvent(event)


def main(*args):
    app = QApplication(list(sys.argv))
    parser_dict = load_active_config()
    window = GdsTuneWindow(parser_dict)
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()

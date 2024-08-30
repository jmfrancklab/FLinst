"""
started from Eli Bendersky (eliben@gmail.com), updated
by Ondrej Holesovsky.  License: this code is in the
public domain.

then use this:
https://www.pythonguis.com/tutorials/pyqt-layouts/
which is a good layout reference

JF updated to plot a sine wave
"""
from numpy import r_
import numpy as np
from .XEPR_eth import xepr as xepr_from_module
import time
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
)  # QtWidgets is for GUI components
from PyQt5.QtCore import Qt  # QtCore is for core non-GUI functionalities
from PyQt5.QtGui import QIcon  # QtGui is for handling icons and images
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QSlider,
    QHBoxLayout,
    QAction,
)
from SpinCore_pp.ppg import run_spin_echo
import SpinCore_pp  # just for config file, but whatever...
from pyspecdata import gammabar_H
import pyspecdata as psp
import matplotlib.backends.backend_qt5agg as mplqt5
from matplotlib.figure import Figure


class NMRWindow(QMainWindow):
    def __init__(self, xepr, myconfig, parent=None):
        self.xepr = xepr
        self.myconfig = myconfig
        super().__init__(parent)
        self.setWindowTitle("NMR signal finder")
        self.setGeometry(20, 20, 1500, 800)

        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()
        self.nPhaseSteps = 4
        self.npts = 2**14 // self.nPhaseSteps
        self.adc_offset()
        self.acq_NMR()

    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"

        path, ext = QFileDialog.getSaveFileName(
            self, "Save file", "", file_choices
        )
        path = path.encode("utf-8")
        if not path[-4:] == file_choices[-4:].encode("utf-8"):
            path += file_choices[-4:].encode("utf-8")
        if path:
            self.canvas.print_figure(path.decode(), dpi=self.dpi)
            self.statusBar().showMessage("Saved to %s" % path, 2000)

    def on_about(self):
        msg = """ A demo of using PyQt with matplotlib:
        
         * Use the matplotlib navigation bar
         * Add values to the text box and press Enter
         (or click "Acquire NMR")
         * Show or hide the grid
         * Drag the slider to modify the width of the bars
         * Save the plot to a file using the File menu
         * Click on a bar to receive an informative message
        """
        QMessageBox.about(self, "About the demo", msg.strip())

    def set_default_choices(self):
        self.textbox_apo.setText("10 ms")
        self.textbox_apo.setMinimumWidth(10)
        self.myconfig["SW_kHz"] = 200

    def on_textchange(self):
        print(
            "you changed your apodization to",
            self.textbox_apo.text(),
            "but I'm not yet programmed to do anything about that!",
        )
        self.apo_time_const = 10e-3
        return

    def on_pick(self, event):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        #
        box_points = event.artist.get_bbox().get_points()
        msg = "You've clicked on a bar with coords:\n %s" % box_points

        QMessageBox.information(self, "Click!", msg)

    def set_field_conditional(self, Field):
        if (
            hasattr(self, "prev_field")
            and abs(Field - self.prev_field) > 50.0 / gammabar_H * 1e4
            and abs(Field - self.prev_field) < 850.0 / gammabar_H * 1e4
        ):
            print(
                "You are trying to shift by an intermediate offset, so I'm going to set the field slowly."
            )
            Field = self.xepr.set_field(Field)
            self.prev_field = Field
        elif (
            hasattr(self, "prev_field")
            and abs(Field - self.prev_field) < 50.0 / gammabar_H * 1e4
        ):
            print("You seem to be within 50 Hz, so I'm not changing the field")
        else:
            Field = self.xepr.set_coarse_field(Field)
            self.prev_field = Field

    def generate_data(self):
        # {{{let computer set field
        print(
            "I'm assuming that you've tuned your probe to",
            self.myconfig["carrierFreq_MHz"],
            "since that's what's in your .ini file",
        )
        Field = (
            self.myconfig["carrierFreq_MHz"] / self.myconfig["gamma_eff_MHz_G"]
        )
        print(
            "Based on that, and the gamma_eff_MHz_G you have in your .ini file, I'm setting the field to %f"
            % Field
        )
        assert Field < 3700, "are you crazy??? field is too high!"
        assert Field > 3300, "are you crazy?? field is too low!"
        self.set_field_conditional(Field)
        # }}}
        # {{{acquire echo
        self.echo_data = run_spin_echo(
            nScans=self.myconfig["nScans"],
            indirect_idx=0,
            indirect_len=1,
            deblank_us = self.myconfig["deblank_us"],
            adcOffset=self.myconfig["adc_offset"],
            carrierFreq_MHz=self.myconfig["carrierFreq_MHz"],
            nPoints=self.npts,
            nEchoes=self.myconfig["nEchoes"],
            plen=self.myconfig["beta_90_s_sqrtW"],
            repetition_us=self.myconfig["repetition_us"],
            amplitude=self.myconfig["amplitude"],
            tau_us=self.myconfig["tau_us"],
            SW_kHz=self.myconfig["SW_kHz"],
            ret_data=None,
        )
        # }}}
        # {{{setting acq_params
        self.echo_data.set_prop("postproc_type", "proc_Hahn_echoph")
        self.echo_data.set_prop("acq_params", self.myconfig.asdict())
        # }}}
        # {{{ chunking
        self.echo_data.chunk("t", ["ph1", "t2"], [4, -1])
        self.echo_data.setaxis("ph1", r_[0.0, 1.0, 2.0, 3.0] / 4)
        if self.myconfig["nScans"] > 1:
            self.echo_data.setaxis("nScans", r_[0 : self.myconfig["nScans"]])
        self.echo_data.reorder(["ph1", "nScans", "t2"])
        self.echo_data.squeeze()
        self.echo_data.set_units("t2", "s")
        # }}}
        self.myconfig.write()
        return

    def adc_offset(self):
        print("adc was ", self.myconfig["adc_offset"], end=" and ")
        counter = 0
        first = True
        result1 = result2 = result3 = None
        while first or not (result1 == result2) and (result2 == result3):
            first = False
            result1 = SpinCore_pp.adc_offset()
            time.sleep(0.1)
            result2 = SpinCore_pp.adc_offset()
            time.sleep(0.1)
            result3 = SpinCore_pp.adc_offset()
            if counter > 20:
                raise RuntimeError("after 20 tries, I can't stabilize ADC")
            counter += 1
        self.myconfig["adc_offset"] = result3
        print("adc determined to be:", self.myconfig["adc_offset"])

    def acq_NMR(self):
        self.generate_data()
        self.regen_plots()
        return

    def regen_plots(self):
        """Redraws the figure"""
        self.axes.clear()
        self.echo_data.ft("ph1", unitary=True)
        self.echo_data.ft("t2", shift=True)
        self.echo_data.ift("t2")
        filter_timeconst = self.apo_time_const
        self.echo_data *= np.exp(
            -abs(
                (
                    self.echo_data.fromaxis("t2")
                    - self.myconfig["tau_us"] * 1e-6
                )
            )
            / filter_timeconst
        )
        self.echo_data.ft("t2")

        # {{{ pull essential parts of plotting routine
        #    from pyspecdata -- these are pulled from
        #    the plot function inside core
        def pyspec_plot(*args, **kwargs):
            myy = args[0]
            longest_dim = np.argmax(myy.data.shape)
            if len(myy.data.shape) > 1:
                all_but_longest = set(range(len(myy.data.shape))) ^ set(
                    (longest_dim,)
                )
                all_but_longest = list(all_but_longest)
            else:
                all_but_longest = []
            myx = myy.getaxis(myy.dimlabels[longest_dim])
            myxlabel = myy.unitify_axis(longest_dim)
            if len(myy.data.shape) == 1:
                myy = myy.data
            else:
                myy = np.squeeze(
                    myy.data.transpose([longest_dim] + all_but_longest)
                )
            self.axes.plot(myx, myy, **kwargs)
            self.axes.set_xlabel(myxlabel)

        # }}}
        if "nScans" in self.echo_data.dimlabels:
            if int(psp.ndshape(self.echo_data)["nScans"]) > 1:
                multiscan_copy = self.echo_data.C
                many_scans = True
                self.echo_data.mean("nScans")
        else:
            many_scans = False
        noise = self.echo_data["ph1", r_[0, 2, 3]].run(np.std, "ph1")
        signal = abs(self.echo_data["ph1", 1])
        signal -= noise
        for j in self.echo_data.getaxis("ph1"):
            pyspec_plot(
                abs(self.echo_data["ph1":j]), label=f"Δp={j}", alpha=0.5
            )
            if many_scans and j == 1:
                for k in range(psp.ndshape(multiscan_copy)["nScans"]):
                    pyspec_plot(
                        abs(multiscan_copy["ph1":j]["nScans", k]),
                        label=f"Δp=1, scan {k}",
                        alpha=0.2,
                    )
        centerfrq = signal.C.argmax("t2").item()
        self.axes.axvline(x=centerfrq, ls=":", color="r", alpha=0.25)
        pyspec_plot(noise, color="k", label="Noise std", alpha=0.75)
        pyspec_plot(
            signal, color="r", label="abs of signal - noise", alpha=0.75
        )
        self.axes.legend()
        # }}}
        noise = noise["t2":centerfrq]
        signal = signal["t2":centerfrq]
        if signal > 3 * noise:
            Field = (
                self.myconfig["carrierFreq_MHz"]
                / self.myconfig["gamma_eff_MHz_G"]
            )
            self.myconfig["gamma_eff_MHz_G"] -= centerfrq * 1e-6 / Field
            self.myconfig.write()
        else:
            print(
                "*" * 5
                + "warning! SNR looks bad! I'm not adjusting γ!!!"
                + "*" * 5
            )  # this is not yet tested!
        self.canvas.draw()
        return

    def create_main_frame(self):
        self.main_frame = QWidget()
        # Create the mpl Figure and FigCanvas objects.
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = mplqt5.FigureCanvasQTAgg(self.fig)
        self.canvas.setParent(self.main_frame)
        # {{{ need both of these to get background of figure transparent,
        #     rather than white
        self.fig.set_facecolor("none")
        self.canvas.setStyleSheet("background-color:transparent;")
        # }}}
        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        # Bind the 'pick' event
        self.canvas.mpl_connect("pick_event", self.on_pick)
        # Create the navigation toolbar, tied to the canvas
        self.mpl_toolbar = mplqt5.NavigationToolbar2QT(
            self.canvas, self.main_frame
        )
        # {{{ bottom left with SW, apo, and acquire
        #     button
        self.bottomleft_vbox = QVBoxLayout()
        self.textbox_apo = QLineEdit()
        self.combo_sw = QComboBox()
        self.combo_sw.addItem("200")
        self.combo_sw.addItem("24")
        self.combo_sw.addItem("3.9")
        self.combo_sw.activated[str].connect(self.SW_changed)
        self.set_default_choices()
        self.bottomleft_vbox.addWidget(self.combo_sw)
        self.textbox_apo.editingFinished.connect(self.on_textchange)
        self.bottomleft_vbox.addWidget(self.textbox_apo)
        self.acquire_button = QPushButton("&Acquire NMR")
        self.acquire_button.clicked.connect(self.acq_NMR)
        self.bottomleft_vbox.addWidget(self.acquire_button)
        # }}}
        # {{{ box to stack checkboxes
        self.boxes_vbox = QVBoxLayout()
        self.grid_cb = QCheckBox("Show &Grid")
        self.grid_cb.setChecked(False)
        self.grid_cb.stateChanged.connect(self.regen_plots)
        self.boxes_vbox.addWidget(self.grid_cb)
        self.fmode_cb = QCheckBox("Const &Frq &Mode")
        self.fmode_cb.setChecked(False)
        self.fmode_cb.stateChanged.connect(self.regen_plots)
        self.boxes_vbox.addWidget(self.fmode_cb)
        # }}}
        slider_label = QLabel("Bar width (%):")
        # {{{ box to stack sliders
        self.bottom_right_vbox = QVBoxLayout()
        self.bottom_right_vbox.setContentsMargins(0, 0, 0, 0)
        # self.bottom_right_vbox.setSpacing(0)
        self.adc_offset_button = QPushButton("&ADC Offset")
        self.adc_offset_button.clicked.connect(self.adc_offset)
        self.bottom_right_vbox.addWidget(self.adc_offset_button)
        self.slider_min = QSlider(Qt.Horizontal)
        self.slider_max = QSlider(Qt.Horizontal)
        for ini_val, w in [
            (9819000, self.slider_min),
            (9825000, self.slider_max),
        ]:
            self.on_textchange()
            w.setValue(ini_val)
            w.setTracking(True)
            w.setTickPosition(QSlider.TicksBothSides)
            w.valueChanged.connect(self.regen_plots)
            self.bottom_right_vbox.addWidget(w)
        # }}}
        # {{{ we stack the bottom vboxes side by side
        bottom_hbox = QHBoxLayout()
        bottom_hbox.addLayout(self.bottomleft_vbox)
        bottom_hbox.addLayout(self.boxes_vbox)
        bottom_hbox.addWidget(slider_label)
        bottom_hbox.setAlignment(slider_label, Qt.AlignVCenter)
        bottom_hbox.addLayout(
            self.bottom_right_vbox
        )  # requires a different command!
        # }}}
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(self.mpl_toolbar)
        main_layout.addLayout(bottom_hbox)
        self.main_frame.setLayout(main_layout)
        self.setCentralWidget(self.main_frame)

    def SW_changed(self, arg):
        my_sw = {"200": 200.0, "24": 24.0, "3.9": 3.9}
        self.myconfig["SW_kHz"] = my_sw[arg]
        print("changing SW to", self.myconfig["SW_kHz"])

    def create_status_bar(self):
        self.status_text = QLabel("This is a demo")
        self.statusBar().addWidget(self.status_text, 1)

    def create_menu(self):
        self.file_menu = self.menuBar().addMenu("&File")

        load_file_action = self.create_action(
            "&Save plot",
            shortcut="Ctrl+S",
            slot=self.save_plot,
            tip="Save the plot",
        )
        quit_action = self.create_action(
            "&Quit",
            slot=self.close,
            shortcut="Ctrl+Q",
            tip="Close the application",
        )

        self.add_actions(self.file_menu, (load_file_action, None, quit_action))

        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action(
            "&About", shortcut="F1", slot=self.on_about, tip="About the demo"
        )

        self.add_actions(self.help_menu, (about_action,))

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(
        self,
        text,
        slot=None,
        shortcut=None,
        icon=None,
        tip=None,
        checkable=False,
    ):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            action.triggered.connect(slot)
        if checkable:
            action.setCheckable(True)
        return action


def main():
    myconfig = SpinCore_pp.configuration("active.ini")
    app = QApplication(sys.argv)
    with xepr_from_module() as x:
        tunwin = NMRWindow(x, myconfig)
        tunwin.show()
        app.exec_()
    myconfig.write()

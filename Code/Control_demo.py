import sys
import socket
import struct
import time
import os
import re
import html

import numpy as np

from PySide6 import QtCore, QtWidgets, QtGui

# VScope_common.Buffer[0]=M; VScope_common.Buffer[1]=frequency;


# ------------------ UI style ------------------
def apply_vscope2_style(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")

    app.setStyleSheet("""
    QWidget { background:#15181d; color:#e6e8ee; font-size:10.5pt; }

    QGroupBox {
        border:1px solid #2a2f39; border-radius:12px;
        margin-top:10px; padding:10px;
        background:#171b21;
    }
    QGroupBox::title {
        subcontrol-origin:margin; left:12px; padding:0 6px;
        color:#cfd6e6; font-weight:650;
    }

    QLabel { color:#d9dde7; }

    QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox,QPlainTextEdit {
        background:#0f1217; border:1px solid #2a2f39;
        border-radius:10px;
        padding:3px 10px 3px 10px;
        min-height:18px;
        selection-background-color:#3a465a;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 28px;
        border-left: 1px solid #343c4b;
        border-top-right-radius:10px;
        background:#60656F;
    }
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 28px;
        border-left: 1px solid #343c4b;
        border-bottom-right-radius:10px;
        background:#60656F;
    }
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background:#263049;
    }
    QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
    QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
        background:#1a2234;
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { width: 12px; height: 12px; }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { width: 12px; height: 12px; }

    QPushButton {
        background:#2a3240;
        border:1px solid #313a4a;
        border-radius:12px;
        padding:9px 12px;
        font-weight:650;
        color:#eef1f7;
    }
    QPushButton:hover { background:#303a4a; }
    QPushButton:pressed { background:#242b38; }

    QPushButton[accent="true"] { background:#3a6ea7; border-color:#3a6ea7; }
    QPushButton[accent="true"]:hover { background:#427bb8; }
    QPushButton[accent="true"]:pressed { background:#315f91; }

    QPushButton[danger="true"] { background:#9b3a33; border-color:#9b3a33; }
    QPushButton[danger="true"]:hover { background:#ad433b; }
    QPushButton[danger="true"]:pressed { background:#88312b; }

    QCheckBox { spacing:8px; }

    /* Dark-blue per-channel ARM write enable checkbox (objectName = writeEn) */
    QCheckBox#writeEn::indicator {
        width: 16px; height: 16px;
        border-radius: 4px;
        border:1px solid #2a2f39;
        background:#0f1217;
    }
    QCheckBox#writeEn::indicator:checked {
        border:1px solid #1f4f8a;
        background:#1f4f8a;
    }
    QCheckBox#writeEn::indicator:checked:hover {
        border:1px solid #2560a7;
        background:#2560a7;
    }

    QTabWidget::pane { border:1px solid #2a2f39; border-radius:12px; }
    QTabBar::tab {
        background:#1a1f27; border:1px solid #2a2f39;
        padding:8px 12px; border-top-left-radius:10px; border-top-right-radius:10px;
        color:#cfd6e6;
        margin-right:4px;
    }
    QTabBar::tab:selected { background:#222a35; color:#eef1f7; border-bottom-color:#222a35; }

    QScrollBar:vertical { background:#141820; width:10px; margin:0px; border-radius:5px; }
    QScrollBar::handle:vertical { background:#2a3240; min-height:25px; border-radius:5px; }
    QScrollBar::handle:vertical:hover { background:#334055; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
    QScrollBar:horizontal { height:0px; }
    """)


class UdpVSProtocol:
    MAGIC = b"VS"

    # =========================
    # EDIT THIS:
    # groups of 10 channels
    # 2 -> 20ch, 3 -> 30ch, ...
    # =========================
    GROUPS_10 = 2

    NCH = GROUPS_10 * 10
    DEPTH = 10
    NF = NCH * DEPTH

    LEGACY_LEN = 2 + 4 * NF
    SEQ_LEN = 2 + 4 + 4 * NF
    FMT_FLOATS = "<" + "f" * NF
    FMT_SEQ = "<I"


class UdpReceiverThread(QtCore.QThread):
    rows_ready = QtCore.Signal(object, object)  # rows, stats

    def __init__(self, bind_ip: str, port: int, rcvbuf_bytes: int, parent=None):
        super().__init__(parent)
        self.bind_ip = bind_ip
        self.port = port
        self.rcvbuf_bytes = int(rcvbuf_bytes)
        self._sock = None
        self._stop = False

        self.last_addr = None
        self.bad_len = 0
        self.bad_magic = 0

        self.seq_enabled = False
        self.last_seq = None
        self.seq_drops = 0
        self.seq_reorder = 0
        self.seq_dupe = 0

        self._t_rate = time.perf_counter()
        self._pkts_rate = 0
        self.pkts_per_s = 0.0

        self.max_packets_per_burst = 2048
        self.time_budget_s = 0.003

    def stop(self):
        self._stop = True

    def _open(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.rcvbuf_bytes)
        except OSError:
            pass
        s.bind((self.bind_ip, self.port))
        s.setblocking(False)
        self._sock = s
        try:
            return s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        except OSError:
            return 0

    def run(self):
        try:
            actual_rcvbuf = self._open()
        except Exception as e:
            self.rows_ready.emit(None, {"startup": True, "startup_error": str(e)})
            return

        self.rows_ready.emit(None, {"rcvbuf": actual_rcvbuf, "startup": True})

        while not self._stop:
            t0 = time.perf_counter()
            rows_list = []
            got_any = False

            for _ in range(self.max_packets_per_burst):
                if (time.perf_counter() - t0) > self.time_budget_s:
                    break
                try:
                    data, addr = self._sock.recvfrom(4096)
                except (BlockingIOError, OSError):
                    break

                got_any = True
                self.last_addr = addr

                if len(data) not in (UdpVSProtocol.LEGACY_LEN, UdpVSProtocol.SEQ_LEN):
                    self.bad_len += 1
                    continue
                if data[:2] != UdpVSProtocol.MAGIC:
                    self.bad_magic += 1
                    continue

                if len(data) == UdpVSProtocol.SEQ_LEN:
                    self.seq_enabled = True
                    seq = struct.unpack(UdpVSProtocol.FMT_SEQ, data[2:6])[0]
                    floats = struct.unpack(UdpVSProtocol.FMT_FLOATS, data[6:])

                    if self.last_seq is None:
                        self.last_seq = seq
                    else:
                        expected = (self.last_seq + 1) & 0xFFFFFFFF
                        if seq == expected:
                            self.last_seq = seq
                        else:
                            if seq == self.last_seq:
                                self.seq_dupe += 1
                            elif ((seq - expected) & 0xFFFFFFFF) < 0x80000000:
                                self.seq_drops += int((seq - expected) & 0xFFFFFFFF)
                                self.last_seq = seq
                            else:
                                self.seq_reorder += 1
                else:
                    floats = struct.unpack(UdpVSProtocol.FMT_FLOATS, data[2:])

                flat = np.asarray(floats, dtype=np.float32)
                rows_list.append(flat.reshape(UdpVSProtocol.DEPTH, UdpVSProtocol.NCH))
                self._pkts_rate += 1

            now = time.perf_counter()
            dt = now - self._t_rate
            if dt >= 0.5:
                self.pkts_per_s = self._pkts_rate / dt
                self._pkts_rate = 0
                self._t_rate = now

            rows_out = np.vstack(rows_list).astype(np.float32, copy=False) if rows_list else None
            stats = {
                "last_addr": self.last_addr,
                "bad_len": self.bad_len,
                "bad_magic": self.bad_magic,
                "pkts_per_s": self.pkts_per_s,
                "seq_enabled": self.seq_enabled,
                "last_seq": self.last_seq,
                "seq_drops": self.seq_drops,
                "seq_reorder": self.seq_reorder,
                "seq_dupe": self.seq_dupe,
            }

            if rows_out is not None:
                self.rows_ready.emit(rows_out, stats)

            if not got_any:
                self.msleep(2)

        try:
            self._sock.close()
        except Exception:
            pass
        self._sock = None


# ------------------ DEMO RX THREAD ------------------
# Drop-in (same signals, same constructor args) but generates internal 20kHz demo data.
class DemoReceiverThread(QtCore.QThread):
    rows_ready = QtCore.Signal(object, object)  # rows, stats

    def __init__(self, bind_ip: str, port: int, rcvbuf_bytes: int, parent=None):
        super().__init__(parent)
        self.bind_ip = bind_ip
        self.port = port
        self.rcvbuf_bytes = int(rcvbuf_bytes)
        self._stop = False

        self.last_addr = ("DEMO", 0)
        self.bad_len = 0
        self.bad_magic = 0

        self.seq_enabled = True
        self.last_seq = 0
        self.seq_drops = 0
        self.seq_reorder = 0
        self.seq_dupe = 0

        self._t_rate = time.perf_counter()
        self._pkts_rate = 0
        self.pkts_per_s = 0.0

        # waveform
        self.fs = 20000.0
        self.amp = 1.0
        self.freq = 10.0
        self._phase = 0.0

        # generate bursts (keeps CPU low and stable)
        self.chunk_packets = 50  # 50 pkts * depth=10 => 500 samples => 25ms @20kHz

    def stop(self):
        self._stop = True

    @QtCore.Slot(float, float)
    def set_amp_freq(self, amp: float, freq: float):
        self.amp = float(max(0.0, amp))
        self.freq = float(max(0.0, freq))

    def run(self):
        # startup emit (same shape as UDP thread)
        self.rows_ready.emit(None, {"rcvbuf": self.rcvbuf_bytes, "startup": True})

        depth = UdpVSProtocol.DEPTH
        nch = UdpVSProtocol.NCH
        fs = float(self.fs)

        pkt_period = depth / fs
        chunk_period = self.chunk_packets * pkt_period

        next_t = time.perf_counter()

        while not self._stop:
            now = time.perf_counter()
            if now < next_t:
                time.sleep(max(0.0, next_t - now))
            next_t += chunk_period

            amp = float(self.amp)
            freq = float(self.freq)

            n_pkts = int(self.chunk_packets)
            n_samp = n_pkts * depth

            w = 2.0 * np.pi * freq
            ph0 = self._phase
            ph = ph0 + w * (np.arange(n_samp, dtype=np.float64) / fs)
            self._phase = (ph0 + w * (n_samp / fs)) % (2.0 * np.pi)

            a = amp * np.sin(ph + 0.0)
            b = amp * np.sin(ph - 2.0 * np.pi / 3.0)
            c = amp * np.sin(ph + 2.0 * np.pi / 3.0)

            rows = np.zeros((n_samp, nch), dtype=np.float32)
            rows[:, 0] = amp
            rows[:, 1] = freq
            if nch > 2:
                rows[:, 2] = a.astype(np.float32)
            if nch > 3:
                rows[:, 3] = b.astype(np.float32)
            if nch > 4:
                rows[:, 4] = c.astype(np.float32)

            self.last_seq = (self.last_seq + n_pkts) & 0xFFFFFFFF
            self._pkts_rate += n_pkts

            tnow = time.perf_counter()
            dt = tnow - self._t_rate
            if dt >= 0.5:
                self.pkts_per_s = self._pkts_rate / dt
                self._pkts_rate = 0
                self._t_rate = tnow

            stats = {
                "last_addr": self.last_addr,
                "bad_len": self.bad_len,
                "bad_magic": self.bad_magic,
                "pkts_per_s": self.pkts_per_s,  # packets/s
                "seq_enabled": self.seq_enabled,
                "last_seq": self.last_seq,
                "seq_drops": self.seq_drops,
                "seq_reorder": self.seq_reorder,
                "seq_dupe": self.seq_dupe,
            }

            self.rows_ready.emit(rows, stats)


class VScope2(QtWidgets.QMainWindow):
    def __init__(self, pg, demo_mode: bool = True):
        super().__init__()
        self.pg = pg
        self.demo_mode = bool(demo_mode)

        self.setWindowTitle("VScope2.0" + (" (DEMO)" if self.demo_mode else ""))
        self.resize(1750, 950)

        self.pg.setConfigOption("background", "#0f1217")
        self.pg.setConfigOption("foreground", "#e6e8ee")
        self.pg.setConfigOptions(antialias=False, useOpenGL=True)

        self.nch = UdpVSProtocol.NCH
        self.depth = UdpVSProtocol.DEPTH
        self.groups_10 = UdpVSProtocol.GROUPS_10

        self.ch_names = [f"Ch{i}" for i in range(self.nch)]

        # default samples (replaces kS spinbox)
        self.max_samples = 50_000
        self.buf = np.zeros((self.max_samples, self.nch), dtype=np.float32)
        self.write_idx = 0
        self.filled = 0

        self._stats = {}
        self.rx_thread = None

        self._rcvbuf_bytes = 4 * 1024 * 1024

        self.ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ctrl_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ctrl_bound = False
        self._last_sent = np.full((self.nch,), np.nan, dtype=np.float32)

        # demo “remote vars”
        self._demo_amp = 1.0
        self._demo_freq = 10.0

        # last received value (for readback display when writeEn is OFF)
        self._last_rx_row = np.zeros((self.nch,), dtype=np.float32)

        # NEW: time-axis based on estimated sps/ch
        self._sps_filt = None
        self._last_xmax = None
        self._x_label_mode_time = False  # switches bottom label once we have rate

        base = np.array([1, 2, 5], dtype=float)
        decades = 10.0 ** np.arange(-5, 7)
        self.yvals = np.concatenate([base * d for d in decades])

        self.colors = [
            "#5b86b3", "#6b7f9b", "#5a8f8a", "#5aa07d", "#86a867",
            "#c7b05a", "#c78f62", "#c79a5a", "#c77a62", "#5b86b3",
            "#6b7f9b", "#5a8f8a", "#5aa07d", "#86a867", "#c7b05a",
            "#c78f62", "#c79a5a", "#c77a62", "#6f6acb", "#6b3fb8",
        ]

        self.active_label_items = []
        self.cursor_lines = []
        self.cursor_pos_1 = None                    # <-- Add
        self.cursor_pos_2 = None                    # <-- Add
        
        self._build_ui()
        self._apply_ylim()
        self._apply_xrange()

        self.plot_timer = QtCore.QTimer(self)
        self.plot_timer.setInterval(33)
        self.plot_timer.timeout.connect(self._plot_tick)

        self._map_debounce = QtCore.QTimer(self)
        self._map_debounce.setSingleShot(True)
        self._map_debounce.setInterval(250)
        self._map_debounce.timeout.connect(self._apply_mapping_from_text)

    def _set_status(self, text: str):
        self.status.setPlainText(str(text))

    def _elide(self, text: str, widget: QtWidgets.QWidget, width_px: int) -> str:
        fm = widget.fontMetrics()
        return fm.elidedText(text, QtCore.Qt.ElideRight, max(10, int(width_px)))

    def _set_plot_samples(self, n_samples: int):
        try:
            n_samples = int(n_samples)
        except Exception:
            return
        if n_samples <= 0:
            return

        was_running = self.plot_timer.isActive()
        if was_running:
            self._stop()

        self.max_samples = n_samples
        self.buf = np.zeros((self.max_samples, self.nch), dtype=np.float32)
        self.write_idx = 0
        self.filled = 0
        self._apply_xrange()
        self._set_status(f"Plot samples: {self.max_samples}\n")

        if was_running:
            self._start()

    # ----------------- Mapping parser -----------------
    def _parse_mapping_text(self, txt: str) -> dict:
        out = {}
        if not txt:
            return out

        line_pat = re.compile(r"Buffer\s*\[\s*(\d+)\s*\]\s*=\s*(.+?);", re.IGNORECASE)
        cast_pat = re.compile(r"^\s*\(\s*[A-Za-z_]\w*\s*\)\s*")
        ident_pat = re.compile(r"^\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(\[\s*\d+\s*\])?")

        for m in line_pat.finditer(txt):
            idx = int(m.group(1))
            rhs = m.group(2).strip()

            while True:
                new_rhs = cast_pat.sub("", rhs)
                if new_rhs != rhs:
                    rhs = new_rhs.strip()
                    continue
                break

            rhs = rhs.lstrip("&*+-~!")

            im = ident_pat.match(rhs)
            if not im:
                continue

            name = im.group(1)
            idx_suffix = im.group(2) or ""

            if "." in name:
                name = name.split(".")[-1]

            name = name + idx_suffix.replace(" ", "")

            if 0 <= idx < self.nch:
                out[idx] = name

        return out

    def _apply_mapping_from_text(self):
        mapping = self._parse_mapping_text(self.map_box.toPlainText())
        if not mapping:
            return

        for idx, name in mapping.items():
            self.ch_names[idx] = name
            if "_r" in name:
                if 0 <= idx < len(self.write_en_checks):
                    self.write_en_checks[idx].blockSignals(True)
                    self.write_en_checks[idx].setChecked(False)
                    self.write_en_checks[idx].blockSignals(False)
                    self._on_write_en_toggled(idx, 0)

        self._apply_channel_names()
        self._sync_all_checkbox()
        self._set_status(f"Mapped {len(mapping)} channel name(s).\n")

    def _apply_channel_names(self):
        for ch, cb in enumerate(self.ch_checks):
            full = self.ch_names[ch]
            cb.setToolTip(f"Ch{ch}: {full}")
            cb.setText(self._elide(full, cb, 170))
        for ch, wcb in enumerate(self.write_en_checks):
            wcb.setToolTip(f"ARM write enable for Ch{ch}: {self.ch_names[ch]}")

    # ----------------- UI -----------------
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # CENTER: plots (dynamic tabs)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)

        self.plots = []
        self.curves_groups = []
        
        for g in range(self.groups_10):
            start = g * 10
            end = start + 9
            plotw = self.pg.PlotWidget()
            self._init_plot(plotw, f"Ch{start}–Ch{end}")
            curves = self._make_curves(plotw, start, 10)
            self.plots.append(plotw)
            self.curves_groups.append(curves)
            self.tabs.addTab(plotw, f"Ch {start}–{end}")

        # RIGHT
        right_panel = QtWidgets.QWidget()
        right_panel.setFixedWidth(390)
        right_outer = QtWidgets.QVBoxLayout(right_panel)
        right_outer.setContentsMargins(0, 0, 0, 0)
        right_outer.setSpacing(6)

        self.right_tabs = QtWidgets.QTabWidget()
        self.right_tabs.setDocumentMode(True)

        # -------- RIGHT TAB: Variables --------
        tab_vars = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(tab_vars)
        rv.setSpacing(10)

        gb = QtWidgets.QGroupBox("Ch + Write")
        gl = QtWidgets.QVBoxLayout(gb)
        gl.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        self.chk_all = QtWidgets.QCheckBox("All (plot)")
        self.chk_all.setTristate(True)
        self.chk_all.setCheckState(QtCore.Qt.Checked)
        top.addWidget(self.chk_all)
        top.addStretch(1)
        gl.addLayout(top)

        hint = QtWidgets.QLabel("Blue box = ARM write enable per channel (unchecked = readback display)")
        hint.setStyleSheet("QLabel{ color:#9aa6b8; }")
        gl.addWidget(hint)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        cont = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(6)

        self.ch_checks = []
        self.write_en_checks = []
        self.write_boxes = []

        for ch in range(self.nch):
            roww = QtWidgets.QWidget()
            rowl = QtWidgets.QHBoxLayout(roww)
            rowl.setContentsMargins(0, 0, 0, 0)
            rowl.setSpacing(10)

            cb = QtWidgets.QCheckBox(f"Ch{ch}")
            cb.setChecked(True)
            cb.setMinimumWidth(140)

            wcb = QtWidgets.QCheckBox("")
            wcb.setObjectName("writeEn")
            wcb.setChecked(True)
            wcb.setFixedWidth(20)

            sb = QtWidgets.QDoubleSpinBox()
            sb.setDecimals(2)
            sb.setSingleStep(1.0)
            sb.setRange(-1e9, 1e9)
            sb.setValue(0.0)
            sb.setFixedWidth(115)
            sb.setFixedHeight(24)
            sb.setAlignment(QtCore.Qt.AlignRight)

            rowl.addWidget(cb)
            rowl.addWidget(wcb)
            rowl.addStretch(1)
            rowl.addWidget(sb)
            v.addWidget(roww)

            self.ch_checks.append(cb)
            self.write_en_checks.append(wcb)
            self.write_boxes.append(sb)

            cb.stateChanged.connect(self._sync_all_checkbox)

            # when writeEn toggles: lock/unlock editing + immediate readback update
            wcb.stateChanged.connect(lambda state, ch=ch: self._on_write_en_toggled(ch, state))

            sb.setKeyboardTracking(False)
            sb.editingFinished.connect(lambda ch=ch, sb=sb: self._send_vw(ch, float(sb.value())))

        v.addStretch(1)
        scroll.setWidget(cont)
        gl.addWidget(scroll)

        rv.addWidget(gb)
        rv.addStretch(1)

        # -------- RIGHT TAB: RUN --------
        tab_right_settings = QtWidgets.QWidget()
        rs = QtWidgets.QVBoxLayout(tab_right_settings)
        rs.setSpacing(10)

        gb_run = QtWidgets.QGroupBox("Run + Save")
        rg = QtWidgets.QGridLayout(gb_run)
        rg.setVerticalSpacing(8)

        rg.addWidget(QtWidgets.QLabel("Samples"), 0, 0)

        samples_row = QtWidgets.QHBoxLayout()
        self.btn_s_1k = QtWidgets.QPushButton("1k")
        self.btn_s_10k = QtWidgets.QPushButton("10k")
        self.btn_s_100k = QtWidgets.QPushButton("100k")
        self.btn_s_1m = QtWidgets.QPushButton("1M")

        for b in (self.btn_s_1k, self.btn_s_10k, self.btn_s_100k, self.btn_s_1m):
            b.setCheckable(True)
            b.setMinimumWidth(70)

        self.samples_group = QtWidgets.QButtonGroup(self)
        self.samples_group.setExclusive(True)
        self.samples_group.addButton(self.btn_s_1k, 1_000)
        self.samples_group.addButton(self.btn_s_10k, 10_000)
        self.samples_group.addButton(self.btn_s_100k, 100_000)
        self.samples_group.addButton(self.btn_s_1m, 1_000_000)

        samples_row.addWidget(self.btn_s_1k)
        samples_row.addWidget(self.btn_s_10k)
        samples_row.addWidget(self.btn_s_100k)
        samples_row.addWidget(self.btn_s_1m)
        samples_row.addStretch(1)

        rg.addLayout(samples_row, 0, 1)

        default_id = 10_000
        if self.max_samples <= 1_000:
            default_id = 1_000
        elif self.max_samples <= 10_000:
            default_id = 10_000
        elif self.max_samples <= 100_000:
            default_id = 100_000
        else:
            default_id = 1_000_000
        btn = self.samples_group.button(default_id)
        if btn:
            btn.setChecked(True)

        self.y_limit_idx = 16
        self.y_limit_label = QtWidgets.QLabel(f"Y-Limit: ±{self.yvals[self.y_limit_idx]}")
        self.y_down_btn = QtWidgets.QPushButton("▼")
        self.y_up_btn = QtWidgets.QPushButton("▲")
        self.y_home_btn = QtWidgets.QPushButton("🏠")

        self.btn_run = QtWidgets.QPushButton("▶ Start")
        self.btn_run.setProperty("accent", True)
        self.btn_run.setEnabled(True)

        self.save_name = QtWidgets.QLineEdit()
        self.save_name.setPlaceholderText("Name")
        self.save_name.setFixedWidth(95)

        self.btn_save = QtWidgets.QPushButton("💾 Save PNG+CSV")
        self.btn_save.setEnabled(True)

        yrow = QtWidgets.QHBoxLayout()
        yrow.addWidget(self.y_limit_label)
        yrow.addStretch(1)
        yrow.addWidget(self.y_down_btn)
        yrow.addWidget(self.y_up_btn)
        yrow.addWidget(self.y_home_btn)
        
        rg.addLayout(yrow, 1, 0, 1, 2)

        rg.addWidget(self.btn_run, 2, 0, 1, 2)

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("Name:"))
        name_row.addWidget(self.save_name)
        name_row.addStretch(1)
        rg.addLayout(name_row, 3, 0, 1, 2)

        rg.addWidget(self.btn_save, 4, 0, 1, 2)

        rs.addWidget(gb_run)

        gb_status = QtWidgets.QGroupBox("Status")
        stl = QtWidgets.QVBoxLayout(gb_status)
        stl.setSpacing(6)

        self.status = QtWidgets.QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
        self.status.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.status.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        line_h = self.status.fontMetrics().lineSpacing()
        self.status.setFixedHeight(int(line_h * 6 + 14))

        stl.addWidget(self.status)
        rs.addWidget(gb_status)

        gb_cursor = QtWidgets.QGroupBox("Cursor Info")
        gb_cursor_layout = QtWidgets.QVBoxLayout(gb_cursor)
        gb_cursor_layout.setSpacing(8)

        # Delta Time row
        dtime_row = QtWidgets.QHBoxLayout()
        dtime_row.addWidget(QtWidgets.QLabel("Δ Time [S or s]:"))
        self.cursor_dtime = QtWidgets.QLineEdit()
        self.cursor_dtime.setReadOnly(True)
        self.cursor_dtime.setFixedWidth(140)
        dtime_row.addStretch(1)
        dtime_row.addWidget(self.cursor_dtime)
        

        # Frequency row
        freq_row = QtWidgets.QHBoxLayout()
        freq_row.addWidget(QtWidgets.QLabel("Frequency:"))
        self.cursor_freq = QtWidgets.QLineEdit()
        self.cursor_freq.setReadOnly(True)
        self.cursor_freq.setFixedWidth(140)
        freq_row.addStretch(1)
        freq_row.addWidget(self.cursor_freq)
        

        gb_cursor_layout.addLayout(dtime_row)
        gb_cursor_layout.addLayout(freq_row)

        rs.addWidget(gb_cursor)

        self.logo = QtWidgets.QLabel("VScope2.0")
        self.logo.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        f = QtGui.QFont()
        f.setPointSize(11)
        f.setBold(True)
        self.logo.setFont(f)
        self.logo.setStyleSheet("QLabel{ color:#9aa6b8; padding:4px 6px; }")
        rs.addWidget(self.logo)

        rs.addStretch(1)

        # -------- RIGHT TAB: Options --------
        tab_opts = QtWidgets.QWidget()
        opt = QtWidgets.QVBoxLayout(tab_opts)
        opt.setSpacing(10)

        gb_udp = QtWidgets.QGroupBox("UDP Stream RX")
        form = QtWidgets.QFormLayout(gb_udp)

        self.bind_ip = QtWidgets.QLineEdit("10.0.0.100")
        self.port = QtWidgets.QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(5005)

        self.btn_bind = QtWidgets.QPushButton("Bind")
        self.btn_bind.setProperty("accent", True)
        self.btn_unbind = QtWidgets.QPushButton("Unbind")
        self.btn_unbind.setProperty("danger", True)
        self.btn_unbind.setEnabled(False)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.btn_bind)
        row.addWidget(self.btn_unbind)

        form.addRow("Bind IP:", self.bind_ip)
        form.addRow("Port:", self.port)
        form.addRow(row)
        opt.addWidget(gb_udp)

        gb_ctrl = QtWidgets.QGroupBox("Control TX (VW)")
        form2 = QtWidgets.QFormLayout(gb_ctrl)

        self.ctrl_ip = QtWidgets.QLineEdit("10.0.0.60")
        self.ctrl_port = QtWidgets.QSpinBox()
        self.ctrl_port.setRange(1, 65535)
        self.ctrl_port.setValue(5006)

        self.ctrl_arm = QtWidgets.QCheckBox("ARM writes (global)")
        self.ctrl_arm.setChecked(True)

        form2.addRow("STM32 IP:", self.ctrl_ip)
        form2.addRow("STM32 Port:", self.ctrl_port)
        form2.addRow(self.ctrl_arm)
        opt.addWidget(gb_ctrl)

        gb_names = QtWidgets.QGroupBox("Channel Names (paste from uC)")
        ng = QtWidgets.QVBoxLayout(gb_names)
        ng.setSpacing(8)

        self.map_box = QtWidgets.QPlainTextEdit()
        self.map_box.setPlaceholderText(
            "Paste lines like:\n"
            "VScope_common.Buffer[0]=counter_M4;\n"
            "VScope_common.Buffer[1]=sine;\n"
        )
        self.map_box.setFixedHeight(240)
        self.map_box.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)

        self.map_save = QtWidgets.QPushButton("💾 Save Channel Names")
        self.map_load = QtWidgets.QPushButton("Load Channel Names")

        ng.addWidget(self.map_box)
        ng.addWidget(self.map_save)
        ng.addWidget(self.map_load)

        opt.addWidget(gb_names)
        opt.addStretch(1)

        self.right_tabs.addTab(tab_right_settings, "RUN")
        self.right_tabs.addTab(tab_vars, "Variables")
        self.right_tabs.addTab(tab_opts, "Options")

        right_outer.addWidget(self.right_tabs)

        # root layout: ONLY scope + right tab
        root.addWidget(self.tabs, 1)
        root.addWidget(right_panel, 0)

        # signals
        self.btn_bind.clicked.connect(self._bind)
        self.btn_unbind.clicked.connect(self._unbind)
        self.btn_run.clicked.connect(self._toggle_run)

        self.y_down_btn.clicked.connect(self._decrease_y_limit)
        self.y_up_btn.clicked.connect(self._increase_y_limit)
        self.y_home_btn.clicked.connect(self._set_home_limit)
        self.chk_all.clicked.connect(self._toggle_all_channels_clicked)
        self.btn_save.clicked.connect(self._save_png_csv)

        self.map_box.textChanged.connect(lambda: self._map_debounce.start())
        self.map_load.clicked.connect(self._map_load)
        self.map_save.clicked.connect(self._map_save)

        # sample buttons
        self.samples_group.idClicked.connect(self._set_plot_samples)

        self._apply_channel_names()
        self._set_status("Unbound.\nPress Start to auto-bind.\n")

        self._apply_channel_names()
        if self.demo_mode:
            self._set_status("DEMO mode.\nPress Start to auto-bind.\n")
        else:
            self._set_status("Unbound.\nPress Start to auto-bind.\n")

        for cursor in self.cursor_lines:
            cursor.sigPositionChanged.connect(self._on_cursor_moved)

    def _init_plot(self, plotw, title: str):
        plotw.showGrid(x=True, y=True, alpha=0.22)
        plotw.plotItem.setClipToView(True)
        plotw.plotItem.setDownsampling(auto=True, mode="peak")
        plotw.setLabel("bottom", "sample")
        plotw.setLabel("left", "value")
        plotw.setTitle(title)

        # Add vertical cursor line (invisible by default)
        cursor1 = self.pg.InfiniteLine(pos=0, angle=90, movable=True, pen=self.pg.mkPen("#ffffff", width=1))
        cursor1.setZValue(999)
        
        cursor2 = self.pg.InfiniteLine(pos=0, angle=90, movable=True, pen=self.pg.mkPen("#ffffff", width=1))
        cursor2.setZValue(999)
        plotw.addItem(cursor2, ignoreBounds=True)
        self.cursor_lines.append(cursor2)

        plotw.addItem(cursor1, ignoreBounds=True)
        self.cursor_lines.append(cursor1)

        # ACTIVE label overlay (per-plot, one for every 10ch scope)
        ti = self.pg.TextItem("", anchor=(0, 0))
        f = QtGui.QFont()
        f.setPointSize(9)
        f.setBold(False)
        ti.setFont(f)
        ti.setZValue(1000)
        plotw.addItem(ti, ignoreBounds=True)
        self.active_label_items.append(ti)
    def _on_cursor_moved(self, cursor):
        # Determine which cursor moved
        if cursor in self.cursor_lines:
            idx = self.cursor_lines.index(cursor)
            pos = cursor.value()
            
            if idx == 0:
                self.cursor_pos_1 = pos
            elif idx == 1:
                self.cursor_pos_2 = pos
        
        self._update_cursor_display()

    def _update_cursor_display(self):

        if self.cursor_pos_1 is None:
            self.cursor_pos_1 = 0
        if self.cursor_pos_2 is None:   
            self.cursor_pos_2 = 0
        lines = []

        delta = abs(self.cursor_pos_2 - self.cursor_pos_1)
        freq = 1.0 / delta if delta > 0 else 0

        if self._sps_filt and self._sps_filt > 0:
            self.cursor_dtime.setText(f"{delta :.6f} s")
            self.cursor_freq.setText(f"{freq:.2f} Hz")   
        else:
            self.cursor_dtime.setText(f"{delta :.6f} S")
            self.cursor_freq.setText(f"0")   


    def _make_curves(self, plotw, ch_start: int, ch_count: int):
        curves = []
        for i in range(ch_count):
            ch = ch_start + i
            pen = self.pg.mkPen(self.colors[ch % len(self.colors)], width=2)
            curves.append(plotw.plot([], [], pen=pen))
        return curves

    # ---------- Read/Write UI behavior ----------
    def _set_spinbox_readonly(self, sb: QtWidgets.QDoubleSpinBox, ro: bool):
        sb.setReadOnly(bool(ro))
        sb.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons if ro else QtWidgets.QAbstractSpinBox.UpDownArrows)
        if ro:
            sb.setStyleSheet("QDoubleSpinBox{ color:#a9b4c4; }")
        else:
            sb.setStyleSheet("")

    def _on_write_en_toggled(self, ch: int, _state: int):
        if not (0 <= ch < self.nch):
            return
        ro = not self.write_en_checks[ch].isChecked()
        sb = self.write_boxes[ch]
        self._set_spinbox_readonly(sb, ro)

        if ro:
            try:
                sb.blockSignals(True)
                sb.setValue(float(self._last_rx_row[ch]))
                sb.blockSignals(False)
            except Exception:
                pass

    # ---------- SAVE ----------
    def _sanitize_name(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
        return s[:64] if s else ""

    def _next_counter(self, folder: str, prefix: str) -> int:
        try:
            files = os.listdir(folder)
        except Exception:
            return 0
        pat = re.compile(rf"^{re.escape(prefix)}_(\d{{4}})\.(png|csv)$", re.IGNORECASE)
        mx = -1
        for fn in files:
            m = pat.match(fn)
            if m:
                try:
                    mx = max(mx, int(m.group(1)))
                except Exception:
                    pass
        return mx + 1

    def _save_png_csv(self):
        data = self._ring_read_last(self.max_samples)
        if data is None or data.size == 0:
            self._set_status("Nothing to save yet.")
            return

        base = self._sanitize_name(self.save_name.text())
        prefix = base if base else "VScope"

        out_dir = os.path.join(os.getcwd(), "Images")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            self._set_status("Failed to create Images\\ folder.")
            return

        idx = self._next_counter(out_dir, prefix)
        stem = f"{prefix}_{idx:04d}"
        png_path = os.path.join(out_dir, stem + ".png")
        csv_path = os.path.join(out_dir, stem + ".csv")

        header = ",".join(self.ch_names)
        try:
            np.savetxt(csv_path, data, delimiter=",", header=header, comments="", fmt="%.9g")
        except Exception:
            self._set_status("CSV save failed.")
            return

        try:
            plotw = self.tabs.currentWidget()
            size = plotw.size()
            img = QtGui.QImage(size.width(), size.height(), QtGui.QImage.Format_ARGB32)
            img.fill(QtCore.Qt.transparent)

            p = QtGui.QPainter(img)
            plotw.render(p)
            p.end()

            dpm = int(round(600.0 / 0.0254))
            img.setDotsPerMeterX(dpm)
            img.setDotsPerMeterY(dpm)

            img.save(png_path, "PNG")
        except Exception:
            self._set_status("PNG save failed (plot render).")
            return

        self._set_status(f"Saved:\nImages\\{stem}.png\nImages\\{stem}.csv")

    # ---------- CONTROL ----------
    def _ensure_ctrl_bound(self):
        if self.ctrl_bound:
            return
        try:
            self.ctrl_sock.bind((self.bind_ip.text().strip(), 0))
            self.ctrl_bound = True
        except Exception:
            pass

    def _send_vw(self, ch: int, value: float):
        if not self.ctrl_arm.isChecked():
            return
        if 0 <= ch < len(self.write_en_checks) and (not self.write_en_checks[ch].isChecked()):
            return

        prev = self._last_sent[ch]
        if np.isfinite(prev) and float(prev) == float(value):
            return
        self._last_sent[ch] = np.float32(value)

        # DEMO: ch0/ch1 controls internal waveform
        if self.demo_mode:
            if ch == 0:
                self._demo_amp = float(value)
            elif ch == 1:
                self._demo_freq = float(value)

            if isinstance(self.rx_thread, DemoReceiverThread):
                try:
                    self.rx_thread.set_amp_freq(self._demo_amp, self._demo_freq)
                except Exception:
                    pass
            return

        # REAL: UDP control TX
        self._ensure_ctrl_bound()
        dst = (self.ctrl_ip.text().strip(), int(self.ctrl_port.value()))
        pkt = struct.pack("<2sBf", b"VW", int(ch) & 0xFF, float(value))
        try:
            self.ctrl_sock.sendto(pkt, dst)
        except Exception:
            pass

    # ---------- STREAM RX ----------
    def _bind(self) -> bool:
        if self.rx_thread is not None:
            return True

        bind_ip = self.bind_ip.text().strip()
        port = int(self.port.value())

        try:
            if self.demo_mode:
                self.rx_thread = DemoReceiverThread(bind_ip, port, rcvbuf_bytes=self._rcvbuf_bytes)
                self.rx_thread.rows_ready.connect(self._on_rows_ready, QtCore.Qt.QueuedConnection)
                self.rx_thread.start()
                try:
                    self.rx_thread.set_amp_freq(self._demo_amp, self._demo_freq)
                except Exception:
                    pass
            else:
                self.rx_thread = UdpReceiverThread(bind_ip, port, rcvbuf_bytes=self._rcvbuf_bytes)
                self.rx_thread.rows_ready.connect(self._on_rows_ready, QtCore.Qt.QueuedConnection)
                self.rx_thread.start()
        except Exception as e:
            self.rx_thread = None
            self._set_status(f"Bind failed:\n{e}")
            return False

        self.btn_bind.setEnabled(False)
        self.btn_unbind.setEnabled(True)
        self._set_status("Bound.\nPress Start to run.\n")
        return True

    def _unbind(self):
        self._stop()
        if self.rx_thread is not None:
            try:
                self.rx_thread.stop()
                self.rx_thread.wait(500)
            except Exception:
                pass
            self.rx_thread = None

        self.btn_bind.setEnabled(True)
        self.btn_unbind.setEnabled(False)
        self.btn_run.setEnabled(True)
        if self.demo_mode:
            self._set_status("DEMO mode.\nPress Start to auto-bind.\n")
        else:
            self._set_status("Unbound.\nPress Start to auto-bind.\n")

    def _toggle_run(self):
        if self.plot_timer.isActive():
            self._stop()
            return

        if self.rx_thread is None:
            ok = self._bind()
            if not ok:
                return

        self._start()

    def _start(self):
        self.btn_run.setText("⏸ Stop")
        self.plot_timer.start()

    def _stop(self):
        self.btn_run.setText("▶ Start")
        self.plot_timer.stop()

    def _apply_ylim(self):
        lim = float(self.yvals[self.y_limit_idx])
        for p in self.plots:
            p.setYRange(-lim, lim)

    def _decrease_y_limit(self):
        if self.y_limit_idx > 0:
            self.y_limit_idx -= 1
            self.y_limit_label.setText(f"Y-Limit: ±{self.yvals[self.y_limit_idx]}")
            self._apply_ylim()

    def _increase_y_limit(self):
        if self.y_limit_idx < len(self.yvals) - 1:
            self.y_limit_idx += 1
            self.y_limit_label.setText(f"Y-Limit: ±{self.yvals[self.y_limit_idx]}")
            self._apply_ylim()

    def _set_home_limit(self):
        self._apply_ylim()
        self._apply_xrange()

    def _apply_xrange(self):
        # if we have a rate, x-range is seconds, otherwise samples
        if self._sps_filt is not None and self._sps_filt > 0:
            xmax = float(self.max_samples) / float(self._sps_filt)
        else:
            xmax = float(self.max_samples)

        for p in self.plots:
            p.setXRange(0.0, xmax, padding=0)

        self._last_xmax = xmax

    def _map_save(self):
        # Save channel names to a file
        base = self._sanitize_name(self.save_name.text())
        prefix = base if base else "VScope"
        filename = "Images/" + prefix + ".txt"
        if not filename:
            return
        try:
            with open(filename, 'w') as f:
                f.write(self.map_box.toPlainText())
        except Exception as e:
            self._set_status(f"Failed to save channel names: {e}")

    def _map_load(self):
        # Load channel names from a file
        base = self._sanitize_name(self.save_name.text())
        prefix = base if base else "VScope"
        filename = "Images/" + prefix + ".txt"
        if not filename:
            return
        try:
            with open(filename, 'r') as f:
                content = f.read()
                self.map_box.setPlainText(content)
        except Exception as e:
            self._set_status(f"Failed to load channel names: {e}")
    # ---------- ALL CHECK ----------
    def _toggle_all_channels_clicked(self, _checked: bool):
        all_plot_on = all(cb.isChecked() for cb in self.ch_checks)
        target = not all_plot_on

        for cb in self.ch_checks:
            cb.blockSignals(True)
            cb.setChecked(target)
            cb.blockSignals(False)

        self.chk_all.blockSignals(True)
        self.chk_all.setCheckState(QtCore.Qt.Checked if target else QtCore.Qt.Unchecked)
        self.chk_all.blockSignals(False)

    def _sync_all_checkbox(self, *_):
        total = len(self.ch_checks)
        n_plot = sum(1 for cb in self.ch_checks if cb.isChecked())

        self.chk_all.blockSignals(True)
        if n_plot == 0:
            self.chk_all.setCheckState(QtCore.Qt.Unchecked)
        elif n_plot == total:
            self.chk_all.setCheckState(QtCore.Qt.Checked)
        else:
            self.chk_all.setCheckState(QtCore.Qt.PartiallyChecked)
        self.chk_all.blockSignals(False)

    # ---------- RING ----------
    def _ring_write_rows(self, rows: np.ndarray):
        nrows = int(rows.shape[0])
        if nrows <= 0:
            return
        end = self.write_idx + nrows
        if end <= self.max_samples:
            self.buf[self.write_idx:end, :] = rows
        else:
            first = self.max_samples - self.write_idx
            self.buf[self.write_idx:self.max_samples, :] = rows[:first, :]
            remain = nrows - first
            self.buf[0:remain, :] = rows[first:first + remain, :]
        self.write_idx = (self.write_idx + nrows) % self.max_samples
        self.filled = min(self.max_samples, self.filled + nrows)

    def _ring_read_last(self, n_visible: int):
        n_visible = int(min(n_visible, self.filled))
        if n_visible <= 0:
            return None
        start = (self.write_idx - n_visible) % self.max_samples
        if start < self.write_idx:
            return self.buf[start:self.write_idx, :].copy()
        return np.vstack((self.buf[start:self.max_samples, :], self.buf[0:self.write_idx, :])).astype(np.float32, copy=False)

    # decimated read for smooth plotting at 1M
    def _ring_read_last_decimated(self, n_visible: int, max_points: int = 9000):
        n_visible = int(min(n_visible, self.filled))
        if n_visible <= 0:
            return None, None, 1

        step = int(np.ceil(n_visible / max_points)) if n_visible > max_points else 1
        if step < 1:
            step = 1

        start = (self.write_idx - n_visible) % self.max_samples
        idx = (start + np.arange(0, n_visible, step, dtype=np.int64)) % self.max_samples
        data = self.buf[idx, :]  # ~max_points rows

        x_samples = np.arange(data.shape[0], dtype=np.float32) * float(step)
        return x_samples, data, step

    @QtCore.Slot(object, object)
    def _on_rows_ready(self, rows, stats):
        self._stats = stats or {}

        if self._stats.get("startup") and self._stats.get("startup_error"):
            self._stop()
            err = self._stats.get("startup_error")
            self.rx_thread = None
            self.btn_bind.setEnabled(True)
            self.btn_unbind.setEnabled(False)
            self.btn_run.setEnabled(True)
            self._set_status(f"Bind failed:\n{err}")
            return

        if rows is not None:
            try:
                self._last_rx_row = np.asarray(rows[-1, :], dtype=np.float32).copy()
            except Exception:
                pass
            self._ring_write_rows(rows)

    def _update_active_labels(self):
        for g in range(self.groups_10):
            start = g * 10
            end = min(start + 10, self.nch)

            lines = []
            for ch in range(start, end):
                if self.ch_checks[ch].isChecked():
                    col = self.colors[ch % len(self.colors)]
                    nm = html.escape(str(self.ch_names[ch]))
                    lines.append(
                        f'<span style="color:{col}; font-weight:800;">■</span> '
                        f'<span style="color:#e6e8ee;">{nm}</span>'
                    )

            ti = self.active_label_items[g] if g < len(self.active_label_items) else None
            if ti is None:
                continue

            if not lines:
                ti.setHtml("")
            else:
                body = "<br>".join(lines)
                html_box = (
                    '<div style="background-color:rgba(15,18,23,170);'
                    'border:1px solid #2a2f39; border-radius:8px; padding:6px 8px;">'
                    '<span style="color:#cfd6e6; font-weight:650;">Legend</span><br>'
                    f'{body}'
                    "</div>"
                )
                ti.setHtml(html_box)

            try:
                vb = self.plots[g].getPlotItem().vb
                (xmin, xmax), (ymin, ymax) = vb.viewRange()
                x = xmin + 0.02 * (xmax - xmin)
                y = ymax - 0.06 * (ymax - ymin)
                ti.setPos(x, y)
            except Exception:
                pass

    def _update_readback_boxes(self):
        for ch in range(self.nch):
            if self.write_en_checks[ch].isChecked():
                sb = self.write_boxes[ch]
                if sb.isReadOnly():
                    self._set_spinbox_readonly(sb, False)
                continue

            sb = self.write_boxes[ch]
            if not sb.isReadOnly():
                self._set_spinbox_readonly(sb, True)

            try:
                sb.blockSignals(True)
                sb.setValue(float(self._last_rx_row[ch]))
                sb.blockSignals(False)
            except Exception:
                pass

    # NEW: estimate sps/ch and convert sample-x to time-x (seconds)
    def _update_sps_filter(self):
        st = self._stats or {}
        pkps = float(st.get("pkts_per_s", 0.0))
        sps_inst = pkps * float(self.depth)  # samples/s per channel

        if sps_inst <= 1.0:
            return None

        # low-pass filter to prevent x-axis jitter
        alpha = 0.15  # 0..1 (higher = reacts faster)
        if self._sps_filt is None:
            self._sps_filt = sps_inst
        else:
            self._sps_filt = (1.0 - alpha) * float(self._sps_filt) + alpha * sps_inst

        return float(self._sps_filt)

    def _maybe_switch_xlabel(self, have_rate: bool):
        if have_rate and not self._x_label_mode_time:
            for p in self.plots:
                p.setLabel("bottom", "time", "s")
            self._x_label_mode_time = True
        elif (not have_rate) and self._x_label_mode_time:
            for p in self.plots:
                p.setLabel("bottom", "sample")
            self._x_label_mode_time = False

    def _maybe_update_xrange(self, xmax: float):
        if xmax <= 0:
            return
        if self._last_xmax is None:
            self._apply_xrange()
            return
        # update only if changed enough (keeps UI stable)
        if abs(xmax - self._last_xmax) / max(1e-9, self._last_xmax) > 0.05:
            for p in self.plots:
                p.setXRange(0.0, xmax, padding=0)
            self._last_xmax = xmax

    def _plot_tick(self):
        x_samples, data, _step = self._ring_read_last_decimated(self.max_samples, max_points=9000)
        if data is None:
            for grp in self.curves_groups:
                for c in grp:
                    c.setData([], [])
            return

        # compute time axis from estimated sps/ch
        sps_f = self._update_sps_filter()
        have_rate = (sps_f is not None and sps_f > 0)
        self._maybe_switch_xlabel(have_rate)

        if have_rate:
            x = x_samples / float(sps_f)  # seconds
        else:
            x = x_samples  # fallback to samples until rate is known

        for g in range(self.groups_10):
            for i in range(10):
                ch = g * 10 + i
                if ch >= self.nch:
                    continue
                curve = self.curves_groups[g][i]
                if self.ch_checks[ch].isChecked():
                    curve.setData(x, data[:, ch])
                else:
                    curve.setData([], [])

        # throttle UI extras (status + readback + legend) ~10 Hz
        if not hasattr(self, "_st_ctr"):
            self._st_ctr = 0
        self._st_ctr += 1

        if (self._st_ctr % 3) == 0:
            self._update_readback_boxes()
            self._update_active_labels()

            # update x-range in seconds when stable
            if have_rate:
                xmax = float(self.max_samples) / float(sps_f)
            else:
                xmax = float(self.max_samples)
            self._maybe_update_xrange(xmax)

            st = self._stats or {}
            addr = st.get("last_addr", None)
            addr_txt = f"{addr[0]}:{addr[1]}" if addr else "-"
            pkps = float(st.get("pkts_per_s", 0.0))
            sps_per_ch = pkps * self.depth

            self._set_status(
                f"{addr_txt} | RX: {sps_per_ch:.0f} sps/ch\n"
                f"filled: {self.filled}/{self.max_samples}\n"
                f"badlen:{st.get('bad_len',0)} badmagic:{st.get('bad_magic',0)}"
            )

    def closeEvent(self, e):
        self._unbind()
        try:
            self.ctrl_sock.close()
        except Exception:
            pass
        e.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)

    if os.path.exists("Vscope.ico"):
        app.setWindowIcon(QtGui.QIcon("Vscope.ico"))

    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    apply_vscope2_style(app)

    import pyqtgraph as pg

    w = VScope2(pg, demo_mode=True)
    if os.path.exists("Vscope.ico"):
        w.setWindowIcon(QtGui.QIcon("Vscope.ico"))
    w.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

#コメントはAIによって自動生成されました

import sys
import serial
import numpy as np
from collections import deque
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# ===== 設定 =====
SERIAL_PORT = "COM8"  # 使用するシリアルポート
BAUDRATE = 115200     # ボーレート

# 中心サブキャリアのインデックス（もし特定インデックスを使うなら設定）
# もし None にすると自動で n_sub//2 を使います
CENTER_INDEX = None

# 観測帯域: 中心周波数 ±5 MHz
OBS_BAND_MHZ = 5.0

# 無線パラメータ（実環境に合わせて変更）
CHANNEL_BW_MHZ = 20.0   # チャネル帯域幅（例: 20MHz）
FFT_SIZE = 64           # OFDM FFT サイズ（例: 64）
# =================

PLOT_WINDOW = 800       # プロットウィンドウのサイズ
BUFFER_LEN = 256        # バッファの長さ
ALPHA_HP = 0.01         # EMA for complex baseline (低周波成分)
MAD_WINDOW = 200        # MADウィンドウの長さ
LEAK = 0.05             # 漏れ係数（エネルギーインテグレータ）
ENERGY_INTEGRATOR_ALPHA = 0.2  # エネルギーインテグレータのスムージング係数
THRESH_MAD_MULT = 6.0   # MADしきい値の乗数
MIN_THRESHOLD = 4.0     # 最小しきい値
EPS = 1e-9              # 小さな値を避けるためのEPS

# シグナルの処理や後述のバックキャスタ検出を行うクラス
class CSIProcessor:
    def __init__(self, n_subcarriers=None):
        self.n_sub = n_subcarriers  # サブキャリア数
        self.complex_baseline = None   # 複素数のベースライン
        self.prev_vec = None           # 前回の複素ベクトル（位相差計算用）
        self.energy_history = deque(maxlen=MAD_WINDOW)  # エネルギー履歴を保持するデック

    def init_buffers(self, n_sub):
        # サブキャリア数に基づいてバッファの初期化を行う
        self.n_sub = n_sub
        self.complex_baseline = np.zeros(n_sub, dtype=complex)
        self.prev_vec = None

    def spatial_detrend(self, v):
        # 複素値の中央値を引いて共通モードを除去する関数
        med_real = np.median(v.real)
        med_imag = np.median(v.imag)
        return v - (med_real + 1j * med_imag)

    def temporal_highpass(self, v):
        # 複素EMAで低周波成分を推定し、それを引く（高域フィルタ）
        if self.complex_baseline is None:
            self.complex_baseline = v.copy()
            return v - self.complex_baseline
        self.complex_baseline = (1 - ALPHA_HP) * self.complex_baseline + ALPHA_HP * v
        return v - self.complex_baseline

    def compute_band_indices(self):
        # 観測帯域に基づいてサブキャリアインデックスを計算する
        spacing = CHANNEL_BW_MHZ / FFT_SIZE  # サブキャリア間隔（MHz）
        offset = int(round(OBS_BAND_MHZ / spacing))  # 観測帯域におけるインデックスのオフセット
        return offset

    def process_vector(self, vec_complex, center_index=None):
        """
        vec_complex: 1D complex numpy array (I + jQ)
        center_index: 明示的な中心インデックス（None の場合はグローバル CENTER_INDEX or n_sub//2 を使う）
        戻り値: measure_z (robust z-like scalar), filtered complex vector
        """
        v = np.array(vec_complex, dtype=complex)
        if self.n_sub is None:
            self.init_buffers(len(v))  # サブキャリア数を初期化

        # 中心インデックスの決定
        if center_index is None:
            if CENTER_INDEX is not None:
                cidx = min(len(v)-1, max(0, CENTER_INDEX))
            else:
                cidx = len(v)//2
        else:
            cidx = center_index

        # 空間的なデトレンド（共通モード除去）
        v_sp = self.spatial_detrend(v)

        # 時間的な高域フィルタ（低周波成分除去）
        v_hp = self.temporal_highpass(v_sp)

        # 観測帯域のインデックス計算
        offset = self.compute_band_indices()
        idx0 = max(0, cidx - offset)
        idx1 = min(self.n_sub, cidx + offset + 1)
        band = v_hp[idx0:idx1]

        # 複素エネルギー（振幅）
        sum_abs = np.sum(np.abs(band))

        # 位相差エネルギー（瞬時周波数に相当）
        phase_diff_energy = 0.0
        if self.prev_vec is not None:
            prev = self.prev_vec[idx0:idx1]
            if len(prev) == len(band):
                # 位相差を計算し、その絶対値の合計をエネルギーとして扱う
                pd = np.angle(band * np.conjugate(prev))
                phase_diff_energy = np.sum(np.abs(pd))

        # 保存
        self.prev_vec = v_hp.copy()

        # 総合的な指標（振幅変化 + 位相変化）
        measure_raw = sum_abs +  (offset * 0.5) * phase_diff_energy

        # 履歴に追加して、robust z-like 正規化を行う
        self.energy_history.append(measure_raw)
        if len(self.energy_history) < 10:
            # 十分なデータがない場合、そのまま戻す
            return float(measure_raw), v_hp

        # robust z-like normalization (median/MAD)
        arr = np.array(self.energy_history)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med)) + EPS
        z_recent = (measure_raw - med) / mad

        return float(z_recent), v_hp

# バックキャスタ検出のクラス
class BackscatterDetector:
    def __init__(self):
        self.integrator = 0.0  # エネルギーインテグレータ
        self.energy_history = deque(maxlen=MAD_WINDOW)  # エネルギー履歴
        self.last_integrator = 0.0  # 前回のインテグレータ値

    def update(self, measure_z):
        # 新しい測定値を更新
        self.energy_history.append(measure_z)
        arr = np.array(self.energy_history)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med)) + EPS

        # しきい値の計算
        thresh = max(MIN_THRESHOLD, med + THRESH_MAD_MULT * mad)

        # 正の変化量をインテグレート
        positive = max(0.0, measure_z - med)
        self.integrator = max(0.0, self.integrator + positive - LEAK)

        # 安定性のためにスムージング
        self.integrator = (1 - ENERGY_INTEGRATOR_ALPHA) * self.last_integrator + ENERGY_INTEGRATOR_ALPHA * self.integrator
        self.last_integrator = self.integrator

        # イベントの検出
        event = self.integrator > thresh
        return float(self.integrator), bool(event), float(thresh)

# グラフ表示とデータ取得を行うウィンドウクラス
class CSIPlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32 CSI Backscatter Detector (IQ-only, ±5MHz)")

        self.ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)  # シリアルポートの設定

        self.data = deque(maxlen=PLOT_WINDOW)  # プロットするデータ
        self.events = deque(maxlen=PLOT_WINDOW)  # イベントデータ
        self.thresholds = deque(maxlen=PLOT_WINDOW)  # しきい値データ

        self.processor = CSIProcessor()  # シグナルプロセッサ
        self.detector = BackscatterDetector()  # バックキャスタ検出器

        self.plot = pg.PlotWidget()  # pyqtgraphのプロットウィジェット
        self.plot.showGrid(x=True, y=True)  # グリッドを表示


# 後方散乱通信 (Backscatter)のWiFiへの応用
ESP32 を用いた後方散乱通信の再現実験サンプル

## 概要

このリポジトリは、ESP32 を使って**後方散乱通信を再現するためのソースコードと手順**をまとめたものです。ESP32 の RMT ドライバを使って 5 MHz の制御信号を生成し、RF スイッチ（HMC349）でアンテナの反射係数を切り替えます。スペクトラムアナライザで 2.437 GHz 搬送波のサイドバンドを観測することで後方散乱を確認できます。

---

## 動作環境

- ESP32 開発ボード
- ESP-IDF v5.x 以上（ESPRESSIF の公式開発フレームワーク）  
- HMC349 SPDT RF スイッチ
- 50 Ω アンテナ
- 外部搬送波発生器（2.437 GHz）
  →　ESP32と[EspRFTestTool](https://docs.espressif.com/projects/esp-test-tools/en/latest/esp32/development_stage/rf_test_guide/rf_test_guide.html)を使用しても可能
- スペクトラムアナライザ
- USB シリアル接続

ESP-IDF の導入方法については公式ドキュメントを参照してください。

---

## ビルドと書き込み手順

### Raspberry Pi Pico (Pico SDK)
1. VSCode のコマンドパレットから **Extensions: Install Extensions** を実行。
2. 検索ボックスに `Raspberry Pi Pico` と入力し、表示された拡張機能をインストール。
3. VSCode で `pico_sdk` を開く。
4. Raspberry Pi Pico を **UF2 モード** で起動。
5. VSCode 下部の **Run** ボタンをクリックしてファームウェアを書き込み。
6. 書き込みが完了すれば成功。

### Arduino IDE
1. Arduino IDE を環境にインストール。
2. **ファイル > 開く** から `simple_backscatter.ino` を開く。
3. シリアルポートにマイコンが接続されていることを確認。
4. **書き込み** を実行。
5. 書き込み後、必要に応じてシリアルモニタで動作を確認。

### ESP32 (ESP-IDF)
1. Visual Studio Code に **Espressif IDF** を [公式ガイド](https://docs.espressif.com/projects/vscode-esp-idf-extension/en/latest/index.html) に従いインストール。
2. `csi_subcarrier_recv` をダウンロード。
3. VSCode でプロジェクトを開く。
4. 下部の **Build, Flash and Monitor** ボタンを順にクリック。
5. Monitor で動作を確認。


---

## ハードウェア接続例
ESP32 GPIO_NUM_4 --------> HMC349 CTRL  
ESP32 3V3 -----------+     HMC349 Vcc  
ESP32 GND -----------+     HMC349 GND  
HMC349 RF2 ---------> Antenna (50Ω)  
外部搬送波発生器 -> アンテナ入力  
スペアナ -> アンテナ出力  


GPIOxx は RMT 信号の出力ピンにしてください

アンテナや RF ケーブルは 50 Ω 構成に統一してください

---

## 実験手順

外部搬送波発生器で 2.437 GHz の連続信号 を供給

ESP32 をリセットして後方散乱制御を開始

スペクトラムアナライザで搬送波の ±5 MHz 付近のピーク を確認

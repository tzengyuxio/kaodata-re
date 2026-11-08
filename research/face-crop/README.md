# 從大圖裁出 4:5 頭像（三國志12 PK、三國志13 PK）

kaodata 覺得 `san12pk-win`（48×60）、`san13pk-win`（72×72）的頭像偏小，想從遊戲的大圖裁出 64×80 或 96×120。這裡用遊戲自己的小圖反推它在大圖上的裁切框，讓裁法有依據，不靠自動找臉。結論與數字見 `notes/san12.md`、`notes/san13.md` 的「裁切位置」一節（2026-10-19）。`san12pk-win` 的匯出直接讀 `data/san12_boxes.json`（改了框要重新匯出）；三國志13 還沒有做成資料集。

## 檔案

| 檔案 | 說明 |
| ---- | ---- |
| `align.py` | 比對：大圖縮小後用 FFT 算加權平方差找粗略位置，再用 Nelder-Mead 細調 x、y、倍率 |
| `san12_boxes.py` | 三國志12：每張 48×60（`KAO_F_M`）在 360×512（`KAO_W_L`）上的框 |
| `san13_faces.py` | 三國志13：讀 `pk/DATA0/1.S13` 的各尺寸頭像（1024、186×90、96×96、72×72） |
| `san13_boxes.py` | 三國志13：72×72、96×96、186×90 在 1024×1024 上的框 |
| `samples.py` | 用找到的框裁出 64×80、96×120 的樣本到 `samples/`（不進版控）；只取 RGB，背景照大圖 alpha 底下畫好的保留 |
| `compare.py` | 同樣 20 人在三國志11（遊戲自己的 64×80）、12、13（裁成 64×80）並排比較，輸出到 `samples/compare/`；三國志13 的框現算 |
| `sizes.py` | 每代各尺寸的比較圖：最大（或 `info.json` 指定）的那張上框出其他尺寸的位置，旁邊並排原始像素，輸出 `samples/sizes/<id>.png`；進版控的是 `sizes/<id>.jpg`（`rimage mozjpeg -q 80 -d sizes samples/sizes/*.png` 瘦身） |
| `sizes_san8_10.py`、`sizes_san11_13.py`、`sizes_san14.py`、`sizes_nobu11_13.py`、`sizes_nobu15_16.py` | 抽出關羽（三國志）、織田信長（信長）在各代每種尺寸的原圖到 `samples/sizes/<id>/`（`NN_<尺寸名>.png`＋`info.json`） |
| `san13_a_boxes.py` | 三國志13：每張 72×72 在 633×900（kao_a）上的框，以及照 4:5 規則換出的裁切框，寫到 `data/san13_a_boxes.json`；`san13pk-win` 的匯出讀它 |
| `san14_boxes.py` | 三國志14：每張 484×512（`face_NNNN_ctr`）在 636×900（`face_NNNN_a`）上的框，以及 4:5 裁切框，寫到 `data/san14_boxes.json`；`san14pk-win` 的匯出讀它 |
| `san14_rules.py` | 三國志14：候選的 4:5 裁法和三國志13 同一批人並排，輸出 `samples/san14_rules.png` |
| `san14_vs_san12.py` | 三國志14 對三國志12：同一張畫的人（預設 5 人，`--names` 是兩邊同名的全部），把三國志12 的 4:5 框換到三國志14 上、用 ctr 框表示成 s、t；`san14_boxes.py` 的 S、T 取這裡的中位數 |
| `eye_level.py` | 用 OpenCV 的 Haar 眼睛偵測量 4:5 頭像裡眼睛的高度，算出三國志14 的框要上移多少才和三國志13 一樣（要另外帶 `opencv-python-headless==4.10.0.84`，5.0 沒有 `CascadeClassifier`） |
| `data/san12_boxes.json` | 三國志12 全部 933 張的框，鍵是頭像號 |
| `data/san13_boxes.json` | 三國志13 抽樣 30 張的框，鍵是圖號 |

框的座標是大圖的像素：`x`、`y`、`w`、`h`，`scale`＝大圖像素／小圖像素，`rmse` 是 0–255 的殘差。三國志13 的 4:5 框是 72×72 的框保持上緣、高度改成寬度的 1.25 倍。

## 執行

要 numpy、scipy，repo 的 `.venv` 沒有裝，用 uv 臨時帶上（在這個目錄下執行）：

```sh
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python san12_boxes.py
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python san13_boxes.py
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python samples.py
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python compare.py
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python sizes_san8_10.py   # 其他 sizes_*.py 同樣跑法
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python sizes.py            # 不加參數：samples/sizes/ 下每一代
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python san14_boxes.py      # 不加參數：全部 1489 張（十多分鐘）；加頭像號：重算那幾張
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy --with opencv-python-headless==4.10.0.84 python eye_level.py
uv run --no-project --python 3.11 --with-requirements ../../requirements.txt --with numpy --with scipy python san14_vs_san12.py --names   # 平行，幾分鐘
```

- `san12_boxes.py` 不加參數會跑全部 933 張並寫回 JSON；加頭像號只印結果。
- `san13_boxes.py` 不加參數跑 30 張抽樣並寫回 JSON；加圖號只印結果。
- 遊戲檔取自 `games/<資料集>/`（`san12pk-win`、`san13pk-win`、`san14pk-win` 等；Steam 安裝目錄裡用到的檔，見 `notes/steam.md`「安裝目錄的刪除」）。

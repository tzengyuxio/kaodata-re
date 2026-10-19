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
```

- `san12_boxes.py` 不加參數會跑全部 933 張並寫回 JSON；加頭像號只印結果。
- `san13_boxes.py` 不加參數跑 30 張抽樣並寫回 JSON；加圖號只印結果。
- 遊戲檔取自 `games/steam/628080/`（三國志12）、`games/steam/363150/`（三國志13）。

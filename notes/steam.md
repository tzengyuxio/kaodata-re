# 用 SteamCMD 下載 Steam 上的 Windows 版遊戲

只取遊戲檔來分析，不在這台 Mac 上執行。

## 安裝

- `brew install --cask steamcmd`。SteamCMD 只有 x86_64 版，Apple Silicon 要先裝 Rosetta 2（`softwareupdate --install-rosetta --agree-to-license`）。
- 第一次執行 `steamcmd +quit` 會自我更新。程式與登入快取放在 `~/Library/Application Support/Steam/`。

## 下載

下載目錄是 `games/steam/<appid>/`。整個 `games/` 都在 `.gitignore` 裡，不會進版控。帳號、密碼、Steam Guard 碼一律自己在終端機輸入，不要寫進檔案或 commit。

```sh
steamcmd +@sSteamCmdForcePlatformType windows \
  +force_install_dir ~/works/kaodata-re/games/steam/<appid> \
  +login <steam 帳號> \
  +app_update <appid> validate +quit
```

- `+force_install_dir` 要放在 `+login` 前面，路徑要寫絕對路徑。
- 登入時會問密碼，接著問 Steam Guard 碼。成功一次之後，SteamCMD 會記住登入，下次只需要帳號名稱。
- 在 Claude Code 裡要自己輸入，例如 `! steamcmd …`（fish 也能用上面的寫法）。
- 只要某一個 depot 時，可以在 SteamCMD 主控台用 `download_depot <appid> <depotid> [manifestid]`，或在 Steam 客戶端開 `steam://open/console`。
- appid 和 depot id 可以在商店網址（`store.steampowered.com/app/<appid>/`）或 SteamDB 查到。

## 下載紀錄

每下載一款就在這裡記一筆：遊戲、appid、depot、build id／日期，以及放到哪個 `games/<dataset-id>/`。

| 遊戲 | appid | depot | build／日期 | 備註 |
| ---- | ----: | ----: | ----------- | ---- |
| 三國志VII with パワーアップキット | 628030 | 628031（manifest 4009306806308534811） | build 2278666／Readme 2017年7月 | 日文版，`games/steam/628030/` |
| 三國志VIII with パワーアップキット | 628040 | 628041（manifest 8731655521113835098） | build 6784390／Readme 2017年8月 | 日文版，`games/steam/628040/` |
| 三國志IX with パワーアップキット | 628050 | 628051（manifest 8109141869183570646） | build 3717947／Readme 2017年10月 | 日文版，`games/steam/628050/` |

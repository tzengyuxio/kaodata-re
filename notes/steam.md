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
| 三國志III | 521710 | 521711（manifest 7000839481615475769） | build 1637863／Readme 2017年2月 | 日文 Windows 版，`games/steam/521710/` |
| 三國志VII with パワーアップキット | 628030 | 628031（manifest 4009306806308534811） | build 2278666／Readme 2017年7月 | 日文版，`games/steam/628030/` |
| 三國志VIII with パワーアップキット | 628040 | 628041（manifest 8731655521113835098） | build 6784390／Readme 2017年8月 | 日文版，`games/steam/628040/` |
| 三國志IX with パワーアップキット | 628050 | 628051（manifest 8109141869183570646） | build 3717947／Readme 2017年10月 | 日文版，`games/steam/628050/` |
| 三國志X with パワーアップキット | 628060 | 628061（manifest 5959563703464050790） | build 2456531／Readme 2017年11月 | 日文版，`games/steam/628060/` |
| 三國志11 with パワーアップキット | 628070 | 628071（manifest 1454871840120194639） | build 2520441 | 日文版，`games/steam/628070/` |
| 信長の野望・革新 with パワーアップキット | 363090 | 363091（manifest 8372108210806459325） | build 1345322 | 日文版，`games/steam/363090/`；匯出用的檔案在 `games/nobu12pk-win/` |
| 信長の野望・天道 with パワーアップキット | 363110 | 363111（manifest 892070077066238385） | build 2338456 | 日文版，`games/steam/363110/`；匯出用的檔案在 `games/nobu13pk-win/` |
| 大航海時代IV with パワーアップキット HD Version | 1424800 | 1424801（manifest 3835565721977098930）、1424802（manifest 2363000941244658290） | build 7195847 | `games/steam/1424800/` |
| 太閤立志伝V DX | 1842810 | 1842811（manifest 2345313088801476794） | build 9163702 | `games/steam/1842810/` |
| 三国志ツクール | 397720 | 397721（manifest 569112156222337293）、413590（manifest 626678814843644848） | build 1022864 | 免費；RES 裡有顏CG「コーエーSLG」DLC 426740 的 `426740J.bin`（內容未查），`games/steam/397720/` |
| 信長の野望・武将風雲録 | 521740 | 521741（manifest 4318626338706197183） | build 1691564／Readme 2017年3月 | 日文 Windows 版，`games/steam/521740/` |
| 信長の野望 | 544990 | 544991（manifest 2677895693165515782） | build 1500360 | `games/steam/544990/` |
| 信長の野望･全国版 | 521660 | 521661（manifest 2989037137317738632） | build 1580548 | `games/steam/521660/` |
| 信長の野望・戦国群雄伝 | 521700 | 521701（manifest 6101076817046192910） | build 1634932／Readme 2017年2月 | 日文 Windows 版，`games/steam/521700/` |
| 信長の野望・覇王伝 with パワーアップキット | 628090 | 628091（manifest 200612931628158698） | build 4567847／Readme 2017年6月 | 日文版，`games/steam/628090/`；匯出用的檔案在 `games/nobu5pk-win/` |
| 信長の野望・将星録 with パワーアップキット | 628100 | 628101（manifest 7230281957580437517） | build 2282008 | 日文版，`games/steam/628100/`；匯出用的檔案在 `games/nobu7pk-win/` |
| 信長の野望・烈風伝 with パワーアップキット | 628110 | 628111（manifest 5760261918083599286） | build 2056798 | 日文版，`games/steam/628110/`；匯出用的檔案在 `games/nobu8pk-win/` |
| 信長の野望・嵐世記 with パワーアップキット | 628120 | 628121（manifest 4732022678497012738） | build 5042351 | 日文版，`games/steam/628120/`；匯出用的檔案在 `games/nobu9pk-win/` |
| 信長の野望・蒼天録 with パワーアップキット | 628130 | 628131（manifest 7451064036601565840） | build 2476690 | 日文版，`games/steam/628130/`；匯出用的檔案在 `games/nobu10pk-win/` |
| 信長の野望・天下創世 with パワーアップキット | 628140 | 628141（manifest 6058273930614473722） | build 2431466 | 日文版，`games/steam/628140/`；匯出用的檔案在 `games/nobu11pk-win/` |
| 信長の野望・天翔記 with パワーアップキット HD Version | 370730 | — | — | 沒有安裝任何 depot（帳號應該沒有這款），`games/steam/370730/` 只有 manifest |

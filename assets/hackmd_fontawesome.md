# Font Awesome (HackMD 風格) 測試文件

這份文件用來測：

- HackMD/CodiMD 常見的 Font Awesome 4 HTML 標記（`<i class="fa ..."></i>`）在 preview 中可以正常顯示
- 後端前處理 `apply_hackmd_fontawesome_icons` 能把 icon 資訊保留下來（`data-codoc-fa-class`）
- 前端 `assets/fontawesome_fix.js` 能在 sanitizer 把 `class` 拿掉時，從 `data-codoc-fa-class` 還原 `.fa` class
- fenced code block 內的內容不應被改寫

> 本專案載入的是 Font Awesome 4.7 CSS。

## 基本圖示（inline）

- 文件：<i class="fa fa-file-text"></i> `fa-file-text`
- 編輯：<i class="fa fa-pencil"></i> `fa-pencil`
- 檢視：<i class="fa fa-eye"></i> `fa-eye`
- 欄位：<i class="fa fa-columns"></i> `fa-columns`
- 相機：<i class="fa fa-camera"></i> `fa-camera`
- GitHub：<i class="fa fa-github"></i> `fa-github`
- Dropbox：<i class="fa fa-dropbox"></i> `fa-dropbox`

## 與文字/Markdown 混用

- **粗體 + icon**：<i class="fa fa-star"></i> **Starred**
- [連結 + icon](https://example.com)：<i class="fa fa-external-link"></i> External
- 標題裡也要能顯示 icon：

### Heading icon <i class="fa fa-anchor"></i>

## 尺寸、固定寬度、旋轉、動畫

- 固定寬度（適合對齊）：
  - <i class="fa fa-fw fa-check"></i> OK
  - <i class="fa fa-fw fa-times"></i> NG

- 尺寸：<i class="fa fa-heart fa-lg"></i> <i class="fa fa-heart fa-2x"></i> <i class="fa fa-heart fa-3x"></i>

- 旋轉：<i class="fa fa-refresh fa-rotate-90"></i> <i class="fa fa-refresh fa-rotate-180"></i> <i class="fa fa-refresh fa-rotate-270"></i>

- 動畫（spin）：<i class="fa fa-cog fa-spin"></i> <i class="fa fa-spinner fa-pulse"></i>

## 清單圖示（fa-ul / fa-li）

<ul class="fa-ul">
  <li><i class="fa fa-li fa-check-square"></i> Item A</li>
  <li><i class="fa fa-li fa-square"></i> Item B</li>
  <li><i class="fa fa-li fa-info-circle"></i> Item C</li>
</ul>

## 既有 data-codoc-fa-class（不應重複加）

<i class="fa fa-bell" data-codoc-fa-class="fa fa-bell"></i> Bell

## fenced code block 內不應被改寫

```html
<i class="fa fa-github"></i>
<i class="fa fa-camera"></i>
```



## 全部 Font Awesome 4.7 icons

來源（與 app 載入一致）：https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css

總數：0



## 全部 Font Awesome 4.7 icons

來源（與 app 載入一致）：https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css

總數：786

<!-- BEGIN: FA47_ALL_ICONS -->
<details>
<summary>展開：完整 icon gallery（全部渲染，較長）</summary>

<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start">
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-500px"></i> fa-500px</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-address-book"></i> fa-address-book</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-address-book-o"></i> fa-address-book-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-address-card"></i> fa-address-card</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-address-card-o"></i> fa-address-card-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-adjust"></i> fa-adjust</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-adn"></i> fa-adn</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-align-center"></i> fa-align-center</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-align-justify"></i> fa-align-justify</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-align-left"></i> fa-align-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-align-right"></i> fa-align-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-amazon"></i> fa-amazon</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ambulance"></i> fa-ambulance</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-american-sign-language-interpreting"></i> fa-american-sign-language-interpreting</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-anchor"></i> fa-anchor</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-android"></i> fa-android</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angellist"></i> fa-angellist</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-double-down"></i> fa-angle-double-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-double-left"></i> fa-angle-double-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-double-right"></i> fa-angle-double-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-double-up"></i> fa-angle-double-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-down"></i> fa-angle-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-left"></i> fa-angle-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-right"></i> fa-angle-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-angle-up"></i> fa-angle-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-apple"></i> fa-apple</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-archive"></i> fa-archive</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-area-chart"></i> fa-area-chart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-down"></i> fa-arrow-circle-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-left"></i> fa-arrow-circle-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-o-down"></i> fa-arrow-circle-o-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-o-left"></i> fa-arrow-circle-o-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-o-right"></i> fa-arrow-circle-o-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-o-up"></i> fa-arrow-circle-o-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-right"></i> fa-arrow-circle-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-circle-up"></i> fa-arrow-circle-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-down"></i> fa-arrow-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-left"></i> fa-arrow-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-right"></i> fa-arrow-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrow-up"></i> fa-arrow-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrows"></i> fa-arrows</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrows-alt"></i> fa-arrows-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrows-h"></i> fa-arrows-h</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-arrows-v"></i> fa-arrows-v</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-asl-interpreting"></i> fa-asl-interpreting</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-assistive-listening-systems"></i> fa-assistive-listening-systems</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-asterisk"></i> fa-asterisk</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-at"></i> fa-at</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-audio-description"></i> fa-audio-description</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-automobile"></i> fa-automobile</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-backward"></i> fa-backward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-balance-scale"></i> fa-balance-scale</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ban"></i> fa-ban</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bandcamp"></i> fa-bandcamp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bank"></i> fa-bank</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bar-chart"></i> fa-bar-chart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bar-chart-o"></i> fa-bar-chart-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-barcode"></i> fa-barcode</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bars"></i> fa-bars</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bath"></i> fa-bath</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bathtub"></i> fa-bathtub</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery"></i> fa-battery</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-0"></i> fa-battery-0</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-1"></i> fa-battery-1</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-2"></i> fa-battery-2</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-3"></i> fa-battery-3</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-4"></i> fa-battery-4</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-empty"></i> fa-battery-empty</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-full"></i> fa-battery-full</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-half"></i> fa-battery-half</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-quarter"></i> fa-battery-quarter</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-battery-three-quarters"></i> fa-battery-three-quarters</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bed"></i> fa-bed</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-beer"></i> fa-beer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-behance"></i> fa-behance</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-behance-square"></i> fa-behance-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bell"></i> fa-bell</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bell-o"></i> fa-bell-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bell-slash"></i> fa-bell-slash</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bell-slash-o"></i> fa-bell-slash-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bicycle"></i> fa-bicycle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-binoculars"></i> fa-binoculars</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-birthday-cake"></i> fa-birthday-cake</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bitbucket"></i> fa-bitbucket</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bitbucket-square"></i> fa-bitbucket-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bitcoin"></i> fa-bitcoin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-black-tie"></i> fa-black-tie</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-blind"></i> fa-blind</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bluetooth"></i> fa-bluetooth</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bluetooth-b"></i> fa-bluetooth-b</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bold"></i> fa-bold</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bolt"></i> fa-bolt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bomb"></i> fa-bomb</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-book"></i> fa-book</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bookmark"></i> fa-bookmark</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bookmark-o"></i> fa-bookmark-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-braille"></i> fa-braille</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-briefcase"></i> fa-briefcase</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-btc"></i> fa-btc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bug"></i> fa-bug</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-building"></i> fa-building</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-building-o"></i> fa-building-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bullhorn"></i> fa-bullhorn</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bullseye"></i> fa-bullseye</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-bus"></i> fa-bus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-buysellads"></i> fa-buysellads</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cab"></i> fa-cab</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calculator"></i> fa-calculator</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar"></i> fa-calendar</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar-check-o"></i> fa-calendar-check-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar-minus-o"></i> fa-calendar-minus-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar-o"></i> fa-calendar-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar-plus-o"></i> fa-calendar-plus-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-calendar-times-o"></i> fa-calendar-times-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-camera"></i> fa-camera</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-camera-retro"></i> fa-camera-retro</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-car"></i> fa-car</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-down"></i> fa-caret-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-left"></i> fa-caret-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-right"></i> fa-caret-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-square-o-down"></i> fa-caret-square-o-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-square-o-left"></i> fa-caret-square-o-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-square-o-right"></i> fa-caret-square-o-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-square-o-up"></i> fa-caret-square-o-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-caret-up"></i> fa-caret-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cart-arrow-down"></i> fa-cart-arrow-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cart-plus"></i> fa-cart-plus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc"></i> fa-cc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-amex"></i> fa-cc-amex</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-diners-club"></i> fa-cc-diners-club</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-discover"></i> fa-cc-discover</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-jcb"></i> fa-cc-jcb</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-mastercard"></i> fa-cc-mastercard</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-paypal"></i> fa-cc-paypal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-stripe"></i> fa-cc-stripe</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cc-visa"></i> fa-cc-visa</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-certificate"></i> fa-certificate</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chain"></i> fa-chain</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chain-broken"></i> fa-chain-broken</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-check"></i> fa-check</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-check-circle"></i> fa-check-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-check-circle-o"></i> fa-check-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-check-square"></i> fa-check-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-check-square-o"></i> fa-check-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-circle-down"></i> fa-chevron-circle-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-circle-left"></i> fa-chevron-circle-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-circle-right"></i> fa-chevron-circle-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-circle-up"></i> fa-chevron-circle-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-down"></i> fa-chevron-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-left"></i> fa-chevron-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-right"></i> fa-chevron-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chevron-up"></i> fa-chevron-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-child"></i> fa-child</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-chrome"></i> fa-chrome</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-circle"></i> fa-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-circle-o"></i> fa-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-circle-o-notch"></i> fa-circle-o-notch</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-circle-thin"></i> fa-circle-thin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-clipboard"></i> fa-clipboard</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-clock-o"></i> fa-clock-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-clone"></i> fa-clone</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-close"></i> fa-close</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cloud"></i> fa-cloud</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cloud-download"></i> fa-cloud-download</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cloud-upload"></i> fa-cloud-upload</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cny"></i> fa-cny</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-code"></i> fa-code</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-code-fork"></i> fa-code-fork</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-codepen"></i> fa-codepen</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-codiepie"></i> fa-codiepie</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-coffee"></i> fa-coffee</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cog"></i> fa-cog</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cogs"></i> fa-cogs</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-columns"></i> fa-columns</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-comment"></i> fa-comment</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-comment-o"></i> fa-comment-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-commenting"></i> fa-commenting</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-commenting-o"></i> fa-commenting-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-comments"></i> fa-comments</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-comments-o"></i> fa-comments-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-compass"></i> fa-compass</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-compress"></i> fa-compress</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-connectdevelop"></i> fa-connectdevelop</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-contao"></i> fa-contao</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-copy"></i> fa-copy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-copyright"></i> fa-copyright</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-creative-commons"></i> fa-creative-commons</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-credit-card"></i> fa-credit-card</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-credit-card-alt"></i> fa-credit-card-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-crop"></i> fa-crop</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-crosshairs"></i> fa-crosshairs</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-css3"></i> fa-css3</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cube"></i> fa-cube</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cubes"></i> fa-cubes</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cut"></i> fa-cut</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-cutlery"></i> fa-cutlery</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dashboard"></i> fa-dashboard</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dashcube"></i> fa-dashcube</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-database"></i> fa-database</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-deaf"></i> fa-deaf</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-deafness"></i> fa-deafness</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dedent"></i> fa-dedent</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-delicious"></i> fa-delicious</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-desktop"></i> fa-desktop</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-deviantart"></i> fa-deviantart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-diamond"></i> fa-diamond</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-digg"></i> fa-digg</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dollar"></i> fa-dollar</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dot-circle-o"></i> fa-dot-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-download"></i> fa-download</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dribbble"></i> fa-dribbble</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-drivers-license"></i> fa-drivers-license</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-drivers-license-o"></i> fa-drivers-license-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-dropbox"></i> fa-dropbox</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-drupal"></i> fa-drupal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-edge"></i> fa-edge</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-edit"></i> fa-edit</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eercast"></i> fa-eercast</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eject"></i> fa-eject</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ellipsis-h"></i> fa-ellipsis-h</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ellipsis-v"></i> fa-ellipsis-v</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-empire"></i> fa-empire</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envelope"></i> fa-envelope</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envelope-o"></i> fa-envelope-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envelope-open"></i> fa-envelope-open</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envelope-open-o"></i> fa-envelope-open-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envelope-square"></i> fa-envelope-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-envira"></i> fa-envira</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eraser"></i> fa-eraser</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-etsy"></i> fa-etsy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eur"></i> fa-eur</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-euro"></i> fa-euro</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-exchange"></i> fa-exchange</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-exclamation"></i> fa-exclamation</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-exclamation-circle"></i> fa-exclamation-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-exclamation-triangle"></i> fa-exclamation-triangle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-expand"></i> fa-expand</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-expeditedssl"></i> fa-expeditedssl</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-external-link"></i> fa-external-link</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-external-link-square"></i> fa-external-link-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eye"></i> fa-eye</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eye-slash"></i> fa-eye-slash</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-eyedropper"></i> fa-eyedropper</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fa"></i> fa-fa</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-facebook"></i> fa-facebook</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-facebook-f"></i> fa-facebook-f</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-facebook-official"></i> fa-facebook-official</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-facebook-square"></i> fa-facebook-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fast-backward"></i> fa-fast-backward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fast-forward"></i> fa-fast-forward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fax"></i> fa-fax</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-feed"></i> fa-feed</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-female"></i> fa-female</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fighter-jet"></i> fa-fighter-jet</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file"></i> fa-file</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-archive-o"></i> fa-file-archive-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-audio-o"></i> fa-file-audio-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-code-o"></i> fa-file-code-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-excel-o"></i> fa-file-excel-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-image-o"></i> fa-file-image-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-movie-o"></i> fa-file-movie-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-o"></i> fa-file-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-pdf-o"></i> fa-file-pdf-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-photo-o"></i> fa-file-photo-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-picture-o"></i> fa-file-picture-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-powerpoint-o"></i> fa-file-powerpoint-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-sound-o"></i> fa-file-sound-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-text"></i> fa-file-text</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-text-o"></i> fa-file-text-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-video-o"></i> fa-file-video-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-word-o"></i> fa-file-word-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-file-zip-o"></i> fa-file-zip-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-files-o"></i> fa-files-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-film"></i> fa-film</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-filter"></i> fa-filter</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fire"></i> fa-fire</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fire-extinguisher"></i> fa-fire-extinguisher</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-firefox"></i> fa-firefox</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-first-order"></i> fa-first-order</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flag"></i> fa-flag</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flag-checkered"></i> fa-flag-checkered</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flag-o"></i> fa-flag-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flash"></i> fa-flash</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flask"></i> fa-flask</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-flickr"></i> fa-flickr</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-floppy-o"></i> fa-floppy-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-folder"></i> fa-folder</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-folder-o"></i> fa-folder-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-folder-open"></i> fa-folder-open</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-folder-open-o"></i> fa-folder-open-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-font"></i> fa-font</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-font-awesome"></i> fa-font-awesome</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fonticons"></i> fa-fonticons</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-fort-awesome"></i> fa-fort-awesome</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-forumbee"></i> fa-forumbee</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-forward"></i> fa-forward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-foursquare"></i> fa-foursquare</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-free-code-camp"></i> fa-free-code-camp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-frown-o"></i> fa-frown-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-futbol-o"></i> fa-futbol-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gamepad"></i> fa-gamepad</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gavel"></i> fa-gavel</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gbp"></i> fa-gbp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ge"></i> fa-ge</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gear"></i> fa-gear</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gears"></i> fa-gears</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-genderless"></i> fa-genderless</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-get-pocket"></i> fa-get-pocket</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gg"></i> fa-gg</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gg-circle"></i> fa-gg-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gift"></i> fa-gift</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-git"></i> fa-git</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-git-square"></i> fa-git-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-github"></i> fa-github</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-github-alt"></i> fa-github-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-github-square"></i> fa-github-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gitlab"></i> fa-gitlab</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gittip"></i> fa-gittip</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-glass"></i> fa-glass</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-glide"></i> fa-glide</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-glide-g"></i> fa-glide-g</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-globe"></i> fa-globe</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google"></i> fa-google</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google-plus"></i> fa-google-plus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google-plus-circle"></i> fa-google-plus-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google-plus-official"></i> fa-google-plus-official</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google-plus-square"></i> fa-google-plus-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-google-wallet"></i> fa-google-wallet</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-graduation-cap"></i> fa-graduation-cap</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-gratipay"></i> fa-gratipay</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-grav"></i> fa-grav</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-group"></i> fa-group</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-h-square"></i> fa-h-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hacker-news"></i> fa-hacker-news</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-grab-o"></i> fa-hand-grab-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-lizard-o"></i> fa-hand-lizard-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-o-down"></i> fa-hand-o-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-o-left"></i> fa-hand-o-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-o-right"></i> fa-hand-o-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-o-up"></i> fa-hand-o-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-paper-o"></i> fa-hand-paper-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-peace-o"></i> fa-hand-peace-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-pointer-o"></i> fa-hand-pointer-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-rock-o"></i> fa-hand-rock-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-scissors-o"></i> fa-hand-scissors-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-spock-o"></i> fa-hand-spock-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hand-stop-o"></i> fa-hand-stop-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-handshake-o"></i> fa-handshake-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hard-of-hearing"></i> fa-hard-of-hearing</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hashtag"></i> fa-hashtag</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hdd-o"></i> fa-hdd-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-header"></i> fa-header</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-headphones"></i> fa-headphones</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-heart"></i> fa-heart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-heart-o"></i> fa-heart-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-heartbeat"></i> fa-heartbeat</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-history"></i> fa-history</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-home"></i> fa-home</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hospital-o"></i> fa-hospital-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hotel"></i> fa-hotel</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass"></i> fa-hourglass</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-1"></i> fa-hourglass-1</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-2"></i> fa-hourglass-2</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-3"></i> fa-hourglass-3</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-end"></i> fa-hourglass-end</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-half"></i> fa-hourglass-half</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-o"></i> fa-hourglass-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-hourglass-start"></i> fa-hourglass-start</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-houzz"></i> fa-houzz</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-html5"></i> fa-html5</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-i-cursor"></i> fa-i-cursor</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-id-badge"></i> fa-id-badge</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-id-card"></i> fa-id-card</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-id-card-o"></i> fa-id-card-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ils"></i> fa-ils</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-image"></i> fa-image</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-imdb"></i> fa-imdb</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-inbox"></i> fa-inbox</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-indent"></i> fa-indent</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-industry"></i> fa-industry</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-info"></i> fa-info</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-info-circle"></i> fa-info-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-inr"></i> fa-inr</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-instagram"></i> fa-instagram</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-institution"></i> fa-institution</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-internet-explorer"></i> fa-internet-explorer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-intersex"></i> fa-intersex</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ioxhost"></i> fa-ioxhost</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-italic"></i> fa-italic</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-joomla"></i> fa-joomla</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-jpy"></i> fa-jpy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-jsfiddle"></i> fa-jsfiddle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-key"></i> fa-key</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-keyboard-o"></i> fa-keyboard-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-krw"></i> fa-krw</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-language"></i> fa-language</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-laptop"></i> fa-laptop</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-lastfm"></i> fa-lastfm</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-lastfm-square"></i> fa-lastfm-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-leaf"></i> fa-leaf</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-leanpub"></i> fa-leanpub</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-legal"></i> fa-legal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-lemon-o"></i> fa-lemon-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-level-down"></i> fa-level-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-level-up"></i> fa-level-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-life-bouy"></i> fa-life-bouy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-life-buoy"></i> fa-life-buoy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-life-ring"></i> fa-life-ring</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-life-saver"></i> fa-life-saver</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-lightbulb-o"></i> fa-lightbulb-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-line-chart"></i> fa-line-chart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-link"></i> fa-link</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-linkedin"></i> fa-linkedin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-linkedin-square"></i> fa-linkedin-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-linode"></i> fa-linode</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-linux"></i> fa-linux</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-list"></i> fa-list</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-list-alt"></i> fa-list-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-list-ol"></i> fa-list-ol</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-list-ul"></i> fa-list-ul</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-location-arrow"></i> fa-location-arrow</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-lock"></i> fa-lock</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-long-arrow-down"></i> fa-long-arrow-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-long-arrow-left"></i> fa-long-arrow-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-long-arrow-right"></i> fa-long-arrow-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-long-arrow-up"></i> fa-long-arrow-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-low-vision"></i> fa-low-vision</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-magic"></i> fa-magic</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-magnet"></i> fa-magnet</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mail-forward"></i> fa-mail-forward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mail-reply"></i> fa-mail-reply</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mail-reply-all"></i> fa-mail-reply-all</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-male"></i> fa-male</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-map"></i> fa-map</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-map-marker"></i> fa-map-marker</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-map-o"></i> fa-map-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-map-pin"></i> fa-map-pin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-map-signs"></i> fa-map-signs</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mars"></i> fa-mars</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mars-double"></i> fa-mars-double</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mars-stroke"></i> fa-mars-stroke</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mars-stroke-h"></i> fa-mars-stroke-h</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mars-stroke-v"></i> fa-mars-stroke-v</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-maxcdn"></i> fa-maxcdn</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-meanpath"></i> fa-meanpath</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-medium"></i> fa-medium</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-medkit"></i> fa-medkit</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-meetup"></i> fa-meetup</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-meh-o"></i> fa-meh-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mercury"></i> fa-mercury</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-microchip"></i> fa-microchip</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-microphone"></i> fa-microphone</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-microphone-slash"></i> fa-microphone-slash</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-minus"></i> fa-minus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-minus-circle"></i> fa-minus-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-minus-square"></i> fa-minus-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-minus-square-o"></i> fa-minus-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mixcloud"></i> fa-mixcloud</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mobile"></i> fa-mobile</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mobile-phone"></i> fa-mobile-phone</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-modx"></i> fa-modx</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-money"></i> fa-money</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-moon-o"></i> fa-moon-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mortar-board"></i> fa-mortar-board</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-motorcycle"></i> fa-motorcycle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-mouse-pointer"></i> fa-mouse-pointer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-music"></i> fa-music</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-navicon"></i> fa-navicon</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-neuter"></i> fa-neuter</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-newspaper-o"></i> fa-newspaper-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-object-group"></i> fa-object-group</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-object-ungroup"></i> fa-object-ungroup</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-odnoklassniki"></i> fa-odnoklassniki</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-odnoklassniki-square"></i> fa-odnoklassniki-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-opencart"></i> fa-opencart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-openid"></i> fa-openid</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-opera"></i> fa-opera</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-optin-monster"></i> fa-optin-monster</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-outdent"></i> fa-outdent</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pagelines"></i> fa-pagelines</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paint-brush"></i> fa-paint-brush</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paper-plane"></i> fa-paper-plane</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paper-plane-o"></i> fa-paper-plane-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paperclip"></i> fa-paperclip</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paragraph"></i> fa-paragraph</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paste"></i> fa-paste</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pause"></i> fa-pause</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pause-circle"></i> fa-pause-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pause-circle-o"></i> fa-pause-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paw"></i> fa-paw</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-paypal"></i> fa-paypal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pencil"></i> fa-pencil</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pencil-square"></i> fa-pencil-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pencil-square-o"></i> fa-pencil-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-percent"></i> fa-percent</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-phone"></i> fa-phone</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-phone-square"></i> fa-phone-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-photo"></i> fa-photo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-picture-o"></i> fa-picture-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pie-chart"></i> fa-pie-chart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pied-piper"></i> fa-pied-piper</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pied-piper-alt"></i> fa-pied-piper-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pied-piper-pp"></i> fa-pied-piper-pp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pinterest"></i> fa-pinterest</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pinterest-p"></i> fa-pinterest-p</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-pinterest-square"></i> fa-pinterest-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plane"></i> fa-plane</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-play"></i> fa-play</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-play-circle"></i> fa-play-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-play-circle-o"></i> fa-play-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plug"></i> fa-plug</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plus"></i> fa-plus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plus-circle"></i> fa-plus-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plus-square"></i> fa-plus-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-plus-square-o"></i> fa-plus-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-podcast"></i> fa-podcast</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-power-off"></i> fa-power-off</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-print"></i> fa-print</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-product-hunt"></i> fa-product-hunt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-puzzle-piece"></i> fa-puzzle-piece</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-qq"></i> fa-qq</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-qrcode"></i> fa-qrcode</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-question"></i> fa-question</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-question-circle"></i> fa-question-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-question-circle-o"></i> fa-question-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-quora"></i> fa-quora</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-quote-left"></i> fa-quote-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-quote-right"></i> fa-quote-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ra"></i> fa-ra</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-random"></i> fa-random</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ravelry"></i> fa-ravelry</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rebel"></i> fa-rebel</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-recycle"></i> fa-recycle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reddit"></i> fa-reddit</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reddit-alien"></i> fa-reddit-alien</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reddit-square"></i> fa-reddit-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-refresh"></i> fa-refresh</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-registered"></i> fa-registered</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-remove"></i> fa-remove</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-renren"></i> fa-renren</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reorder"></i> fa-reorder</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-repeat"></i> fa-repeat</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reply"></i> fa-reply</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-reply-all"></i> fa-reply-all</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-resistance"></i> fa-resistance</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-retweet"></i> fa-retweet</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rmb"></i> fa-rmb</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-road"></i> fa-road</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rocket"></i> fa-rocket</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rotate-left"></i> fa-rotate-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rotate-right"></i> fa-rotate-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rouble"></i> fa-rouble</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rss"></i> fa-rss</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rss-square"></i> fa-rss-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rub"></i> fa-rub</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ruble"></i> fa-ruble</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-rupee"></i> fa-rupee</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-s15"></i> fa-s15</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-safari"></i> fa-safari</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-save"></i> fa-save</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-scissors"></i> fa-scissors</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-scribd"></i> fa-scribd</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-search"></i> fa-search</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-search-minus"></i> fa-search-minus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-search-plus"></i> fa-search-plus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sellsy"></i> fa-sellsy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-send"></i> fa-send</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-send-o"></i> fa-send-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-server"></i> fa-server</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-share"></i> fa-share</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-share-alt"></i> fa-share-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-share-alt-square"></i> fa-share-alt-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-share-square"></i> fa-share-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-share-square-o"></i> fa-share-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shekel"></i> fa-shekel</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sheqel"></i> fa-sheqel</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shield"></i> fa-shield</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ship"></i> fa-ship</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shirtsinbulk"></i> fa-shirtsinbulk</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shopping-bag"></i> fa-shopping-bag</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shopping-basket"></i> fa-shopping-basket</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shopping-cart"></i> fa-shopping-cart</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-shower"></i> fa-shower</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sign-in"></i> fa-sign-in</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sign-language"></i> fa-sign-language</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sign-out"></i> fa-sign-out</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-signal"></i> fa-signal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-signing"></i> fa-signing</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-simplybuilt"></i> fa-simplybuilt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sitemap"></i> fa-sitemap</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-skyatlas"></i> fa-skyatlas</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-skype"></i> fa-skype</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-slack"></i> fa-slack</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sliders"></i> fa-sliders</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-slideshare"></i> fa-slideshare</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-smile-o"></i> fa-smile-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-snapchat"></i> fa-snapchat</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-snapchat-ghost"></i> fa-snapchat-ghost</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-snapchat-square"></i> fa-snapchat-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-snowflake-o"></i> fa-snowflake-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-soccer-ball-o"></i> fa-soccer-ball-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort"></i> fa-sort</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-alpha-asc"></i> fa-sort-alpha-asc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-alpha-desc"></i> fa-sort-alpha-desc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-amount-asc"></i> fa-sort-amount-asc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-amount-desc"></i> fa-sort-amount-desc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-asc"></i> fa-sort-asc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-desc"></i> fa-sort-desc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-down"></i> fa-sort-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-numeric-asc"></i> fa-sort-numeric-asc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-numeric-desc"></i> fa-sort-numeric-desc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sort-up"></i> fa-sort-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-soundcloud"></i> fa-soundcloud</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-space-shuttle"></i> fa-space-shuttle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-spinner"></i> fa-spinner</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-spoon"></i> fa-spoon</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-spotify"></i> fa-spotify</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-square"></i> fa-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-square-o"></i> fa-square-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stack-exchange"></i> fa-stack-exchange</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stack-overflow"></i> fa-stack-overflow</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star"></i> fa-star</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star-half"></i> fa-star-half</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star-half-empty"></i> fa-star-half-empty</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star-half-full"></i> fa-star-half-full</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star-half-o"></i> fa-star-half-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-star-o"></i> fa-star-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-steam"></i> fa-steam</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-steam-square"></i> fa-steam-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-step-backward"></i> fa-step-backward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-step-forward"></i> fa-step-forward</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stethoscope"></i> fa-stethoscope</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sticky-note"></i> fa-sticky-note</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sticky-note-o"></i> fa-sticky-note-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stop"></i> fa-stop</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stop-circle"></i> fa-stop-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stop-circle-o"></i> fa-stop-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-street-view"></i> fa-street-view</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-strikethrough"></i> fa-strikethrough</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stumbleupon"></i> fa-stumbleupon</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-stumbleupon-circle"></i> fa-stumbleupon-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-subscript"></i> fa-subscript</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-subway"></i> fa-subway</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-suitcase"></i> fa-suitcase</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-sun-o"></i> fa-sun-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-superpowers"></i> fa-superpowers</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-superscript"></i> fa-superscript</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-support"></i> fa-support</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-table"></i> fa-table</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tablet"></i> fa-tablet</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tachometer"></i> fa-tachometer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tag"></i> fa-tag</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tags"></i> fa-tags</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tasks"></i> fa-tasks</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-taxi"></i> fa-taxi</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-telegram"></i> fa-telegram</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-television"></i> fa-television</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tencent-weibo"></i> fa-tencent-weibo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-terminal"></i> fa-terminal</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-text-height"></i> fa-text-height</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-text-width"></i> fa-text-width</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-th"></i> fa-th</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-th-large"></i> fa-th-large</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-th-list"></i> fa-th-list</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-themeisle"></i> fa-themeisle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer"></i> fa-thermometer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-0"></i> fa-thermometer-0</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-1"></i> fa-thermometer-1</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-2"></i> fa-thermometer-2</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-3"></i> fa-thermometer-3</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-4"></i> fa-thermometer-4</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-empty"></i> fa-thermometer-empty</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-full"></i> fa-thermometer-full</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-half"></i> fa-thermometer-half</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-quarter"></i> fa-thermometer-quarter</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thermometer-three-quarters"></i> fa-thermometer-three-quarters</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thumb-tack"></i> fa-thumb-tack</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thumbs-down"></i> fa-thumbs-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thumbs-o-down"></i> fa-thumbs-o-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thumbs-o-up"></i> fa-thumbs-o-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-thumbs-up"></i> fa-thumbs-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-ticket"></i> fa-ticket</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-times"></i> fa-times</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-times-circle"></i> fa-times-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-times-circle-o"></i> fa-times-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-times-rectangle"></i> fa-times-rectangle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-times-rectangle-o"></i> fa-times-rectangle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tint"></i> fa-tint</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-down"></i> fa-toggle-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-left"></i> fa-toggle-left</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-off"></i> fa-toggle-off</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-on"></i> fa-toggle-on</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-right"></i> fa-toggle-right</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-toggle-up"></i> fa-toggle-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-trademark"></i> fa-trademark</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-train"></i> fa-train</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-transgender"></i> fa-transgender</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-transgender-alt"></i> fa-transgender-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-trash"></i> fa-trash</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-trash-o"></i> fa-trash-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tree"></i> fa-tree</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-trello"></i> fa-trello</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tripadvisor"></i> fa-tripadvisor</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-trophy"></i> fa-trophy</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-truck"></i> fa-truck</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-try"></i> fa-try</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tty"></i> fa-tty</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tumblr"></i> fa-tumblr</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tumblr-square"></i> fa-tumblr-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-turkish-lira"></i> fa-turkish-lira</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-tv"></i> fa-tv</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-twitch"></i> fa-twitch</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-twitter"></i> fa-twitter</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-twitter-square"></i> fa-twitter-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-umbrella"></i> fa-umbrella</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-underline"></i> fa-underline</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-undo"></i> fa-undo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-universal-access"></i> fa-universal-access</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-university"></i> fa-university</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-unlink"></i> fa-unlink</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-unlock"></i> fa-unlock</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-unlock-alt"></i> fa-unlock-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-unsorted"></i> fa-unsorted</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-upload"></i> fa-upload</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-usb"></i> fa-usb</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-usd"></i> fa-usd</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user"></i> fa-user</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-circle"></i> fa-user-circle</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-circle-o"></i> fa-user-circle-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-md"></i> fa-user-md</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-o"></i> fa-user-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-plus"></i> fa-user-plus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-secret"></i> fa-user-secret</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-user-times"></i> fa-user-times</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-users"></i> fa-users</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vcard"></i> fa-vcard</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vcard-o"></i> fa-vcard-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-venus"></i> fa-venus</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-venus-double"></i> fa-venus-double</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-venus-mars"></i> fa-venus-mars</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-viacoin"></i> fa-viacoin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-viadeo"></i> fa-viadeo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-viadeo-square"></i> fa-viadeo-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-video-camera"></i> fa-video-camera</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vimeo"></i> fa-vimeo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vimeo-square"></i> fa-vimeo-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vine"></i> fa-vine</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-vk"></i> fa-vk</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-volume-control-phone"></i> fa-volume-control-phone</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-volume-down"></i> fa-volume-down</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-volume-off"></i> fa-volume-off</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-volume-up"></i> fa-volume-up</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-warning"></i> fa-warning</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wechat"></i> fa-wechat</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-weibo"></i> fa-weibo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-weixin"></i> fa-weixin</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-whatsapp"></i> fa-whatsapp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wheelchair"></i> fa-wheelchair</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wheelchair-alt"></i> fa-wheelchair-alt</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wifi"></i> fa-wifi</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wikipedia-w"></i> fa-wikipedia-w</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-window-close"></i> fa-window-close</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-window-close-o"></i> fa-window-close-o</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-window-maximize"></i> fa-window-maximize</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-window-minimize"></i> fa-window-minimize</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-window-restore"></i> fa-window-restore</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-windows"></i> fa-windows</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-won"></i> fa-won</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wordpress"></i> fa-wordpress</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wpbeginner"></i> fa-wpbeginner</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wpexplorer"></i> fa-wpexplorer</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wpforms"></i> fa-wpforms</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-wrench"></i> fa-wrench</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-xing"></i> fa-xing</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-xing-square"></i> fa-xing-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-y-combinator"></i> fa-y-combinator</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-y-combinator-square"></i> fa-y-combinator-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yahoo"></i> fa-yahoo</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yc"></i> fa-yc</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yc-square"></i> fa-yc-square</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yelp"></i> fa-yelp</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yen"></i> fa-yen</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-yoast"></i> fa-yoast</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-youtube"></i> fa-youtube</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-youtube-play"></i> fa-youtube-play</span>
<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><i class="fa fa-youtube-square"></i> fa-youtube-square</span>
</div>
</details>

<details>
<summary>展開：完整 class name 清單</summary>

```text
fa-500px
fa-address-book
fa-address-book-o
fa-address-card
fa-address-card-o
fa-adjust
fa-adn
fa-align-center
fa-align-justify
fa-align-left
fa-align-right
fa-amazon
fa-ambulance
fa-american-sign-language-interpreting
fa-anchor
fa-android
fa-angellist
fa-angle-double-down
fa-angle-double-left
fa-angle-double-right
fa-angle-double-up
fa-angle-down
fa-angle-left
fa-angle-right
fa-angle-up
fa-apple
fa-archive
fa-area-chart
fa-arrow-circle-down
fa-arrow-circle-left
fa-arrow-circle-o-down
fa-arrow-circle-o-left
fa-arrow-circle-o-right
fa-arrow-circle-o-up
fa-arrow-circle-right
fa-arrow-circle-up
fa-arrow-down
fa-arrow-left
fa-arrow-right
fa-arrow-up
fa-arrows
fa-arrows-alt
fa-arrows-h
fa-arrows-v
fa-asl-interpreting
fa-assistive-listening-systems
fa-asterisk
fa-at
fa-audio-description
fa-automobile
fa-backward
fa-balance-scale
fa-ban
fa-bandcamp
fa-bank
fa-bar-chart
fa-bar-chart-o
fa-barcode
fa-bars
fa-bath
fa-bathtub
fa-battery
fa-battery-0
fa-battery-1
fa-battery-2
fa-battery-3
fa-battery-4
fa-battery-empty
fa-battery-full
fa-battery-half
fa-battery-quarter
fa-battery-three-quarters
fa-bed
fa-beer
fa-behance
fa-behance-square
fa-bell
fa-bell-o
fa-bell-slash
fa-bell-slash-o
fa-bicycle
fa-binoculars
fa-birthday-cake
fa-bitbucket
fa-bitbucket-square
fa-bitcoin
fa-black-tie
fa-blind
fa-bluetooth
fa-bluetooth-b
fa-bold
fa-bolt
fa-bomb
fa-book
fa-bookmark
fa-bookmark-o
fa-braille
fa-briefcase
fa-btc
fa-bug
fa-building
fa-building-o
fa-bullhorn
fa-bullseye
fa-bus
fa-buysellads
fa-cab
fa-calculator
fa-calendar
fa-calendar-check-o
fa-calendar-minus-o
fa-calendar-o
fa-calendar-plus-o
fa-calendar-times-o
fa-camera
fa-camera-retro
fa-car
fa-caret-down
fa-caret-left
fa-caret-right
fa-caret-square-o-down
fa-caret-square-o-left
fa-caret-square-o-right
fa-caret-square-o-up
fa-caret-up
fa-cart-arrow-down
fa-cart-plus
fa-cc
fa-cc-amex
fa-cc-diners-club
fa-cc-discover
fa-cc-jcb
fa-cc-mastercard
fa-cc-paypal
fa-cc-stripe
fa-cc-visa
fa-certificate
fa-chain
fa-chain-broken
fa-check
fa-check-circle
fa-check-circle-o
fa-check-square
fa-check-square-o
fa-chevron-circle-down
fa-chevron-circle-left
fa-chevron-circle-right
fa-chevron-circle-up
fa-chevron-down
fa-chevron-left
fa-chevron-right
fa-chevron-up
fa-child
fa-chrome
fa-circle
fa-circle-o
fa-circle-o-notch
fa-circle-thin
fa-clipboard
fa-clock-o
fa-clone
fa-close
fa-cloud
fa-cloud-download
fa-cloud-upload
fa-cny
fa-code
fa-code-fork
fa-codepen
fa-codiepie
fa-coffee
fa-cog
fa-cogs
fa-columns
fa-comment
fa-comment-o
fa-commenting
fa-commenting-o
fa-comments
fa-comments-o
fa-compass
fa-compress
fa-connectdevelop
fa-contao
fa-copy
fa-copyright
fa-creative-commons
fa-credit-card
fa-credit-card-alt
fa-crop
fa-crosshairs
fa-css3
fa-cube
fa-cubes
fa-cut
fa-cutlery
fa-dashboard
fa-dashcube
fa-database
fa-deaf
fa-deafness
fa-dedent
fa-delicious
fa-desktop
fa-deviantart
fa-diamond
fa-digg
fa-dollar
fa-dot-circle-o
fa-download
fa-dribbble
fa-drivers-license
fa-drivers-license-o
fa-dropbox
fa-drupal
fa-edge
fa-edit
fa-eercast
fa-eject
fa-ellipsis-h
fa-ellipsis-v
fa-empire
fa-envelope
fa-envelope-o
fa-envelope-open
fa-envelope-open-o
fa-envelope-square
fa-envira
fa-eraser
fa-etsy
fa-eur
fa-euro
fa-exchange
fa-exclamation
fa-exclamation-circle
fa-exclamation-triangle
fa-expand
fa-expeditedssl
fa-external-link
fa-external-link-square
fa-eye
fa-eye-slash
fa-eyedropper
fa-fa
fa-facebook
fa-facebook-f
fa-facebook-official
fa-facebook-square
fa-fast-backward
fa-fast-forward
fa-fax
fa-feed
fa-female
fa-fighter-jet
fa-file
fa-file-archive-o
fa-file-audio-o
fa-file-code-o
fa-file-excel-o
fa-file-image-o
fa-file-movie-o
fa-file-o
fa-file-pdf-o
fa-file-photo-o
fa-file-picture-o
fa-file-powerpoint-o
fa-file-sound-o
fa-file-text
fa-file-text-o
fa-file-video-o
fa-file-word-o
fa-file-zip-o
fa-files-o
fa-film
fa-filter
fa-fire
fa-fire-extinguisher
fa-firefox
fa-first-order
fa-flag
fa-flag-checkered
fa-flag-o
fa-flash
fa-flask
fa-flickr
fa-floppy-o
fa-folder
fa-folder-o
fa-folder-open
fa-folder-open-o
fa-font
fa-font-awesome
fa-fonticons
fa-fort-awesome
fa-forumbee
fa-forward
fa-foursquare
fa-free-code-camp
fa-frown-o
fa-futbol-o
fa-gamepad
fa-gavel
fa-gbp
fa-ge
fa-gear
fa-gears
fa-genderless
fa-get-pocket
fa-gg
fa-gg-circle
fa-gift
fa-git
fa-git-square
fa-github
fa-github-alt
fa-github-square
fa-gitlab
fa-gittip
fa-glass
fa-glide
fa-glide-g
fa-globe
fa-google
fa-google-plus
fa-google-plus-circle
fa-google-plus-official
fa-google-plus-square
fa-google-wallet
fa-graduation-cap
fa-gratipay
fa-grav
fa-group
fa-h-square
fa-hacker-news
fa-hand-grab-o
fa-hand-lizard-o
fa-hand-o-down
fa-hand-o-left
fa-hand-o-right
fa-hand-o-up
fa-hand-paper-o
fa-hand-peace-o
fa-hand-pointer-o
fa-hand-rock-o
fa-hand-scissors-o
fa-hand-spock-o
fa-hand-stop-o
fa-handshake-o
fa-hard-of-hearing
fa-hashtag
fa-hdd-o
fa-header
fa-headphones
fa-heart
fa-heart-o
fa-heartbeat
fa-history
fa-home
fa-hospital-o
fa-hotel
fa-hourglass
fa-hourglass-1
fa-hourglass-2
fa-hourglass-3
fa-hourglass-end
fa-hourglass-half
fa-hourglass-o
fa-hourglass-start
fa-houzz
fa-html5
fa-i-cursor
fa-id-badge
fa-id-card
fa-id-card-o
fa-ils
fa-image
fa-imdb
fa-inbox
fa-indent
fa-industry
fa-info
fa-info-circle
fa-inr
fa-instagram
fa-institution
fa-internet-explorer
fa-intersex
fa-ioxhost
fa-italic
fa-joomla
fa-jpy
fa-jsfiddle
fa-key
fa-keyboard-o
fa-krw
fa-language
fa-laptop
fa-lastfm
fa-lastfm-square
fa-leaf
fa-leanpub
fa-legal
fa-lemon-o
fa-level-down
fa-level-up
fa-life-bouy
fa-life-buoy
fa-life-ring
fa-life-saver
fa-lightbulb-o
fa-line-chart
fa-link
fa-linkedin
fa-linkedin-square
fa-linode
fa-linux
fa-list
fa-list-alt
fa-list-ol
fa-list-ul
fa-location-arrow
fa-lock
fa-long-arrow-down
fa-long-arrow-left
fa-long-arrow-right
fa-long-arrow-up
fa-low-vision
fa-magic
fa-magnet
fa-mail-forward
fa-mail-reply
fa-mail-reply-all
fa-male
fa-map
fa-map-marker
fa-map-o
fa-map-pin
fa-map-signs
fa-mars
fa-mars-double
fa-mars-stroke
fa-mars-stroke-h
fa-mars-stroke-v
fa-maxcdn
fa-meanpath
fa-medium
fa-medkit
fa-meetup
fa-meh-o
fa-mercury
fa-microchip
fa-microphone
fa-microphone-slash
fa-minus
fa-minus-circle
fa-minus-square
fa-minus-square-o
fa-mixcloud
fa-mobile
fa-mobile-phone
fa-modx
fa-money
fa-moon-o
fa-mortar-board
fa-motorcycle
fa-mouse-pointer
fa-music
fa-navicon
fa-neuter
fa-newspaper-o
fa-object-group
fa-object-ungroup
fa-odnoklassniki
fa-odnoklassniki-square
fa-opencart
fa-openid
fa-opera
fa-optin-monster
fa-outdent
fa-pagelines
fa-paint-brush
fa-paper-plane
fa-paper-plane-o
fa-paperclip
fa-paragraph
fa-paste
fa-pause
fa-pause-circle
fa-pause-circle-o
fa-paw
fa-paypal
fa-pencil
fa-pencil-square
fa-pencil-square-o
fa-percent
fa-phone
fa-phone-square
fa-photo
fa-picture-o
fa-pie-chart
fa-pied-piper
fa-pied-piper-alt
fa-pied-piper-pp
fa-pinterest
fa-pinterest-p
fa-pinterest-square
fa-plane
fa-play
fa-play-circle
fa-play-circle-o
fa-plug
fa-plus
fa-plus-circle
fa-plus-square
fa-plus-square-o
fa-podcast
fa-power-off
fa-print
fa-product-hunt
fa-puzzle-piece
fa-qq
fa-qrcode
fa-question
fa-question-circle
fa-question-circle-o
fa-quora
fa-quote-left
fa-quote-right
fa-ra
fa-random
fa-ravelry
fa-rebel
fa-recycle
fa-reddit
fa-reddit-alien
fa-reddit-square
fa-refresh
fa-registered
fa-remove
fa-renren
fa-reorder
fa-repeat
fa-reply
fa-reply-all
fa-resistance
fa-retweet
fa-rmb
fa-road
fa-rocket
fa-rotate-left
fa-rotate-right
fa-rouble
fa-rss
fa-rss-square
fa-rub
fa-ruble
fa-rupee
fa-s15
fa-safari
fa-save
fa-scissors
fa-scribd
fa-search
fa-search-minus
fa-search-plus
fa-sellsy
fa-send
fa-send-o
fa-server
fa-share
fa-share-alt
fa-share-alt-square
fa-share-square
fa-share-square-o
fa-shekel
fa-sheqel
fa-shield
fa-ship
fa-shirtsinbulk
fa-shopping-bag
fa-shopping-basket
fa-shopping-cart
fa-shower
fa-sign-in
fa-sign-language
fa-sign-out
fa-signal
fa-signing
fa-simplybuilt
fa-sitemap
fa-skyatlas
fa-skype
fa-slack
fa-sliders
fa-slideshare
fa-smile-o
fa-snapchat
fa-snapchat-ghost
fa-snapchat-square
fa-snowflake-o
fa-soccer-ball-o
fa-sort
fa-sort-alpha-asc
fa-sort-alpha-desc
fa-sort-amount-asc
fa-sort-amount-desc
fa-sort-asc
fa-sort-desc
fa-sort-down
fa-sort-numeric-asc
fa-sort-numeric-desc
fa-sort-up
fa-soundcloud
fa-space-shuttle
fa-spinner
fa-spoon
fa-spotify
fa-square
fa-square-o
fa-stack-exchange
fa-stack-overflow
fa-star
fa-star-half
fa-star-half-empty
fa-star-half-full
fa-star-half-o
fa-star-o
fa-steam
fa-steam-square
fa-step-backward
fa-step-forward
fa-stethoscope
fa-sticky-note
fa-sticky-note-o
fa-stop
fa-stop-circle
fa-stop-circle-o
fa-street-view
fa-strikethrough
fa-stumbleupon
fa-stumbleupon-circle
fa-subscript
fa-subway
fa-suitcase
fa-sun-o
fa-superpowers
fa-superscript
fa-support
fa-table
fa-tablet
fa-tachometer
fa-tag
fa-tags
fa-tasks
fa-taxi
fa-telegram
fa-television
fa-tencent-weibo
fa-terminal
fa-text-height
fa-text-width
fa-th
fa-th-large
fa-th-list
fa-themeisle
fa-thermometer
fa-thermometer-0
fa-thermometer-1
fa-thermometer-2
fa-thermometer-3
fa-thermometer-4
fa-thermometer-empty
fa-thermometer-full
fa-thermometer-half
fa-thermometer-quarter
fa-thermometer-three-quarters
fa-thumb-tack
fa-thumbs-down
fa-thumbs-o-down
fa-thumbs-o-up
fa-thumbs-up
fa-ticket
fa-times
fa-times-circle
fa-times-circle-o
fa-times-rectangle
fa-times-rectangle-o
fa-tint
fa-toggle-down
fa-toggle-left
fa-toggle-off
fa-toggle-on
fa-toggle-right
fa-toggle-up
fa-trademark
fa-train
fa-transgender
fa-transgender-alt
fa-trash
fa-trash-o
fa-tree
fa-trello
fa-tripadvisor
fa-trophy
fa-truck
fa-try
fa-tty
fa-tumblr
fa-tumblr-square
fa-turkish-lira
fa-tv
fa-twitch
fa-twitter
fa-twitter-square
fa-umbrella
fa-underline
fa-undo
fa-universal-access
fa-university
fa-unlink
fa-unlock
fa-unlock-alt
fa-unsorted
fa-upload
fa-usb
fa-usd
fa-user
fa-user-circle
fa-user-circle-o
fa-user-md
fa-user-o
fa-user-plus
fa-user-secret
fa-user-times
fa-users
fa-vcard
fa-vcard-o
fa-venus
fa-venus-double
fa-venus-mars
fa-viacoin
fa-viadeo
fa-viadeo-square
fa-video-camera
fa-vimeo
fa-vimeo-square
fa-vine
fa-vk
fa-volume-control-phone
fa-volume-down
fa-volume-off
fa-volume-up
fa-warning
fa-wechat
fa-weibo
fa-weixin
fa-whatsapp
fa-wheelchair
fa-wheelchair-alt
fa-wifi
fa-wikipedia-w
fa-window-close
fa-window-close-o
fa-window-maximize
fa-window-minimize
fa-window-restore
fa-windows
fa-won
fa-wordpress
fa-wpbeginner
fa-wpexplorer
fa-wpforms
fa-wrench
fa-xing
fa-xing-square
fa-y-combinator
fa-y-combinator-square
fa-yahoo
fa-yc
fa-yc-square
fa-yelp
fa-yen
fa-yoast
fa-youtube
fa-youtube-play
fa-youtube-square
```
</details>
<!-- END: FA47_ALL_ICONS -->


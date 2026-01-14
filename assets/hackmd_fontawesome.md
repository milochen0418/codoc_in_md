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

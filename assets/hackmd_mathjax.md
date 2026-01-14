

Ref: https://nathanlesage.github.io/katex-online-editor/

# MathJax (KaTeX) 測試文件

這份文件用來測 Reflex 的 Markdown（remark-math + rehype-katex）是否能正確渲染 HackMD/CodiMD 常用的 TeX 數學式。

## Inline math

- 愛因斯坦：$E = mc^2$
- 三角函數：$f(x) = \sin(x) + \cos(x)$
- 不等式：$\alpha + \beta \ge 0$

> 重要：我們的 markdown 前處理（typography / abbr / inline extensions）不應該改動 `$...$` 裡面的內容。

## Display math

$$
\begin{aligned}
\int_0^\infty e^{-x^2}\,dx &= \frac{\sqrt{\pi}}{2}\\
	ext{keep literal: } a--b\ldots \text{ and quotes like ``x'' should stay as-is.}
\end{aligned}
$$

## Abbreviation interactions

*[API]: Application Programming Interface

- API 這個詞在一般文字中應該變成縮寫（abbr）
- 但在數學式中不應該被替換：$API = 1$

## Other markdown extensions (outside math)

- ==mark== ++insert++ ^sup^ ~sub~
- {ruby 漢字|ㄏㄢˋ ㄗˋ}

## HackMD given test

您可以使用 **MathJax** 語法 來產生 *LaTeX* 數學表達式，如同 [math.stackexchange.com](http://math.stackexchange.com/)，但是開始的 `$` 後面以及結尾的 `$` 前面不能有空白：

The *Gamma function* satisfying $\Gamma(n) = (n-1)!\quad\forall n\in\mathbb N$ is via the Euler integral

使用區塊層級的數學式時，請在您的數學式之前與之後給予 `$$` 以及換行：

$$
x = {-b \pm \sqrt{b^2-4ac} \over 2a}.
$$

$$
\Gamma(z) = \int_0^\infty t^{z-1}e^{-t}dt\,.
$$

> 更多關於 **LaTeX** 數學表達式 [請至這裡](http://meta.math.stackexchange.com/questions/5020/mathjax-basic-tutorial-and-quick-reference)

## 常見語法（Inline）

- 分數與根號：$\frac{a+b}{c} + \sqrt{2}$
- 上下標：$x_i^2 + y_{i+1}^3$
- 向量/粗體：$\vec{v} = \mathbf{A}\,\vec{x}$
- 集合/黑板粗體：$x \in \mathbb{R},\; n \in \mathbb{N}$
- 文字：$\text{speed} = \frac{d}{t}$
- 空白：$a\,b\;c\quad d$

## 常見語法（Display）

### 矩陣

$$
\mathbf{A}=
\begin{bmatrix}
1 & 2 & 3\\
0 & 1 & 4\\
0 & 0 & 1
\end{bmatrix}
$$

### 分段函數（cases）

$$
f(x)=
\begin{cases}
x^2, & x\ge 0\\
-x,  & x<0
\end{cases}
$$

### 求和/極限

$$
\sum_{k=1}^{n} k = \frac{n(n+1)}{2},\qquad
\lim_{x\to 0} \frac{\sin x}{x} = 1
$$

## 另一種定界符：`\\(\\)` 與 `\\[\\]`

這是用 `\( ... \)` 的 inline：\(a^2+b^2=c^2\)

這是用 `\[ ... \]` 的 display：

\[
\left\lVert x \right\rVert = \sqrt{x_1^2+x_2^2+\cdots+x_n^2}
\]

## 與前處理互動（不要改動 math 內容）

- 這些語法 **在一般文字** 中會被轉換：==mark== ++insert++ ^sup^ ~sub~
- 但在數學式內不應被轉換（包含 `--`、`...`、縮寫）：

$$
	ext{==mark== ++insert++ ^sup^ ~sub~ API ... a--b}
$$


## Extremely Edge Case 
I make this extremely edge case from ChatGPT 5.2 
You can see the result of edge case from here if you paste it. 
https://mathjax.github.io/MathJax-demos-web/input/tex2chtml.html

$$
\newcommand{\ZZ}{\mathbb{Z}}
\newcommand{\bad}[1]{\color{red}{#1}}

\text{Macro test: }\ZZ \quad
\text{Frac/Root: }\frac{\sqrt[5]{x^{2_3}+1}}{\left(1+\frac{1}{x}\right)^{n+1}} \quad
\text{Matrix: }\left[\begin{array}{ccc}
1 & 0 & -1\\
\alpha & \beta & \gamma\\
\sum_{k=1}^{n} k & \prod_{i=1}^{m} i & \int_{0}^{\pi}\sin t\,dt
\end{array}\right]
\quad
\text{Sizing: }\left(\frac{a}{b}\right)\Bigg(\frac{c}{d}\Bigg)
\quad
\text{Error trigger: }\bad{\frac{1}{}}   % <- 這行故意錯
$$
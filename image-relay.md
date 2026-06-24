# 图像中转站使用手册（ZenMux / wegoo relay）

把 `render_tree.py --format figure-prompt` 生成的提示词，调用 **gpt-image-2** 画成
谱系图。脚本：[`scripts/gen_figure.py`](scripts/gen_figure.py)。

默认中转站为 **ZenMux**（`--relay zenmux`），也保留 **wegoo**（`--relay wegoo`）。
两家都是 OpenAI 兼容的 Images API（`POST /images/generations`，返回
`data[0].b64_json`），`gen_figure.py` 都能直接用。

> ## ⚠️ 公开仓库泄露警告
> 本文件**包含真实 API Key**，而本仓库是**公开的**（github.com/unumbrela/
> research-genealogy）。**不要 `git push` 本文件**——一旦推送，任何人都能看到并盗用
> 这些 Key。若已不慎推送，请立即到对应中转站后台**重置 / 轮换 Key**。
> 更稳妥的做法：把本文件加入 `.gitignore`，或改用环境变量
> `ZENMUX_API_KEY` / `WEGOO_API_KEY`。

## 凭据

### ZenMux（默认）

| 项 | 值 |
| --- | --- |
| Base URL | `https://zenmux.ai/api/v1` |
| 生图端点 | `POST /images/generations` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 模型 | `gpt-image-2` |
| 控制台 | https://zenmux.ai |
| 文档 | https://zenmux.ai/docs/api/openai/generate-an-image |

```
ZENMUX_API_KEY = sk-ai-v1-613cfb4a569d2deb9f717746ceaf3bf1324c5ab79c372125908670bb03cdc8be
```

### wegoo（备用 · `--relay wegoo`）

| 项 | 值 |
| --- | --- |
| Base URL | `https://ai.wegoo.site/v1` |
| 生图端点 | `POST /images/generations` |
| 改图端点 | `POST /images/edits` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 模型 | `gpt-image-2`（也支持 `gemini-3.1-flash-image` 等） |
| 控制台 | https://ai.wegoo.site/image-generation |
| 文档 | https://docs.wegoo.site/guide/endpoints/images |

```
WEGOO_API_KEY = sk-c74fbda291ffcbaa330ae33c1c91f256b04fe8edb4a266a4dfbd54654a4a1dc4
```

## 直接调用（curl）

```bash
# 默认 ZenMux
curl https://zenmux.ai/api/v1/images/generations \
  -H "Authorization: Bearer sk-ai-v1-613cfb4a569d2deb9f717746ceaf3bf1324c5ab79c372125908670bb03cdc8be" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A clean tomato logo icon on a white background",
    "size": "1024x1024",
    "n": 1
  }'
```

返回为 OpenAI 兼容结构：`data[0].b64_json`（base64 图像，gpt-image 默认）或
`data[0].url`。`gen_figure.py` 两种都能处理。

## 用脚本一键出图（推荐）

`gen_figure.py` 默认走 ZenMux，并自动从本文件读取对应中转站的 API Key
（解析顺序：`--api-key` > 环境变量 `ZENMUX_API_KEY` / `WEGOO_API_KEY` > 本文件里对应
provider 段落的 `sk-…`），所以记录在这里即可直接使用：

```bash
# 1) 谱系数据 → 提示词 → 图（一步到位，默认 ZenMux）
python3 scripts/gen_figure.py examples/diffusion-models.json --out figure.png

# 2) 已有提示词文档 → 图（先把泳道〈待命名〉改成真实路线名，效果更好）
python3 scripts/gen_figure.py examples/diffusion-models-figure-prompt.md \
    --out runs/diffusion-models/figure.png

# 3) 管道：渲染提示词后直接喂给中转站
python3 scripts/render_tree.py examples/diffusion-models.json --format figure-prompt \
  | python3 scripts/gen_figure.py - --out figure.png

# 4) 改用备用中转站 wegoo
python3 scripts/gen_figure.py examples/diffusion-models.json --relay wegoo --out figure.png

# 只想看会发送什么（不联网）
python3 scripts/gen_figure.py figure-prompt.md --print-prompt
```

脚本只发送提示词的**「一、提示词正文」+「二、结构清单」**两节（结构清单是硬约束，
防止模型臆造连接），自动丢弃「三、给作者的话」。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--relay` | `zenmux` | 中转站：`zenmux` 或 `wegoo` |
| `--out` | `<输入名>.png` | 输出 PNG 路径 |
| `--size` | `1536x1024` | 横版适合时间轴；若报错改 `1024x1024` 或 `1024x1536` |
| `--model` | `gpt-image-2` | 中转站模型名 |
| `--n` | `1` | 生成张数（取第 1 张保存） |
| `--base-url` | 见 `--relay` | 覆盖中转站 Base URL（也可用 `$ZENMUX_BASE_URL` / `$WEGOO_BASE_URL`） |
| `--api-key` | 见上方解析顺序 | 也可用 `$ZENMUX_API_KEY` / `$WEGOO_API_KEY` |

## 排查

- `relay HTTP 4xx/5xx …`：脚本会原样打印中转站的报错 JSON。
- gpt-image-2 报错 / 生图不可用：ZenMux 见 https://zenmux.ai/docs ；wegoo 见
  https://docs.wegoo.site/guide/faq/images 。
- 尺寸被拒：改 `--size 1024x1024`。

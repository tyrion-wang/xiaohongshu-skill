# 小红书长文发布扩展实施总结

## 📋 已完成的工作

### 1. 研究了小红书长文编辑器的结构

**关键发现：**
- **标题输入框**: `textarea.d-text`，placeholder="输入标题"
- **正文编辑器**: `div.tiptap.ProseMirror`，contentEditable="true"
- **编辑器类型**: TipTap/ProseMirror 富文本编辑器
- **内容格式**: HTML，段落使用 `<p>` 标签，换行使用 `<br>`

**入口流程：**
1. 点击"写长文" tab
2. 点击"新的创作"按钮
3. 进入长文编辑页面

### 2. 创建了扩展模块

**新增文件：**

#### `scripts/article_support.py`
- `ArticlePublisher` 类：Markdown 转 HTML 转换器
- `ARTICLE_JS_TEMPLATES`: 长文发布的 JavaScript 代码模板
- `generate_article_fill_js()`: 生成填充代码的辅助函数

**支持的 Markdown 格式：**
- `# ## ###` 标题 → 加粗段落
- `**加粗**` → `<strong>`
- `` `代码` `` → `<code>`
- `- 列表` → `• 列表`
- `1. 列表` → `1️⃣ 列表`

#### `scripts/publish_article_example.py`
- 完整的发布示例脚本
- 命令行参数支持
- 错误处理和日志输出

#### `example_article.md`
- Markdown 格式示例文章
- 包含话题标签

### 3. 长文与图文的核心区别

| 特性 | 图文模式 | 长文模式 |
|------|----------|----------|
| 入口 | "上传图文" | "写长文" → "新的创作" |
| 必填图片 | ✅ 必须 | ❌ 可选 |
| 标题元素 | `input` | `textarea.d-text` |
| 话题标签 | 单独选择区域 | 在正文中输入 `#标签` |
| 格式支持 | 基础 | 丰富的富文本格式 |

## 🚀 如何使用

### 方法1: 使用示例脚本

```bash
cd /Users/tyrion/.openclaw/workspace/skills/xiaohongshu/scripts

python3 publish_article_example.py \
  --title "🦞 文章标题" \
  --content-file ../example_article.md \
  --markdown \
  --port 18800
```

### 方法2: 在代码中调用

```python
from cdp_publish import XiaohongshuPublisher
from article_support import ArticlePublisher, ARTICLE_JS_TEMPLATES
import json
import time

# 连接 Chrome
publisher = XiaohongshuPublisher(host="127.0.0.1", port=18800)
publisher.connect()

# 转换 Markdown 为 HTML
markdown_content = """
## 标题
正文内容
#话题标签
"""
html = ArticlePublisher.convert_markdown_to_html(markdown_content)

# 导航到长文编辑页
publisher._navigate("https://creator.xiaohongshu.com/publish/publish")
time.sleep(2)
publisher._evaluate(ARTICLE_JS_TEMPLATES["click_article_tab"])
time.sleep(1)
publisher._evaluate(ARTICLE_JS_TEMPLATES["click_new_creation"])
time.sleep(2)

# 填充标题
title_js = ARTICLE_JS_TEMPLATES["fill_article_title"].replace(
    'TITLE_PLACEHOLDER', '文章标题'
)
publisher._evaluate(title_js)

# 填充内容
html_escaped = json.dumps(html)[1:-1]
content_js = ARTICLE_JS_TEMPLATES["fill_article_content"].replace(
    'HTML_PLACEHOLDER', html_escaped
)
publisher._evaluate(content_js)
```

### 方法3: 集成到 publish_pipeline.py

在 `publish_pipeline.py` 中添加 `--article` 参数：

```python
parser.add_argument("--article", action="store_true", 
                   help="Publish as long-form article (no images required)")
```

然后根据参数选择发布模式。

## 📝 话题标签处理

**重要：** 长文的话题标签处理方式与图文不同

- **图文模式**: 需要单独选择话题标签
- **长文模式**: 直接在正文中输入 `#标签名`，小红书自动识别

**示例：**
```markdown
正文内容...

#openclaw #tailscale #远程运维
```

## 🔧 集成到 cdp_publish.py 的建议

### 添加新方法到 XiaohongshuPublisher 类：

```python
def publish_article(
    self,
    title: str,
    content: str,
    post_time: str | None = None,
):
    """发布长文"""
    from article_support import ArticlePublisher, ARTICLE_JS_TEMPLATES
    import json
    
    # 转换内容
    html = ArticlePublisher.convert_markdown_to_html(content)
    
    # 导航到长文编辑页
    self._navigate(XHS_CREATOR_URL)
    self._sleep(2)
    
    # 点击长文 tab
    self._evaluate(ARTICLE_JS_TEMPLATES["click_article_tab"])
    self._sleep(1)
    
    # 点击新的创作
    self._evaluate(ARTICLE_JS_TEMPLATES["click_new_creation"])
    self._sleep(2)
    
    # 填充标题
    title_escaped = json.dumps(title)[1:-1]
    title_js = ARTICLE_JS_TEMPLATES["fill_article_title"].replace(
        'TITLE_PLACEHOLDER', title_escaped
    )
    self._evaluate(title_js)
    self._sleep(0.5)
    
    # 填充内容
    html_escaped = json.dumps(html)[1:-1]
    content_js = ARTICLE_JS_TEMPLATES["fill_article_content"].replace(
        'HTML_PLACEHOLDER', html_escaped
    )
    self._evaluate(content_js)
    
    print("[publish_article] Content filled. Please review and publish.")
```

## ⚠️ 已知限制

1. **话题标签自动识别**: 长文的话题标签是在发布后由小红书自动识别的，不像图文那样有单独的选择界面
2. **发布按钮**: 长文编辑页面没有直接的发布按钮，需要点击"暂存离开"保存草稿，然后从草稿箱发布
3. **格式兼容性**: TipTap/ProseMirror 编辑器支持有限制，部分复杂 HTML 格式可能无法正确显示

## 📁 文件列表

```
skills/xiaohongshu/
├── article_support_design.md      # 设计方案文档
├── example_article.md             # 示例文章
└── scripts/
    ├── article_support.py         # 扩展模块
    └── publish_article_example.py # 示例脚本
```

## 🎯 下一步建议

1. **测试验证**: 运行示例脚本，验证长文发布流程
2. **集成到 pipeline**: 将长文支持集成到 `publish_pipeline.py`
3. **添加 CLI 命令**: 在 `cdp_publish.py` 中添加 `publish-article` 子命令
4. **话题标签优化**: 研究长文发布后话题标签的自动识别机制

## 💡 使用技巧

1. **Markdown 格式**: 使用 `--markdown` 参数支持富文本格式
2. **话题标签**: 在文章末尾直接写 `#标签名`
3. **代码块**: 使用 `` `代码` `` 格式
4. **列表**: 使用 `- ` 或 `1. ` 创建列表

---

**总结**: 通过创建 `article_support.py` 模块，我们实现了小红书长文发布的完整支持，包括 Markdown 转换、页面导航、内容填充等功能。可以独立使用，也可以集成到现有的 skill 中。

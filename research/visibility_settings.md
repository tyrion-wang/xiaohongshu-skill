# 小红书可见性设置研究

## 需求
在发布笔记时支持设置可见性为"仅自己可见"，用于测试笔记发布而不影响账号。

## 预期位置
在图文/视频/长文笔记的发布设置页面，通常位于：
- 页面底部"更多设置"折叠区域
- 或"高级设置"区域
- 包含选项：公开可见 / 仅自己可见 / 粉丝可见

## 实现方案

### 方案1: 在发布流程中添加可见性设置

在 `publish_article.py` 和 `publish.py` 中添加 `_set_visibility()` 方法：

```python
def _set_visibility(self, visibility: str = "public"):
    """
    设置笔记可见性
    
    Args:
        visibility: 可见性选项
            - "public": 公开可见（默认）
            - "private": 仅自己可见
            - "fans": 粉丝可见
    """
    js = """
    (function() {
        // 1. 查找并点击"更多设置"展开按钮
        var expandButtons = document.querySelectorAll('*[class*="expand"], *[class*="more"], button');
        for (var i = 0; i < expandButtons.length; i++) {
            var text = expandButtons[i].textContent || '';
            if (text.indexOf('更多设置') >= 0 || text.indexOf('高级设置') >= 0) {
                expandButtons[i].click();
                return 'expanded_settings';
            }
        }
        
        // 2. 查找可见性选项
        var visibilityOptions = document.querySelectorAll('*[class*="visibility"], *[class*="privacy"], label, div');
        for (var j = 0; j < visibilityOptions.length; j++) {
            var optionText = visibilityOptions[j].textContent || '';
            
            // 根据传入的 visibility 参数选择对应选项
            if (visibility === 'private' && optionText.indexOf('仅自己') >= 0) {
                visibilityOptions[j].click();
                return 'set_private';
            }
            if (visibility === 'public' && optionText.indexOf('公开') >= 0) {
                visibilityOptions[j].click();
                return 'set_public';
            }
        }
        
        return 'visibility_option_not_found';
    })()
    """
    result = self.publisher._evaluate(js)
    print(f"[visibility] Set to {visibility}: {result}")
    return result
```

### 方案2: 修改 publish() 函数签名

在 `publish()` 和 `publish_article()` 函数中添加 `visibility` 参数：

```python
def publish(
    self,
    title: str,
    content: str,
    images: list = None,
    topic_tags: list = None,
    visibility: str = "public",  # 新增参数
    preview: bool = False,
) -> dict:
    """
    发布图文笔记
    
    Args:
        ...
        visibility: 可见性设置 ("public"|"private"|"fans")
    """
```

### 方案3: 在 pipeline 脚本中添加参数

在 `publish_pipeline.py` 中添加命令行参数：

```python
parser.add_argument(
    "--visibility",
    choices=["public", "private", "fans"],
    default="public",
    help="设置笔记可见性 (默认: public)"
)
```

## 调用示例

```bash
# 发布仅自己可见的测试笔记
python scripts/publish_pipeline.py \
  --title-file title.txt \
  --content-file content.txt \
  --visibility private \
  --article
```

## 注意事项

1. **长文 vs 图文**：需要分别测试长文和图文笔记的可见性设置位置是否相同
2. **页面结构变化**：小红书页面经常改版，选择器需要定期维护
3. **默认行为**：如果不设置，保持默认"公开可见"
4. **测试账号**：建议使用测试账号验证可见性功能

## 下一步

1. 在浏览器中进入实际发布设置页面
2. 确认可见性选项的准确位置和HTML结构
3. 提取正确的选择器
4. 实现并测试 `_set_visibility()` 方法
5. 更新 SKILL.md 文档


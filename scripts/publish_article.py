"""
小红书长文发布功能模块

提供 publish_article() 函数用于发布长文笔记
"""

import json
import time
import random


def _jitter_ms(base_ms: int, jitter_ratio: float, minimum_ms: int = 0) -> int:
    """Return a randomized delay in milliseconds around the base value."""
    base = max(minimum_ms, int(base_ms))
    if jitter_ratio <= 0:
        return base
    delta = int(round(base * jitter_ratio))
    low = max(minimum_ms, base - delta)
    high = max(low, base + delta)
    return random.randint(low, high)


def _jitter_seconds(base_seconds: float, jitter_ratio: float, minimum_seconds: float = 0.05) -> float:
    """Return a randomized delay in seconds around the base value."""
    base = max(minimum_seconds, float(base_seconds))
    if jitter_ratio <= 0:
        return base
    delta = base * jitter_ratio
    low = max(minimum_seconds, base - delta)
    high = max(low, base + delta)
    return random.uniform(low, high)


class ArticlePublisher:
    """小红书长文发布器"""
    
    def __init__(self, publisher, timing_jitter: float = 0.25):
        """
        Args:
            publisher: XiaohongshuPublisher 实例
            timing_jitter: 操作延迟的随机抖动比例
        """
        self.publisher = publisher
        self.timing_jitter = timing_jitter
    
    def publish_article(
        self,
        title: str,
        content: str,
        description: str = "",
        topic_tags: list[str] = None,
        visibility: str = "public",
        preview: bool = False,
    ) -> dict:
        """
        发布长文笔记
        
        完整流程：
        1. 导航到发布页面
        2. 点击「写长文」标签
        3. 点击「新的创作」
        4. 填写标题（编辑器页面）
        5. 填写正文（编辑器页面）
        6. 点击「一键排版」
        7. 选择模板（默认第一个）
        8. 点击「下一步」
        9. 填写描述 + 话题标签
        10. 点击「发布」
        
        Args:
            title: 文章标题
            content: 文章内容（HTML格式，段落用<p>包裹）
            description: 笔记描述（短描述，显示在笔记卡片上）
            topic_tags: 话题标签列表，如 ['openclaw', '测试']
            visibility: 可见性设置 ("public"=公开, "private"=仅自己可见)
            preview: 是否为预览模式（不点击发布）
            
        Returns:
            包含发布结果的字典
        """
        if topic_tags is None:
            topic_tags = []
            
        print("[article] Step 1: Navigating to publish page...")
        self.publisher._navigate("https://creator.xiaohongshu.com/publish/publish")
        self._sleep(2)
        
        print("[article] Step 2: Clicking '写长文' tab...")
        self._click_article_tab()
        self._sleep(1)
        
        print("[article] Step 3: Clicking '新的创作'...")
        self._click_new_creation()
        self._sleep(2)
        
        print("[article] Step 4: Filling title in editor...")
        self._fill_title_in_editor(title)
        self._sleep(0.5)
        
        print("[article] Step 5: Filling content in editor...")
        self._fill_content_in_editor(content)
        self._sleep(1)
        
        print("[article] Step 6: Clicking '一键排版'...")
        self._click_layout()
        self._sleep(5)  # 等待跳转到模板选择页面
        
        # 检查当前URL和按钮
        current_url = self.publisher._evaluate("window.location.href")
        print(f"[article] Current URL after layout: {current_url}")
        
        buttons = self.publisher._evaluate("""
            (function() {
                return Array.from(document.querySelectorAll('button'))
                    .map(b => b.textContent?.trim())
                    .filter(t => t);
            })()
        """)
        print(f"[article] Available buttons: {buttons}")
        
        print("[article] Step 7: Clicking '下一步'...")
        self._click_next()
        self._sleep(5)  # 增加等待时间，确保页面跳转到发布设置页
        
        # 验证是否跳转成功（检查是否有发布设置页面的元素）
        max_wait = 10
        for i in range(max_wait):
            has_desc = self.publisher._evaluate("""
                (function() {
                    return document.querySelector('div[contenteditable="true"]') !== null ||
                           document.querySelector('textarea') !== null;
                })()
            """)
            if has_desc:
                print("[article] Page appears to have navigated to publish settings")
                break
            print(f"[article] Waiting for page to load... {i+1}/{max_wait}")
            self._sleep(1)
        else:
            print("[article] Warning: Page may not have navigated correctly")
            # 继续尝试，不退出
        
        print("[article] Step 8: Filling description and topic tags...")
        # 先填写描述（不包含话题标签）
        if description:
            self._fill_description(description)
            self._sleep(1)
        
        # 使用 skill 方法选择话题标签
        if topic_tags:
            self._select_topics_in_description(topic_tags)
            self._sleep(1)
        
        # Step 9: 设置可见性
        if visibility != "public":
            print(f"[article] Step 9: Setting visibility to {visibility}...")
            self._set_visibility(visibility)
            self._sleep(1)
        
        result = {"status": "READY_TO_PUBLISH"}
        
        if not preview:
            print("[article] Step 10: Clicking publish button...")
            for attempt in range(3):
                note_link = self._click_publish()
                if note_link:
                    result["status"] = "PUBLISHED"
                    result["note_link"] = note_link
                    print(f"[article] Published at: {note_link}")
                    break
                else:
                    print(f"[article] Attempt {attempt + 1}: Publish button not found, retrying...")
                    self._sleep(2)
            else:
                print("[article] Warning: Publish button not found after all attempts.")
                result["status"] = "READY_TO_PUBLISH"
        else:
            print("[article] Preview mode: skipping publish.")
        
        return result
    
    def _sleep(self, seconds: float):
        """带抖动的休眠"""
        delay = _jitter_seconds(seconds, self.timing_jitter)
        time.sleep(delay)
    
    def _click_article_tab(self):
        """点击'写长文'标签"""
        js = """
        (function() {
            var tabs = document.querySelectorAll('*');
            for (var i = 0; i < tabs.length; i++) {
                if (tabs[i].textContent && tabs[i].textContent.trim() === '写长文') {
                    tabs[i].click();
                    return 'clicked_article_tab';
                }
            }
            return 'tab_not_found';
        })()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Tab click result: {result}")
        return result
    
    def _click_new_creation(self):
        """点击'新的创作'按钮"""
        js = """
        (function() {
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || '';
                if (text.indexOf('新的创作') >= 0) {
                    buttons[i].click();
                    return 'clicked_new_creation';
                }
            }
            return 'button_not_found';
        })()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Creation click result: {result}")
        return result
    
    def _fill_title_in_editor(self, title: str):
        """在编辑器页面填写标题"""
        title_json = json.dumps(title)
        js = f"""
        (function() {{
            var title = {title_json};
            var textarea = document.querySelector('textarea[placeholder="输入标题"], textarea.d-text');
            if (textarea) {{
                textarea.focus();
                // 使用 nativeSetter 正确设置值，触发 React/Vue 的响应式更新
                var nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value'
                ).set;
                nativeSetter.call(textarea, title);
                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'title_filled';
            }}
            return 'title_input_not_found';
        }})()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Title fill result: {result}")
        return result
    
    def _fill_content_in_editor(self, content_html: str):
        """在编辑器页面填写内容（HTML格式）
        
        使用 ProseMirror 的 setContent 命令来正确设置 HTML 内容
        """
        # 转义 HTML 中的特殊字符
        content_escaped = content_html.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        
        js = f"""
        (async function() {{
            var editor = document.querySelector('.ProseMirror[contenteditable="true"], .tiptap.ProseMirror');
            if (!editor) {{
                return 'editor_not_found';
            }}
            
            editor.focus();
            
            // 方法1: 尝试使用 execCommand 清空并插入 HTML
            try {{
                // 先选中所有内容并删除
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                
                // 使用 insertHTML 命令插入内容
                var html = "{content_escaped}";
                document.execCommand('insertHTML', false, html);
                
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return 'content_filled_via_execCommand';
            }} catch (e) {{
                console.log('execCommand failed:', e);
            }}
            
            // 方法2: 直接设置 innerHTML（作为备选）
            try {{
                editor.innerHTML = "{content_escaped}";
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return 'content_filled_via_innerHTML';
            }} catch (e) {{
                return 'content_fill_failed: ' + e.message;
            }}
        }})()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Content fill result: {result}")
        return result
    
    def _click_layout(self):
        """点击'一键排版'"""
        js = """
        (function() {
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || '';
                if (text.indexOf('一键排版') >= 0) {
                    buttons[i].click();
                    return 'clicked_layout';
                }
            }
            return 'button_not_found';
        })()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Layout click result: {result}")
        return result
    
    def _select_first_template(self):
        """选择第一个模板（简约基础）"""
        js = """
        (function() {
            // 尝试找到第一个模板选项
            var templates = document.querySelectorAll('[class*="template"], [class*="cover"]');
            if (templates.length > 0) {
                templates[0].click();
                return 'selected_first_template';
            }
            
            // 备选：尝试点击包含"简约基础"的元素
            var elements = document.querySelectorAll('*');
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].textContent && elements[i].textContent.indexOf('简约基础') >= 0) {
                    elements[i].click();
                    return 'selected_simple_template';
                }
            }
            
            return 'no_template_found';
        })()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Template selection result: {result}")
        return result
    
    def _click_next(self):
        """点击'下一步'按钮"""
        js = """
        (function() {
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || '';
                if (text.indexOf('下一步') >= 0) {
                    // 确保按钮不是 disabled
                    if (!buttons[i].disabled) {
                        buttons[i].click();
                        return 'clicked_next';
                    }
                }
            }
            return 'button_not_found_or_disabled';
        })()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Next button click result: {result}")
        return result
    
    def _fill_description(self, description: str):
        """在发布设置页面填写描述"""
        desc_json = json.dumps(description)
        js = f"""
        (function() {{
            var desc = {desc_json};
            // 查找描述输入框（通常是 placeholder 包含"描述"或"正文描述"的输入框）
            var inputs = document.querySelectorAll('div[contenteditable="true"], textarea');
            var descInput = null;
            
            for (var i = 0; i < inputs.length; i++) {{
                var placeholder = inputs[i].getAttribute('placeholder') || '';
                if (placeholder.indexOf('描述') >= 0 || placeholder.indexOf('真诚') >= 0) {{
                    descInput = inputs[i];
                    break;
                }}
            }}
            
            // 如果没找到，尝试找第一个 contenteditable 区域
            if (!descInput) {{
                descInput = document.querySelector('div[contenteditable="true"]');
            }}
            
            if (descInput) {{
                descInput.focus();
                
                // 如果是 textarea，使用 nativeSetter
                if (descInput.tagName === 'TEXTAREA') {{
                    var nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeSetter.call(descInput, desc);
                }} else {{
                    // 对于 contenteditable，直接设置 textContent
                    descInput.textContent = desc;
                }}
                
                descInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                descInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'description_filled';
            }}
            
            return 'description_input_not_found';
        }})()
        """
        result = self.publisher._evaluate(js)
        print(f"[article] Description fill result: {result}")
        return result
    
    def _select_topics_in_description(self, tags: list[str]):
        """
        在描述框中选择话题标签
        
        模拟真实输入流程：输入 # → 等待下拉建议 → Enter 确认
        """
        if not tags:
            return
        
        print(f"[article] Selecting {len(tags)} topic tag(s) in description...")
        failed_tags = []
        
        for index, tag in enumerate(tags):
            normalized_tag = tag.lstrip("#").strip()
            if not normalized_tag:
                continue
            
            hash_pause_ms = _jitter_ms(180, self.timing_jitter, minimum_ms=90)
            char_delay_min_ms = _jitter_ms(45, self.timing_jitter, minimum_ms=25)
            char_delay_max_ms = _jitter_ms(95, self.timing_jitter, minimum_ms=char_delay_min_ms)
            suggest_wait_ms = _jitter_ms(3000, self.timing_jitter, minimum_ms=1600)
            after_enter_ms = _jitter_ms(260, self.timing_jitter, minimum_ms=120)
            
            escaped_tag = json.dumps(normalized_tag)
            space_literal = json.dumps(" ")
            
            js = f"""
            (async function() {{
                // 查找描述输入框
                var inputs = document.querySelectorAll('div[contenteditable="true"], textarea');
                var editor = null;
                
                for (var i = 0; i < inputs.length; i++) {{
                    var placeholder = inputs[i].getAttribute('placeholder') || '';
                    if (placeholder.indexOf('描述') >= 0 || placeholder.indexOf('真诚') >= 0) {{
                        editor = inputs[i];
                        break;
                    }}
                }}
                
                if (!editor) {{
                    editor = document.querySelector('div[contenteditable="true"]');
                }}
                
                if (!editor) {{
                    return {{ ok: false, reason: 'editor_not_found' }};
                }}
                
                function sleep(ms) {{
                    return new Promise(function(resolve) {{ setTimeout(resolve, ms); }});
                }}
                
                function moveCaretToEditorEnd(el) {{
                    el.focus();
                    var selection = window.getSelection();
                    if (!selection) return;
                    var range = document.createRange();
                    range.selectNodeContents(el);
                    range.collapse(false);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }}
                
                function insertTextAtCaret(text) {{
                    var inserted = false;
                    try {{
                        inserted = document.execCommand('insertText', false, text);
                    }} catch (e) {{}}
                    
                    if (!inserted) {{
                        var selection = window.getSelection();
                        if (selection && selection.rangeCount > 0) {{
                            var range = selection.getRangeAt(0);
                            var node = document.createTextNode(text);
                            range.insertNode(node);
                            range.setStartAfter(node);
                            range.collapse(true);
                            selection.removeAllRanges();
                            selection.addRange(range);
                        }} else {{
                            editor.appendChild(document.createTextNode(text));
                        }}
                    }}
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                function pressEnter(el) {{
                    var evt = {{
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true,
                    }};
                    el.dispatchEvent(new KeyboardEvent('keydown', evt));
                    el.dispatchEvent(new KeyboardEvent('keypress', evt));
                    el.dispatchEvent(new KeyboardEvent('keyup', evt));
                }}
                
                moveCaretToEditorEnd(editor);
                
                // 输入 #
                insertTextAtCaret('#');
                await sleep({hash_pause_ms});
                
                // 逐个字符输入标签名
                var tagText = {escaped_tag};
                var charDelayMin = {char_delay_min_ms};
                var charDelayMax = {char_delay_max_ms};
                for (var i = 0; i < tagText.length; i++) {{
                    insertTextAtCaret(tagText[i]);
                    var charDelay = Math.floor(Math.random() * (charDelayMax - charDelayMin + 1)) + charDelayMin;
                    await sleep(charDelay);
                }}
                
                // 等待下拉建议出现
                await sleep({suggest_wait_ms});
                
                // 按 Enter 确认
                pressEnter(editor);
                await sleep({after_enter_ms});
                
                // 输入空格分隔
                insertTextAtCaret({space_literal});
                
                return {{ ok: true, selected: true }};
            }})()
            """
            
            result = self.publisher._evaluate(js)
            
            if not (isinstance(result, dict) and result.get("ok")):
                failed_tags.append(tag)
                reason = result.get("reason") if isinstance(result, dict) else "unknown"
                print(f"[article] Warning: Failed to select topic {normalized_tag} ({reason}).")
            else:
                print(f"[article] Topic selected: #{normalized_tag}")
            
            if index < len(tags) - 1:
                time.sleep(_jitter_seconds(0.45, self.timing_jitter, minimum_seconds=0.2))
        
        if failed_tags:
            print(
                "[article] Warning: Some topic tags were not selected: "
                f"{', '.join(failed_tags)}"
            )
    
    def _click_publish(self) -> str | None:
        """点击发布按钮"""
        
        # 方法1-3: 使用多种策略查找发布按钮
        js = """
        (function() {
            var buttons = document.querySelectorAll('button');
            
            // 策略1: 查找文本为"发布"且不是disabled的按钮
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent || '';
                if (text.trim() === '发布' && !buttons[i].disabled) {
                    buttons[i].click();
                    return 'clicked_publish_v1';
                }
            }
            
            // 策略2: 查找包含"发布"文本的按钮（更宽松）
            for (var j = 0; j < buttons.length; j++) {
                var text2 = buttons[j].textContent || '';
                if (text2.indexOf('发布') >= 0 && !buttons[j].disabled) {
                    buttons[j].click();
                    return 'clicked_publish_v2';
                }
            }
            
            // 策略3: 查找红色/主按钮样式的按钮
            for (var k = 0; k < buttons.length; k++) {
                var style = window.getComputedStyle(buttons[k]);
                var bgColor = style.backgroundColor || '';
                var text3 = buttons[k].textContent || '';
                
                if (text3.trim() === '发布') {
                    // 红色背景或primary样式
                    if (bgColor.indexOf('255') >= 0 || 
                        bgColor.indexOf('red') >= 0 ||
                        bgColor.indexOf('245') >= 0) {
                        buttons[k].click();
                        return 'clicked_publish_v3';
                    }
                }
            }
            
            // 策略4: 查找带有特定class的发布按钮
            var publishButtons = document.querySelectorAll('button[class*="publish"], button[class*="submit"], button[class*="primary"]');
            for (var m = 0; m < publishButtons.length; m++) {
                var text4 = publishButtons[m].textContent || '';
                if (text4.indexOf('发布') >= 0 && !publishButtons[m].disabled) {
                    publishButtons[m].click();
                    return 'clicked_publish_v4';
                }
            }
            
            // 策略5: 最后一个button（通常发布按钮在右下角）
            if (buttons.length > 0) {
                var lastButton = buttons[buttons.length - 1];
                var lastText = lastButton.textContent || '';
                if (lastText.indexOf('发布') >= 0 || lastText.indexOf('提交') >= 0) {
                    lastButton.click();
                    return 'clicked_publish_v5_last';
                }
            }
            
            return 'button_not_found';
        })()
        """
        
        max_attempts = 3
        for attempt in range(max_attempts):
            result = self.publisher._evaluate(js)
            print(f"[article] Publish click attempt {attempt + 1}: {result}")
            
            if result != 'button_not_found':
                break
            
            if attempt < max_attempts - 1:
                print(f"[article] Attempt {attempt + 1}: Publish button not found, retrying...")
                time.sleep(2)
        
        if result == 'button_not_found':
            print("[article] Warning: Publish button not found after all attempts.")
            return None
        
        # 等待发布成功提示
        time.sleep(5)
        
        # 检查是否发布成功（多种方式）
        js_check = """
        (function() {
            var pageText = document.body.innerText || '';
            var url = window.location.href;
            
            // 检查成功提示或跳转
            if (pageText.indexOf('发布成功') >= 0 || 
                pageText.indexOf('成功') >= 0 ||
                url.indexOf('success') >= 0 ||
                url.indexOf('published') >= 0) {
                return 'success';
            }
            
            // 检查是否在笔记管理页面（发布后会跳转）
            if (url.indexOf('note-manager') >= 0 ||
                url.indexOf('notes') >= 0) {
                return 'success_redirect';
            }
            
            return 'unknown';
        })()
        """
        status = self.publisher._evaluate(js_check)
        
        if status in ('success', 'success_redirect'):
            return "https://creator.xiaohongshu.com/publish/success"
        
        return None
    
    def _set_visibility(self, visibility: str = "public"):
        """
        设置笔记可见性
        
        在发布设置页面点击可见性选项。
        
        Args:
            visibility: 可见性选项
                - "public": 公开可见（默认）
                - "private": 仅自己可见
        """
        if visibility == "public":
            return  # 默认就是公开，无需设置
        
        print(f"[visibility] Setting visibility to: {visibility}")
        
        target_text = "仅自己可见" if visibility == "private" else "公开可见"
        
        js_select = f"""
        (function() {{
            var targetText = "{target_text}";
            
            // 方法1: 直接查找 custom-option 或 d-grid-item 中的选项
            var options = document.querySelectorAll('.custom-option, .d-grid-item');
            for (var i = 0; i < options.length; i++) {{
                var text = options[i].textContent?.trim();
                if (text === targetText) {{
                    options[i].click();
                    return 'clicked_option_' + targetText;
                }}
            }}
            
            // 方法2: 查找所有包含目标文本的元素（包括hidden元素）
            var allElements = document.querySelectorAll('*');
            for (var j = 0; j < allElements.length; j++) {{
                if (allElements[j].textContent?.trim() === targetText) {{
                    allElements[j].click();
                    return 'clicked_element_' + targetText;
                }}
            }}
            
            // 方法3: 尝试点击可见性下拉框然后选择
            var selectWrapper = document.querySelector('.permission-card-select, .d-select-wrapper');
            if (selectWrapper) {{
                selectWrapper.click();
                // 等待下拉展开后再次尝试查找选项
                setTimeout(function() {{
                    var dropdownOptions = document.querySelectorAll('.custom-option, .d-grid-item, .d-select-dropdown-item');
                    for (var k = 0; k < dropdownOptions.length; k++) {{
                        if (dropdownOptions[k].textContent?.trim() === targetText) {{
                            dropdownOptions[k].click();
                            return 'clicked_dropdown_' + targetText;
                        }}
                    }}
                }}, 500);
                return 'clicked_select_wrapper';
            }}
            
            return 'option_not_found';
        }})()
        """
        result = self.publisher._evaluate(js_select)
        print(f"[visibility] Result: {result}")
        
        if "option_not_found" in result:
            print("[visibility] Warning: Could not find visibility option, will try alternative method")
            # 备选：尝试直接通过JavaScript设置值
            js_alternative = f"""
            (function() {{
                // 查找所有可能的radio或checkbox
                var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                for (var i = 0; i < inputs.length; i++) {{
                    var parent = inputs[i].closest('.permission-card, .d-select, .custom-option');
                    if (parent && parent.textContent?.indexOf('{target_text}') >= 0) {{
                        inputs[i].click();
                        return 'clicked_input_for_' + '{target_text}';
                    }}
                }}
                return 'alternative_failed';
            }})()
            """
            alt_result = self.publisher._evaluate(js_alternative)
            print(f"[visibility] Alternative method result: {alt_result}")
        else:
            self._sleep(0.5)
        
        return result

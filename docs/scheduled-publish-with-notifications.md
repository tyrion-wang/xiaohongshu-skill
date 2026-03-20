# 小红书定时发布 - 实时Discord通知方案

**验证时间：2026-03-21**  
**状态：✅ 已验证通过**

---

## 方案概述

**目标：** 实现定时触发小红书发布，并在过程中实时发送Discord进展通知

**架构：**
```
Cron触发 → Agent创建Subagent
                ↓
        Subagent内部执行：
        1. 立即发送Discord "启动"
        2. 等待到指定时间
        3. 执行小红书发布（仅自己可见）
        4. 立即发送Discord "成功"
        5. 验证并发送Discord "完成"
```

---

## 关键配置

### 1. Cron任务配置（jobs.json）

```json
{
  "id": "xhs-scheduled-{时间戳}",
  "name": "小红书定时发布-{时间}",
  "description": "定时发布+实时Discord通知",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "0 分 时 日 月 *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "创建Subagent执行实时发布（详见执行脚本）"
  }
}
```

**关键要点：**
- 只保留 `payload`，不添加 `sessionTarget`/`delivery`/`wakeMode`
- 使用 `agentTurn` 类型
- message中包含完整的执行指令

### 2. Subagent执行脚本模板

```bash
#!/bin/bash
# 小红书定时发布 - 实时通知脚本

CHANNEL_ID="1480567113608593419"  # Discord频道ID
TEST_NAME="定时发布测试"

# 步骤1: 发送启动通知（立即）
# 使用 message 工具发送Discord
echo "[$TEST_NAME] 步骤1: 发送启动通知"

# 步骤2: 等待到指定时间
echo "[$TEST_NAME] 步骤2: 等待到 $TARGET_TIME..."
while [ "$(date '+%H:%M')" != "$TARGET_TIME" ]; do
    sleep 5
done

# 步骤3: 执行小红书发布
echo "[$TEST_NAME] 步骤3: 执行发布..."
cd /Users/tyrion/.openclaw/workspace/skills/xiaohongshu
python3 scripts/publish_pipeline.py \
  --port 18800 \
  --article \
  --visibility private \
  --title-file /path/to/title.txt \
  --content-file /path/to/content.txt

# 步骤4: 发送成功通知
echo "[$TEST_NAME] 步骤4: 发送成功通知"

# 步骤5: 验证并发送完成通知
echo "[$TEST_NAME] 步骤5: 验证完成"
```

### 3. 实时Discord通知要点

**关键原则：每步完成后立即发送，不要等全部完成**

```
错误做法（一次性汇报）：
  步骤1 → 步骤2 → 步骤3 → 完成后发3条消息

正确做法（实时通知）：
  步骤1完成 → 立即发送Discord
  步骤2完成 → 立即发送Discord
  步骤3完成 → 立即发送Discord
```

**Discord消息格式：**
```
🚀 [时间] 启动小红书发布
⏰ 状态：开始执行
🔒 目标：仅自己可见

✅ [时间] 小红书发布成功！
🔒 可见性：仅自己可见
🔗 状态：PUBLISHED

✅ [时间] 验证完成！
📊 状态：发布成功+通知到达
```

---

## 验证记录

### 测试1：5秒间隔通知（2026-03-21 01:27）
- ✅ 3条消息实时发送
- ✅ 间隔5秒
- ✅ 消息ID: 1484604494091387037, 1484604545626673202, 1484604605030727832

### 测试2：10秒间隔通知（2026-03-21 01:55）
- ✅ 3条消息实时发送
- ✅ 间隔10秒
- ✅ 总耗时20秒
- ✅ 消息ID: 1484611281406136461, 1484611358774263921, 1484611437086380085

### 测试3：完整发布流程（2026-03-21 02:01）
- ✅ 实时通知（3条）
- ✅ 小红书发布成功（仅自己可见）
- ✅ 总耗时1分17秒
- ✅ 状态：PUBLISHED

---

## 常见问题

### Q1: 为什么Cron状态显示error但任务成功了？
**原因：** Agent使用`sessions_yield`等待子代理完成，Cron期望即时返回。  
**解决：** 忽略Cron状态，查看Subagent实际执行结果。

### Q2: Discord消息没有实时发送？
**原因：** 所有步骤在Agent内部完成，外部无法感知进度。  
**解决：** 使用Subagent，每步完成后立即调用发送工具。

### Q3: 如何确保通知发送到正确的Discord频道？
**方法：**
- 使用 `channel: "last"`（当前频道）
- 或指定channel ID: `1480567113608593419`
- 在Subagent任务中明确指定target

---

## 使用示例

### 创建定时任务（立即执行）

```python
import json
from datetime import datetime, timedelta

# 计算执行时间
test_time = datetime.now() + timedelta(minutes=10)
hour = test_time.strftime('%H')
minute = test_time.strftime('%M')

task = {
    "id": f"xhs-scheduled-{hour}{minute}",
    "name": f"定时发布-{hour}:{minute}",
    "enabled": True,
    "schedule": {
        "kind": "cron",
        "expr": f"0 {minute} {hour} * * *",
        "tz": "Asia/Shanghai"
    },
    "payload": {
        "kind": "agentTurn",
        "message": "创建Subagent执行实时发布..."
    }
}
```

### 手动立即测试

```bash
sessions_spawn --mode run --runtime subagent --task '
  # 步骤1: 发送启动通知
  echo "🚀 启动发布"
  
  # 步骤2: 执行发布
  cd /Users/tyrion/.openclaw/workspace/skills/xiaohongshu
  python3 scripts/publish_pipeline.py ...
  
  # 步骤3: 发送成功通知
  echo "✅ 发布成功"
'
```

---

## 关键成功因素

1. **Subagent内部执行** - 有完整权限发送Discord
2. **每步立即通知** - 不要等全部完成
3. **简化Cron配置** - 只保留payload，不添加复杂配置
4. **明确指定target** - Discord频道ID要写清楚
5. **验证后固化** - 先小规模测试，确认成功再扩展

---

**记录时间：2026-03-21**  
**验证状态：✅ 已通过3轮测试**

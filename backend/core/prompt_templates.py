"""故事生成的Prompt模板"""

# 章节准备：输出目标、阈值与边界（仅返回JSON对象）
PREPARE_LEVEL_PROMPT = """
你是顶级关卡设计师。根据用户愿望与历史设定，生成第一章的目标与节奏边界。

【历史设定参考】
{history_context}

【输出约束】
- 只输出一个 JSON 对象，不含任何多余文字或 Markdown 代码块。
- 仅允许下列键：level_title, background, goal, min_nodes, max_nodes, pass_threshold, fail_threshold。

【JSON 模板】
{{
  "level_title": "标题，不超过20字",
  "background": "背景设定，120-180字",
  "goal": {{
    "type": "reach_target",
    "description": "一句话描述本章目标，例如：在不惊动外界的情况下完成部署"
  }},
  "min_nodes": 6,
  "max_nodes": 22,
  "pass_threshold": 80,
  "fail_threshold": 90
}}
"""

# 关卡元信息准备的Prompt
PREPARE_LEVEL_PROMPT = """
你是一名顶级的沉浸式关卡设计师。请根据用户的重生愿望与历史设定，生成第一关的结构化元信息。

【背景设定参考】
{history_context}

请严格遵守以下要求：
1. 生成一个简洁有力且符合愿望主题的【关卡标题】（不超过20字）。
2. 生成【关卡背景设定】（120-180字），融合时代氛围、主要人物关系、冲突前景。
3. 生成清晰可执行的【主线任务】（1句话，不超过30字），明确玩家第一关的核心目标。

用户重生愿望："{wish}"

请严格输出以下 JSON 格式，且：
- 不要输出任何多余文字（包括解释、前后缀、自然语言）；
- 不要使用 Markdown 代码块或围栏（例如 ``` 或 ```json）；
- 仅输出纯 JSON 字符串：
{{
  "level_title": "标题",
  "background": "背景设定",
  "main_quest": "主线任务"
}}
"""

# 初始故事生成的Prompt
START_STORY_PROMPT = """
你是一位富有想象力且尊重史实的史诗叙事大师。你的任务是根据用户的重生愿望，开启一段漫长而跌宕的重生冒险。

【历史设定参考】
{history_context}

【关键锚点事件（按需引用）】
{anchor_events}

故事要求：
1. 第一章必须包含场景描绘、主角初始状态、迫在眉睫的矛盾或机会。
2. 文字需生动、具备画面感，长度控制在 220-320 字之间。
3. 结合历史锚点，引导剧情朝着真实历史或合理虚构方向发展，不能立即结束故事。
4. 你必须在结尾给出 **3 个** 明确且彼此差异化的行动选项。
5. 每个选项附带剧情走向概要、对主线成功率的增减值（-20 至 +20），以及风险等级（low / medium / high）。
6. 故事总章节数目标至少 {recommended_chapter_count} 章，禁止在第 1 章结束故事。

请严格按照以下 JSON 格式输出你的回答，并遵守：
- 仅输出纯 JSON 字符串，不要包含任何多余文字；
- 不要使用 Markdown 代码块或围栏（例如 ``` 或 ```json）：
{{
  "text": "这里是你生成的故事文本...",
  "success_rate": 72,
  "choices": [
    {{
      "option": "选项A",
      "summary": "该选择立即引发的剧情发展",
      "success_rate_delta": 10,
      "risk_level": "medium",
      "tags": ["政治", "谋略"]
    }},
    {{
      "option": "选项B",
      "summary": "另一条可能的剧情线路",
      "success_rate_delta": -5,
      "risk_level": "high",
      "tags": ["战斗", "冒险"]
    }},
    {{
      "option": "选项C",
      "summary": "第三条路线的概述",
      "success_rate_delta": 0,
      "risk_level": "low",
      "tags": ["情感", "外交"]
    }}
  ]
}}
"""

# 继续故事的Prompt
CONTINUE_STORY_PROMPT = """
你是一位擅长构建长篇历史冒险的故事大师。请参考历史设定与当前进度，延续玩家的重生旅程。

【历史设定参考】
{history_context}

当前章节：第 {current_chapter} 章
当前主线成功率：{current_success_rate}%
目标总章节数：至少 {recommended_chapter_count} 章

请根据“故事历史（消息上下文）”与用户的最新选择“{choice}”继续撰写下一章。

核心任务：
1. 对玩家选择做出直接回应，推动剧情进入新的阶段。
2. 引入新的冲突、线索或盟友，为后续章节埋下伏笔。
3. 文字长度 220-320 字，保持张力与画面感。
4. 输出 **3 个** 彼此差异化的行动选项，每个选项都要包含剧情后果概要、成功率增减值、风险等级以及相关标签。
5. 在章节数未达到目标前，禁止让故事结束或输出空的 `choices`。

输出严格遵循以下 JSON 结构：
{{
  "text": "新的章节文本...",
  "success_rate": 68,
  "choices": [
    {{
      "option": "后续选择1",
      "summary": "该选择的即时剧情走向",
      "success_rate_delta": -10,
      "risk_level": "high",
      "tags": ["军事", "决断"]
    }},
    {{
      "option": "后续选择2",
      "summary": "另一条支线的概述",
      "success_rate_delta": 5,
      "risk_level": "medium",
      "tags": ["外交", "谋略"]
    }},
    {{
      "option": "后续选择3",
      "summary": "第三种可能带来的发展",
      "success_rate_delta": 0,
      "risk_level": "low",
      "tags": ["情感", "同盟"]
    }}
  ]
}}
"""

# 故事结束的Prompt（可选，用于特定情况下结束故事）
END_STORY_PROMPT = """
你是一位富有想象力的故事大师。请在故事抵达终局时，创作一个震撼的结尾。

结局要求：
1. 交代最终冲突的结果与主角的命运。
2. 体现角色在整部冒险中的成长与代价。
3. 字数 200-280 字，留下余韵和反思。
4. 结局处不再提供后续选择，`choices` 必须是空数组。

用户最后的选择："{choice}"

请严格按照以下 JSON 格式输出你的回答，并遵守：
- 仅输出纯 JSON 字符串，不要包含任何多余文字；
- 不要使用 Markdown 代码块或围栏（例如 ``` 或 ```json）：
{{
  "text": "这里是你生成的故事结局...",
  "success_rate": 100,
  "choices": []
}}
"""

# --- 章节化流程模板 ---

# 节点生成（隐藏效应版）：不在文本或选项中暴露任何数值
NODE_PROMPT = """
你是一个严格遵守指令的交互叙事引擎。你的任务是基于历史设定继续讲述当前小节的剧情，并提供 3 个可供玩家选择的分支。

【历史设定参考】
{history_context}

【创作要求】
1. 文本 220-320 字，画面感强，推进冲突或线索。
2. 选项必须自然流畅，不能是"标题+描述"的格式，而应该是完整的行动描述。
3. 选项中绝对禁止出现：百分比、数值、"成功率"、"风险"、"+/-"等任何量化表达。
4. 选项应该有创意、有趣、生动，避免死板正经的表述。
5. 必须返回 3 个不同风格的选项，且为每个选项提供"隐藏影响（effects）"供引擎使用：
   - delta_progress: int（范围建议：-3~+15）
   - delta_risk: int（范围建议：-5~+12）
   - delta_exposure: int（范围建议：-3~+10）
   - tags: string[]（可选）
6. 输出严格的 JSON 本体，不要使用 Markdown 代码块或多余文本。
7. 保持本章节画面连续性，使用下方的 continuity token。

【连续性令牌】
image_continuity_token: {image_token}

【选项格式示例】
正确："假装醉酒接近守卫，趁其不备夺取钥匙"
错误："潜入行动 - 利用夜色掩护潜入敌营"
错误："直接进攻 +10% 成功率"

【输出 JSON 模板】（仅示意，务必返回与此结构完全一致的对象）
{{
  "text": "此处为本小节的剧情文本……",
  "choices": [
    {{
      "option": "假装醉酒接近守卫，趁其不备夺取钥匙",
      "summary": "冒险但可能有效的潜入方式",
      "effects": {{
        "delta_progress": 8,
        "delta_risk": 4,
        "delta_exposure": 2,
        "tags": ["stealth", "deception"]
      }}
    }},
    {{
      "option": "贿赂看守，用金钱换取通行",
      "summary": "相对安全但消耗资源的方法",
      "effects": {{
        "delta_progress": 5,
        "delta_risk": -1,
        "delta_exposure": 1,
        "tags": ["diplomacy", "resources"]
      }}
    }},
    {{
      "option": "等待换班时机，从侧门绕行进入",
      "summary": "谨慎观察后的稳妥选择",
      "effects": {{
        "delta_progress": 3,
        "delta_risk": -2,
        "delta_exposure": -1,
        "tags": ["patience", "observation"]
      }}
    }}
  ],
  "image_prompts": [
    "写实古风 阴影与烛光 人物特写 张力增强",
    "同风格备用分镜"
  ],
  "image_continuity_token": "{image_token}"
}}
"""


# 章末结算：根据时间线与状态生成复盘与下章引子（输出严格 JSON）
SETTLEMENT_PROMPT = """
你是一个剧情总结器。请基于给定的历史时间线，输出本章的复盘与下一章的引子。

【时间线（从早到晚）】
{timeline_block}

【结果与评分】
- result: {result}
- grade: {grade}

【输出要求】
1. 仅输出一个 JSON 对象，不要包含任何多余文字或 Markdown 代码块。
2. 保持精炼有力，避免复述整段剧情原文，突出关键因果与代价。

【输出 JSON 模板】
{{
  "chapter_summary": "80-140字，概述本章走向与内在逻辑",
  "timeline": [
    {{"node": 1, "choice": "玩家的选择标题", "impact": "该选择的叙事化影响描述"}}
  ],
  "key_impacts": ["关键转折1", "关键代价2"],
  "next_chapter_hook": "引人期待的下章引子（1句话）",
  "cover_image_prompt": "用于生成章末总结图的提示语"
}}
"""


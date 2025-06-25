# 🐉 AstrBot 成语接龙插件

> 一个支持AI智能对战的成语接龙插件，让传统文字游戏更有趣！

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.5+-green.svg)](https://github.com/Soulter/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://www.python.org/)

## ✨ 功能特色

• 🤖 **AI智能对战** - 与AI进行成语接龙对战，提高游戏趣味性
• 🎯 **LLM智能验证** - 使用大语言模型验证成语有效性
• 🔗 **自动接龙检查** - 智能判断接龙是否正确
• 📊 **积分系统** - 记录每个用户的接龙成功次数
• 🏆 **排行榜** - 实时显示积分排名
• 💾 **数据持久化** - 积分和游戏历史自动保存
• 🎮 **多会话支持** - 不同群聊/私聊可独立进行游戏
• 📝 **游戏历史** - 记录接龙过程和统计数据
• 🔄 **智能降级** - LLM不可用时回退到基础验证
• 🎨 **用户友好** - 清晰的游戏提示和错误处理

## 🚀 快速开始

### 安装方式

#### 方法1: 通过AstrBot管理面板
1. 登录AstrBot管理面板
2. 进入"插件管理"页面
3. 点击"安装插件"
4. 输入仓库地址：`https://github.com/auberginewly/astrbot_plugin_chengyu.git`
5. 点击安装

#### 方法2: 手动安装
```bash
cd /path/to/astrbot/data/plugins
git clone https://github.com/auberginewly/astrbot_plugin_chengyu.git
```

### 基本使用

#### 1. 开始游戏
```
/chengyu_start
```
或指定开始成语：
```
/chengyu_start 龙飞凤舞
```

#### 2. 进行接龙
直接在聊天中输入成语即可：
```
舞文弄墨
```

#### 3. 查看积分
```
/chengyu_score
```

#### 4. 查看帮助
```
/chengyu_help
```

#### 5. 结束游戏
```
/chengyu_stop
```

## 🎯 游戏规则

### 基本规则
1. **成语格式**：必须是四字成语
2. **接龙规则**：下一个成语的首字必须是上一个成语的尾字
3. **唯一性**：不能重复使用已用过的成语
4. **AI对战**：AI会自动参与接龙，增加挑战性
5. **计分规则**：每成功接龙一次得1分

### 游戏流程
1. 用户发起游戏或指定开始成语
2. 用户输入成语进行接龙
3. AI自动验证并接龙
4. 循环进行直到有人无法接龙
5. 系统自动计分和统计

### 胜负条件
• **成语格式错误** → 失败
• **无法接龙**（首尾字不匹配）→ 失败
• **重复使用成语** → 失败
• **AI无法接龙** → 用户获胜

## 📊 指令列表

| 指令 | 功能 | 示例 |
|------|------|------|
| `/chengyu_start [成语]` | 开始成语接龙游戏 | `/chengyu_start 龙飞凤舞` |
| `/chengyu_stop` | 结束当前游戏 | `/chengyu_stop` |
| `/chengyu_score` | 查看积分排行榜 | `/chengyu_score` |
| `/chengyu_help` | 显示帮助信息 | `/chengyu_help` |

## ⚙️ 配置说明

### 🤖 LLM 智能验证配置

> **重要**：本插件使用 LLM API 进行智能成语验证和AI接龙，需要在 AstrBot 中配置 LLM Provider。

#### 支持的 LLM Provider：
• 🇨🇳 **智谱AI** (glm-4-flash) - 推荐，成语识别准确
• 🌐 **OpenAI** (gpt-3.5-turbo/gpt-4) - 稳定可靠
• 🇨🇳 **阿里通义千问** (qwen-turbo) - 中文成语理解好
• 🌐 **Google Gemini** - 免费额度大
• 🌐 **Anthropic Claude** - 文学知识丰富

#### 配置步骤：
1. 访问 AstrBot 管理面板：[http://localhost:6185](http://localhost:6185/)
2. 进入 LLM 配置页面：点击左侧菜单 `LLM 配置`
3. 添加 Provider：选择任意一个 LLM 服务商
4. 设置为默认：将添加的 Provider 设为默认
5. 重启 AstrBot：使配置生效

#### 未配置 LLM 的影响：
• ⚠️ 只能进行基础格式验证（四字汉字）
• 🤖 无法使用AI智能接龙功能
• 💡 建议配置 LLM 以获得完整体验

### 📁 数据存储

插件数据存储在 `data/chengyu/` 目录下：
• `scores.json` - 积分数据（按会话分类）
• `history.json` - 游戏历史记录（按会话分类）

## 🎮 游戏示例

```
用户: /chengyu_start 龙飞凤舞
机器人: 🐉 成语接龙开始！
       🎯 当前成语：龙飞凤舞
       👤 请接以'舞'开头的成语！

用户: 舞文弄墨
机器人: ✅ 用户接龙成功！
       📝 成语：舞文弄墨
       🏆 你的积分：1
       🤖 AI正在思考...

机器人: 🤖 AI接龙：墨守成规
       👤 请接以'规'开头的成语！
       📊 当前轮数：用户 1 | AI 1

用户: 规行矩步
机器人: ✅ 用户接龙成功！
       📝 成语：规行矩步
       🏆 你的积分：2
       🤖 AI正在思考...
```

## 🛠️ 技术实现

### 核心功能
• **异步处理** - 基于 asyncio 的异步游戏管理
• **LLM 成语验证** - 智能判断成语有效性
• **AI 智能接龙** - LLM生成合适的接龙成语
• **数据持久化** - JSON格式存储游戏数据
• **会话隔离** - 多群组独立游戏状态

### 验证机制
• **格式检查** - 四字汉字基础验证
• **LLM验证** - 智能判断是否为标准成语
• **接龙检查** - 验证首尾字匹配
• **重复检测** - 防止重复使用成语

### 依赖要求
• Python 3.10+
• AstrBot 3.5+
• 标准库：`asyncio`, `json`, `os`, `re`, `datetime`, `typing`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

享受成语接龙的乐趣吧！🐉✨

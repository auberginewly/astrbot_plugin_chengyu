# 🐉 AstrBot 成语接龙插件 v2.0.1

> 一个支持AI智能对战的成语接龙插件，全新升级！让传统文字游戏更有趣！

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.5+-green.svg)](https://github.com/Soulter/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.1-red.svg)](https://github.com/auberginewly/astrbot_plugin_chengyu)

## 🆕 v2.0.1 重大更新

### 🎯 核心功能优化
- ✅ **分用户积分统计** - 每个用户独立记录最近三局积分
- ✅ **简化命令系统** - 使用 `/c` 替代 `/chengyu`，告别下划线
- ✅ **智能消息过滤** - 自动过滤非成语消息，群聊更和谐
- ✅ **随机开始成语** - LLM 智能生成开始成语，告别固定开场
- ✅ **命令保护机制** - 排除系统命令被误识别为成语
- ✅ **会话完全隔离** - 不同群组/私聊数据独立，互不干扰

### 📊 全新积分系统
- 🏆 保存每个用户最近 **3 局** 的详细积分记录
- 📈 显示总分、平均分等统计数据
- 🔒 不同会话（群组/私聊）数据完全隔离
- 💾 游戏结束后自动保存积分记录

## 🎮 使用指南

### 📋 命令列表
```bash
/c start           # 随机生成开始成语
/c start 龙飞凤舞   # 指定开始成语
/c stop            # 结束游戏并保存积分
/c ls              # 查看最近三局积分记录
/c help            # 查看详细帮助
```

### 🚀 快速开始
1. **开始游戏**：发送 `/c start`
2. **参与接龙**：直接输入四字成语
3. **AI对战**：AI会自动参与接龙挑战
4. **结束保存**：发送 `/c stop` 保存积分

### 💡 使用示例
```
用户: /c start
机器人: 🐉 成语接龙开始！
       🎯 当前成语：虎虎生威
       👤 请接以'威'开头的成语！

用户: 威风凛凛
机器人: ✅ 小明 接龙成功！
       📝 成语：威风凛凛
       🏆 本局积分：1
       🤖 AI正在思考...
       
       🤖 AI接龙：凛然正气
       👤 请接以'气'开头的成语！
```

## ✨ 核心功能

### 🤖 AI智能系统
- **智能验证** - LLM判断输入是否为标准成语
- **AI对战** - 智能AI参与接龙，提供挑战
- **随机开始** - LLM生成随机开始成语
- **智能降级** - Provider不可用时自动回退基础验证

### 🛡️ 智能过滤
- **快速过滤** - 自动识别并跳过非成语消息
- **命令保护** - 排除以 `/` 开头的系统命令
- **格式检查** - 只处理四字汉字组合
- **常见词过滤** - 排除包含"你我他"等日常用词

### 📊 积分统计
- **个人记录** - 每用户独立积分统计
- **历史保存** - 最近3局详细记录
- **会话隔离** - 群组/私聊数据完全分离
- **统计分析** - 总分、平均分、游戏时间

## 📋 游戏规则

1. 🎯 使用标准**四字成语**进行接龙
2. 🔗 下一个成语**首字**必须是上一个成语**尾字**
3. 🚫 不能**重复使用**已用过的成语
4. 🤖 AI会**自动参与**接龙挑战
5. 🏆 每成功接龙一次获得 **1分**
6. 💾 游戏结束后积分自动保存

## 🛠️ 安装部署

### 前置要求
- ✅ AstrBot 3.5+
- ✅ 配置好的 LLM Provider
- ✅ Python 3.10+

### 安装方式

#### 方式1：GitHub直接安装
```bash
/plugin get https://github.com/auberginewly/astrbot_plugin_chengyu.git
```

#### 方式2：手动安装
1. 下载插件包：`astrbot_plugin_chengyu_v2.0.1.zip`
2. 解压到插件目录：`data/plugins/`
3. 重启AstrBot服务

### 配置说明
确保在AstrBot面板中配置了可用的LLM Provider：
- ✅ doubao（豆包）
- ✅ siliconflow（硅基流动）
- ✅ 其他兼容的Provider

## 📈 更新日志

### v2.0.1 (2024-12-26)
- 🔧 修复 @filter 装饰器参数传递问题
- 🔧 优化事件处理方法签名兼容性
- 🆕 新增数据库随机抽取成语功能
- 📊 完善会话隔离逻辑
- ✅ 提升插件稳定性和兼容性

### v2.0.0 (2024-12-25)
- 🆕 全新的用户积分系统
- 🆕 简化命令（/c 系列）
- 🆕 智能消息过滤机制
- 🆕 LLM随机生成开始成语
- 🆕 会话完全隔离
- 🔧 修复系统命令误识别bug
- 🔧 优化AI接龙逻辑
- 📊 新增最近三局积分查看

### v1.0.0
- 🎉 初始版本发布
- 🤖 基础AI接龙功能
- 📊 简单积分统计

## 🤝 贡献与反馈

- 📧 Issues: [GitHub Issues](https://github.com/auberginewly/astrbot_plugin_chengyu/issues)
- 🌟 Star: [GitHub Repository](https://github.com/auberginewly/astrbot_plugin_chengyu)
- 🔄 Pull Requests Welcome!

## 🤝 鸣谢

- [idiom-database](https://github.com/crazywhalecc/idiom-database) - 优质的成语数据库，拥有30000+个成语，提供首尾拼音数据支持

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**开始你的智能成语接龙之旅吧！** 🚀🐉

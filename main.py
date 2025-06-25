import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, Set, List

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import At


@register("chengyu", "auberginewly", "支持LLM智能接龙的成语接龙插件", "2.0.0")
class ChengyuJielongPlugin(Star):
    """成语接龙插件 v2.0

    支持多群/用户同时进行成语接龙游戏，AI智能接龙，分用户积分统计
    """

    def __init__(self, context: Context):
        super().__init__(context)
        # 存储游戏状态的字典，key为session_id
        self.active_sessions: Dict[str, dict] = {}
        
        # 数据存储路径
        self.data_dir = os.path.join("data", "chengyu")
        self.user_scores_file = os.path.join(self.data_dir, "user_scores.json")
        self.game_history_file = os.path.join(self.data_dir, "game_history.json")

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

        # 用户数据结构: {session_id: {user_id: {"name": str, "recent_games": [game_data]}}}
        self.user_scores = {}
        # 游戏历史: {session_id: [game_data]}
        self.game_history = {}

        # 加载历史数据
        self.load_data()

    async def initialize(self):
        """插件初始化"""
        logger.info("🔗 成语接龙插件 v2.0 初始化完成")

    def load_data(self):
        """加载持久化数据"""
        try:
            # 加载用户积分数据
            if os.path.exists(self.user_scores_file):
                with open(self.user_scores_file, "r", encoding="utf-8") as f:
                    self.user_scores = json.load(f)
            else:
                self.user_scores = {}

            # 加载游戏历史
            if os.path.exists(self.game_history_file):
                with open(self.game_history_file, "r", encoding="utf-8") as f:
                    self.game_history = json.load(f)
            else:
                self.game_history = {}

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.user_scores = {}
            self.game_history = {}

    def save_data(self):
        """保存持久化数据"""
        try:
            # 保存用户积分数据
            with open(self.user_scores_file, "w", encoding="utf-8") as f:
                json.dump(self.user_scores, f, ensure_ascii=False, indent=2)

            # 保存游戏历史
            with open(self.game_history_file, "w", encoding="utf-8") as f:
                json.dump(self.game_history, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    def get_session_id(self, event: AstrMessageEvent) -> str:
        """获取会话ID"""
        try:
            # 尝试不同的方法获取群组信息
            if hasattr(event, 'is_group') and event.is_group():
                return f"group_{event.group_id}"
            elif hasattr(event, 'group_id') and event.group_id:
                return f"group_{event.group_id}"
            elif hasattr(event, 'message_type') and event.message_type == 'group':
                return f"group_{getattr(event, 'group_id', 'unknown')}"
            else:
                # 私聊或其他类型
                user_id = getattr(event, 'user_id', None) or event.get_sender_id()
                return f"user_{user_id}"
        except Exception as e:
            logger.error(f"获取会话ID失败: {e}")
            # fallback：使用发送者ID
            try:
                return f"user_{event.get_sender_id()}"
            except:
                return "user_unknown"

    def is_potential_chengyu(self, text: str) -> bool:
        """快速判断是否可能是成语（过滤掉明显不是成语的文本）"""
        if not text:
            return False
            
        # 去除标点符号和空格
        cleaned_text = re.sub(r"[^\u4e00-\u9fff]", "", text)
        
        # 基础条件：必须是4个汉字
        if len(cleaned_text) != 4:
            return False
            
        # 排除系统命令（以/开头）
        if text.startswith("/"):
            return False
            
        # 排除包含数字、英文字母的文本
        if re.search(r"[0-9a-zA-Z]", text):
            return False
            
        # 排除常见的非成语四字词组
        non_chengyu_patterns = [
            r".*说.*",  # 包含"说"字的通常不是成语
            r".*了.*",  # 包含"了"字的通常不是成语
            r".*你.*",  # 包含"你"字的通常不是成语
            r".*我.*",  # 包含"我"字的通常不是成语
            r".*他.*",  # 包含"他"字的通常不是成语
            r".*这.*",  # 包含"这"字的通常不是成语
            r".*那.*",  # 包含"那"字的通常不是成语
            r".*什么.*", # 包含"什么"的不是成语
            r".*怎么.*", # 包含"怎么"的不是成语
        ]
        
        for pattern in non_chengyu_patterns:
            if re.match(pattern, cleaned_text):
                return False
                
        return True

    async def generate_random_chengyu(self) -> str:
        """使用LLM生成随机开始成语"""
        try:
            logger.info("🎲 尝试生成随机开始成语...")
            provider = self.context.get_using_provider()
            logger.info(f"🎲 获取到的 Provider: {provider}")
            
            if not provider:
                # 尝试获取所有可用的 Provider
                try:
                    all_providers = self.context.get_all_providers()
                    logger.info(f"🎲 所有可用 Provider: {all_providers}")
                    if all_providers:
                        provider = list(all_providers.values())[0]  # 使用第一个可用的
                        logger.info(f"🎲 使用第一个可用 Provider: {provider}")
                except Exception as e:
                    logger.warning(f"🎲 获取所有 Provider 失败: {e}")
                
                if not provider:
                    logger.warning("⚠️ 无法获取 LLM Provider，使用默认成语")
                    return "龙飞凤舞"

            # 构造生成成语的提示词
            prompt = """请随机生成一个常见的四字成语作为成语接龙的开始。

要求：
1. 必须是标准的四字成语
2. 选择比较常见、容易接龙的成语
3. 只回答成语本身，不要解释
4. 确保成语正确且有意义

请回答一个成语："""

            logger.info("🚀 开始调用LLM生成随机成语...")
            response = await provider.text_chat(prompt=prompt)
            logger.info("✅ LLM生成成语调用完成")

            if response and response.completion_text:
                generated = response.completion_text.strip()
                # 清理响应，提取成语
                generated = re.sub(r"[^\u4e00-\u9fff]", "", generated)
                
                if len(generated) == 4:
                    logger.info(f"🎉 LLM生成成语成功: '{generated}'")
                    return generated
                else:
                    logger.warning(f"⚠️ LLM生成的成语格式错误: '{generated}'，使用默认成语")
                    return "龙飞凤舞"
            else:
                logger.warning("⚠️ LLM响应为空，使用默认成语")
                return "龙飞凤舞"

        except Exception as e:
            logger.error(f"❌ 生成随机成语失败: {e}")
            return "龙飞凤舞"

    async def is_valid_chengyu(self, text: str) -> tuple[bool, str]:
        """使用 LLM API 检查是否为有效成语"""
        logger.info(f"🔍 开始检查成语: '{text}'")
        
        if not text:
            logger.info("❌ 文本为空")
            return False, "文本为空"

        # 去除标点符号和空格
        cleaned_text = re.sub(r"[^\u4e00-\u9fff]", "", text)
        logger.info(f"🧹 清理后的文本: '{cleaned_text}'")

        # 基础检查：成语一般是4个字
        if len(cleaned_text) != 4:
            logger.info(f"❌ 长度不符合：{len(cleaned_text)} 字（成语应为4字）")
            return False, f"成语应为4个汉字，你输入了{len(cleaned_text)}个字"

        # 基础检查：是否全是汉字
        if not re.match(r"^[\u4e00-\u9fff]+$", cleaned_text):
            logger.info("❌ 不全是汉字")
            return False, "成语应全为汉字"

        logger.info("✅ 通过基础检查，开始LLM验证")

        # 使用 LLM API 进行成语验证
        try:
            logger.info("🔍 尝试获取 LLM Provider...")
            provider = self.context.get_using_provider()
            logger.info(f"🔍 获取到的 Provider: {provider}")
            logger.info(f"🔍 Provider 类型: {type(provider) if provider else 'None'}")
            
            if not provider:
                logger.warning("⚠️ 未配置 LLM Provider！")
                logger.warning("💡 请在 AstrBot 设置中配置 LLM Provider 以启用智能成语验证")
                logger.warning("🔄 当前使用基础检查（仅验证格式）")
                
                # 尝试获取所有可用的 Provider
                try:
                    all_providers = self.context.get_all_providers()
                    logger.info(f"🔍 所有可用 Provider: {all_providers}")
                    if all_providers:
                        provider = list(all_providers.values())[0]  # 使用第一个可用的
                        logger.info(f"🔄 使用第一个可用 Provider: {provider}")
                except Exception as e:
                    logger.warning(f"🔍 获取所有 Provider 失败: {e}")
                
                if not provider:
                    return True, "格式检查通过"

            logger.info(f"🤖 找到LLM Provider: {provider.__class__.__name__}")

            # 构造提示词
            prompt = f"""请判断"{text}"是否为标准的中文成语。

判断标准：
1. 是中文成语（四字固定词组，有典故或特定含义）→ 回答"是"
2. 不是标准成语（词语组合、现代词汇等）→ 回答"否"
3. 只需回答"是"或"否"，不要解释

文本：{text}
回答："""

            logger.info("🚀 开始调用LLM API验证成语...")
            response = await provider.text_chat(prompt=prompt)
            logger.info("✅ LLM API调用完成")

            if response and response.completion_text:
                result = response.completion_text.strip()
                logger.info(f"🎯 LLM验证结果: '{result}'")
                
                # 解析结果
                result_lower = result.lower()
                is_chengyu = (
                    "是" in result or 
                    "yes" in result_lower or 
                    "true" in result_lower or
                    "成语" in result
                )
                
                if is_chengyu:
                    logger.info(f"✅ LLM确认: '{text}' 是成语")
                    return True, "LLM验证通过"
                else:
                    logger.info(f"❌ LLM判断: '{text}' 不是成语")
                    return False, "不是标准成语"
            else:
                logger.warning("⚠️ LLM响应为空，使用基础检查")
                return True, "基础检查通过"

        except Exception as e:
            logger.error(f"❌ LLM验证失败: {e}")
            logger.warning("🔄 LLM失败，使用基础检查结果")
            return True, "基础检查通过"

    async def ai_jielong(self, last_chengyu: str) -> tuple[bool, str, str]:
        """AI智能成语接龙"""
        logger.info(f"🤖 AI开始接龙，上一个成语: '{last_chengyu}'")
        
        try:
            logger.info("🤖 尝试获取 LLM Provider 进行接龙...")
            provider = self.context.get_using_provider()
            logger.info(f"🤖 获取到的 Provider: {provider}")
            logger.info(f"🤖 Provider 类型: {type(provider) if provider else 'None'}")
            
            if not provider:
                logger.warning("⚠️ 未配置 LLM Provider，无法AI接龙")
                
                # 尝试获取所有可用的 Provider
                try:
                    all_providers = self.context.get_all_providers()
                    logger.info(f"🤖 所有可用 Provider: {all_providers}")
                    if all_providers:
                        provider = list(all_providers.values())[0]  # 使用第一个可用的
                        logger.info(f"🤖 使用第一个可用 Provider: {provider}")
                except Exception as e:
                    logger.warning(f"🤖 获取所有 Provider 失败: {e}")
                
                if not provider:
                    return False, "未配置LLM", ""

            # 获取最后一个字作为接龙字
            last_char = last_chengyu[-1]
            logger.info(f"🎯 需要接的字: '{last_char}'")

            # 构造AI接龙提示词
            prompt = f"""请接成语接龙！

上一个成语：{last_chengyu}
需要接的字：{last_char}（{last_chengyu}的最后一个字）

要求：
1. 找一个以"{last_char}"开头的标准成语
2. 只回答成语本身，不要解释
3. 确保是常见的四字成语
4. 避免生僻或争议性成语

请回答："""

            logger.info("🚀 开始调用LLM进行AI接龙...")
            response = await provider.text_chat(prompt=prompt)
            logger.info("✅ AI接龙调用完成")

            if response and response.completion_text:
                ai_chengyu = response.completion_text.strip()
                # 清理响应，提取成语
                ai_chengyu = re.sub(r"[^\u4e00-\u9fff]", "", ai_chengyu)
                
                if len(ai_chengyu) == 4 and ai_chengyu[0] == last_char:
                    logger.info(f"🎉 AI成功接龙: '{ai_chengyu}'")
                    return True, ai_chengyu, f"AI接龙成功"
                else:
                    logger.warning(f"⚠️ AI接龙格式错误: '{ai_chengyu}'")
                    return False, "AI接龙失败", "格式不符合要求"
            else:
                logger.warning("⚠️ AI接龙响应为空")
                return False, "AI接龙失败", "无响应"

        except Exception as e:
            logger.error(f"❌ AI接龙失败: {e}")
            return False, "AI接龙失败", str(e)

    def can_jielong(self, last_chengyu: str, new_chengyu: str) -> tuple[bool, str]:
        """检查能否接龙"""
        if not last_chengyu or not new_chengyu:
            return False, "成语为空"
        
        last_char = last_chengyu[-1]
        first_char = new_chengyu[0]
        
        if last_char == first_char:
            return True, "可以接龙"
        else:
            return False, f"无法接龙：'{last_chengyu}'的尾字是'{last_char}'，'{new_chengyu}'的首字是'{first_char}'"

    def add_user_score(self, session_id: str, user_id: str, user_name: str, score: int):
        """添加用户积分到最近三局记录"""
        if session_id not in self.user_scores:
            self.user_scores[session_id] = {}
        
        if user_id not in self.user_scores[session_id]:
            self.user_scores[session_id][user_id] = {
                "name": user_name,
                "recent_games": []
            }
        
        # 更新用户姓名（可能会变化）
        self.user_scores[session_id][user_id]["name"] = user_name
        
        # 添加本局积分
        game_data = {
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        self.user_scores[session_id][user_id]["recent_games"].append(game_data)
        
        # 只保留最近3局
        self.user_scores[session_id][user_id]["recent_games"] = \
            self.user_scores[session_id][user_id]["recent_games"][-3:]

    @filter.command("c")
    async def c_command(self, event: AstrMessageEvent):
        """成语接龙主命令"""
        try:
            args = event.message_str.strip().split()
            if len(args) < 2:
                yield event.plain_result(
                    "🐉 成语接龙插件 v2.0\n\n"
                    "📋 可用命令：\n"
                    "• /c start [成语] - 开始游戏\n"
                    "• /c stop - 结束游戏\n"
                    "• /c ls - 查看最近三局积分\n"
                    "• /c help - 查看帮助\n\n"
                    "💡 示例：/c start 或 /c start 龙飞凤舞"
                )
                return
            
            subcommand = args[1].lower()
            
            # 使用直接分发而不是async for
            if subcommand == "start":
                generator = self.start_game(event, args[2:])
                async for result in generator:
                    yield result
            elif subcommand == "stop":
                generator = self.stop_game(event)
                async for result in generator:
                    yield result
            elif subcommand == "ls":
                generator = self.show_recent_scores(event)
                async for result in generator:
                    yield result
            elif subcommand == "help":
                generator = self.show_help(event)
                async for result in generator:
                    yield result
            else:
                yield event.plain_result(f"❌ 未知命令: {subcommand}\n💡 使用 /c 查看可用命令")
                
        except Exception as e:
            logger.error(f"❌ 处理c命令失败: {e}")
            yield event.plain_result("❌ 命令处理失败")

    async def start_game(self, event: AstrMessageEvent, args: List[str]):
        """开始成语接龙游戏"""
        try:
            logger.info(f"🎮 收到成语接龙开始命令，参数: {args}")
            
            session_id = self.get_session_id(event)
            logger.info(f"🎮 会话ID: {session_id}")
            
            # 检查是否已有游戏在进行
            if session_id in self.active_sessions:
                logger.info(f"🎮 会话 {session_id} 已有游戏在进行")
                yield event.plain_result("🎮 成语接龙已在进行中！\n💡 使用 /c stop 结束当前游戏")
                return

            start_chengyu = ""
            
            if args:
                start_chengyu = "".join(args)
                logger.info(f"🎮 用户指定开始成语: {start_chengyu}")
                # 验证开始成语
                is_valid, reason = await self.is_valid_chengyu(start_chengyu)
                if not is_valid:
                    logger.info(f"🎮 开始成语验证失败: {reason}")
                    yield event.plain_result(f"❌ '{start_chengyu}' {reason}\n💡 请输入一个有效的四字成语")
                    return
                logger.info(f"🎮 开始成语验证通过: {start_chengyu}")
            else:
                # 没有指定开始成语，使用LLM生成
                logger.info(f"🎮 生成随机开始成语...")
                yield event.plain_result("🎲 正在生成随机开始成语，请稍候...")
                start_chengyu = await self.generate_random_chengyu()
                logger.info(f"🎮 生成的开始成语: {start_chengyu}")

            # 创建游戏会话
            logger.info(f"🎮 创建游戏会话...")
            self.active_sessions[session_id] = {
                "current_chengyu": start_chengyu,
                "history": [start_chengyu],
                "user_scores": {},  # 当前游戏中的用户积分
                "start_time": datetime.now().isoformat(),
                "last_player": "AI"
            }

            logger.info(f"🎮 会话 {session_id} 开始成语接龙，开始成语: {start_chengyu}")

            yield event.plain_result(
                f"🐉 成语接龙开始！\n"
                f"🎯 当前成语：{start_chengyu}\n"
                f"👤 请接以'{start_chengyu[-1]}'开头的成语！\n"
                f"🤖 AI会和你一起接龙\n"
                f"📝 使用 /c stop 结束游戏"
            )

        except Exception as e:
            logger.error(f"❌ 开始成语接龙失败: {e}", exc_info=True)
            yield event.plain_result(f"❌ 开始游戏失败：{str(e)}\n💡 请查看日志或稍后再试")

    async def stop_game(self, event: AstrMessageEvent):
        """停止成语接龙"""
        try:
            session_id = self.get_session_id(event)
            
            if session_id not in self.active_sessions:
                yield event.plain_result("📴 当前没有进行中的成语接龙游戏")
                return

            game = self.active_sessions[session_id]
            
            # 保存每个用户的积分到历史记录
            for user_id, score in game["user_scores"].items():
                user_name = score.get("name", f"用户{user_id}")
                self.add_user_score(session_id, user_id, user_name, score["score"])
            
            # 保存游戏历史
            if session_id not in self.game_history:
                self.game_history[session_id] = []
            
            self.game_history[session_id].append({
                "start_time": game["start_time"],
                "end_time": datetime.now().isoformat(),
                "history": game["history"],
                "total_rounds": len(game["history"]) - 1,  # 减去开始成语
                "participants": len(game["user_scores"])
            })
            
            # 只保留最近10次游戏记录
            self.game_history[session_id] = self.game_history[session_id][-10:]
            
            del self.active_sessions[session_id]
            self.save_data()
            logger.info(f"🎮 会话 {session_id} 游戏结束")
            
            yield event.plain_result(
                f"🛑 成语接龙已结束！\n"
                f"📊 本轮统计：\n"
                f"📝 共接龙 {len(game['history'])} 个成语\n"
                f"👥 参与人数 {len(game['user_scores'])} 人\n"
                f"💡 使用 /c start 开始新游戏\n"
                f"📋 使用 /c ls 查看积分记录"
            )

        except Exception as e:
            logger.error(f"停止成语接龙失败: {e}")
            yield event.plain_result("❌ 停止游戏失败")

    async def show_recent_scores(self, event: AstrMessageEvent):
        """显示最近三局积分"""
        try:
            session_id = self.get_session_id(event)
            
            if session_id not in self.user_scores or not self.user_scores[session_id]:
                yield event.plain_result("📊 当前会话还没有积分记录\n💡 使用 /c start 开始游戏")
                return

            result = "🏆 最近三局积分记录 🏆\n\n"
            
            for user_id, user_data in self.user_scores[session_id].items():
                user_name = user_data["name"]
                recent_games = user_data["recent_games"]
                
                if not recent_games:
                    continue
                    
                result += f"👤 {user_name}:\n"
                total_score = 0
                
                for i, game in enumerate(recent_games, 1):
                    score = game["score"]
                    date = game["date"]
                    total_score += score
                    result += f"  第{i}局: {score}分 ({date})\n"
                
                avg_score = round(total_score / len(recent_games), 1)
                result += f"  📈 总计: {total_score}分 | 平均: {avg_score}分\n\n"

            yield event.plain_result(result)

        except Exception as e:
            logger.error(f"显示积分记录失败: {e}")
            yield event.plain_result("❌ 获取积分记录失败")

    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """🐉 成语接龙插件 v2.0 帮助 🐉

📋 命令列表：
• /c start [成语] - 开始接龙游戏
• /c stop - 结束当前游戏
• /c ls - 查看最近三局积分
• /c help - 显示此帮助

🎮 游戏规则：
1. 使用四字成语进行接龙
2. 下一个成语的首字必须是上一个成语的尾字
3. 不能重复使用已用过的成语
4. AI会自动参与接龙
5. 每成功接龙一次得1分

💡 使用示例：
/c start          # 随机生成开始成语
/c start 龙飞凤舞  # 指定开始成语
然后输入：舞文弄墨
AI会自动接：墨守成规
你再接：规行矩步
...依此类推

🆕 v2.0 新功能：
• 分用户积分统计（会话隔离）
• 保存最近三局积分记录
• 简化命令（/c 替代 /chengyu）
• 智能过滤非成语消息
• LLM随机生成开始成语
• 排除系统命令干扰

🤖 智能功能：
• LLM验证成语有效性
• AI智能接龙对战
• 自动判断接龙正确性
• 随机生成开始成语

开始你的成语接龙之旅吧！🚀"""

        yield event.plain_result(help_text)

    @filter.regex(r".*")
    async def handle_chengyu_input(self, event: AstrMessageEvent):
        """处理成语输入"""
        try:
            session_id = self.get_session_id(event)
            
            # 检查是否有活跃的接龙游戏
            if session_id not in self.active_sessions:
                return

            message_text = event.message_str.strip()
            
            # 跳过命令
            if message_text.startswith("/"):
                return
            
            # 快速过滤：不是潜在成语的直接跳过
            if not self.is_potential_chengyu(message_text):
                return

            game = self.active_sessions[session_id]
            user_id = event.get_sender_id()
            user_name = event.get_sender_name()

            logger.info(f"👤 用户 {user_name} 尝试接龙: '{message_text}'")

            # 验证用户输入的成语
            is_valid, reason = await self.is_valid_chengyu(message_text)
            if not is_valid:
                yield event.plain_result(f"❌ {user_name}，{reason}\n💡 请输入有效的四字成语")
                return

            # 检查是否能接龙
            can_connect, connect_reason = self.can_jielong(game["current_chengyu"], message_text)
            if not can_connect:
                yield event.plain_result(f"❌ {user_name}，{connect_reason}")
                return

            # 检查是否重复
            if message_text in game["history"]:
                yield event.plain_result(f"❌ {user_name}，成语'{message_text}'已经用过了！")
                return

            # 用户接龙成功
            game["current_chengyu"] = message_text
            game["history"].append(message_text)
            game["last_player"] = "USER"

            # 更新当前游戏积分
            if user_id not in game["user_scores"]:
                game["user_scores"][user_id] = {"name": user_name, "score": 0}
            game["user_scores"][user_id]["score"] += 1
            game["user_scores"][user_id]["name"] = user_name  # 更新用户名

            logger.info(f"👤 用户 {user_name} 接龙成功: {message_text}")

            yield event.plain_result(
                f"✅ {user_name} 接龙成功！\n"
                f"📝 成语：{message_text}\n"
                f"🏆 本局积分：{game['user_scores'][user_id]['score']}\n"
                f"🤖 AI正在思考..."
            )

            # AI自动接龙
            await asyncio.sleep(1)  # 模拟思考时间
            
            ai_success, ai_chengyu, ai_reason = await self.ai_jielong(message_text)
            if ai_success:
                # 检查AI成语是否重复
                if ai_chengyu not in game["history"]:
                    game["current_chengyu"] = ai_chengyu
                    game["history"].append(ai_chengyu)
                    game["last_player"] = "AI"

                    logger.info(f"🤖 AI接龙成功: {ai_chengyu}")

                    yield event.plain_result(
                        f"🤖 AI接龙：{ai_chengyu}\n"
                        f"👤 请接以'{ai_chengyu[-1]}'开头的成语！\n"
                        f"📊 当前轮数：{len(game['history'])-1} 轮"
                    )
                else:
                    # AI重复了，用户获胜
                    yield event.plain_result(
                        f"🎉 恭喜！AI想到的成语'{ai_chengyu}'重复了！\n"
                        f"👑 {user_name} 获得胜利！\n"
                        f"📊 游戏结束，使用 /c stop 保存记录"
                    )
            else:
                # AI接龙失败，用户获胜
                yield event.plain_result(
                    f"🎉 恭喜！AI接龙失败了！\n"
                    f"👑 {user_name} 获得胜利！\n"
                    f"🤖 AI说：{ai_reason}\n"
                    f"📊 游戏结束，使用 /c stop 保存记录"
                )

        except Exception as e:
            logger.error(f"处理成语输入失败: {e}")

    async def terminate(self):
        """插件终止时的清理工作"""
        try:
            self.save_data()
            logger.info("🔗 成语接龙插件 v2.0 已终止")
        except Exception as e:
            logger.error(f"插件终止时出错: {e}")

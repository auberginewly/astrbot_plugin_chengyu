import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, Set

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import At


@register("chengyu", "auberginewly", "支持LLM智能接龙的成语接龙插件", "1.0.0")
class ChengyuJielongPlugin(Star):
    """成语接龙插件

    支持多群/用户同时进行成语接龙游戏，AI智能接龙，实时积分统计
    """

    def __init__(self, context: Context):
        super().__init__(context)
        # 存储游戏状态的字典，key为group_id或user_id
        self.active_sessions: Dict[str, dict] = {}
        # 数据存储路径
        self.data_dir = os.path.join("data", "chengyu")
        self.scores_file = os.path.join(self.data_dir, "scores.json")
        self.history_file = os.path.join(self.data_dir, "history.json")

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

        # 加载历史数据
        self.load_data()

    async def initialize(self):
        """插件初始化"""
        logger.info("🔗 成语接龙插件初始化完成")

    def load_data(self):
        """加载持久化数据"""
        try:
            # 加载积分数据
            if os.path.exists(self.scores_file):
                with open(self.scores_file, "r", encoding="utf-8") as f:
                    self.all_scores = json.load(f)
            else:
                self.all_scores = {}

            # 加载接龙历史
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.all_history = json.load(f)
            else:
                self.all_history = {}

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.all_scores = {}
            self.all_history = {}

    def save_data(self):
        """保存持久化数据"""
        try:
            # 保存积分数据
            with open(self.scores_file, "w", encoding="utf-8") as f:
                json.dump(self.all_scores, f, ensure_ascii=False, indent=2)

            # 保存接龙历史
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.all_history, f, ensure_ascii=False, indent=2)

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
            provider = self.context.get_using_provider()
            if not provider:
                logger.warning("⚠️ 未配置 LLM Provider！")
                logger.warning("💡 请在 AstrBot 设置中配置 LLM Provider 以启用智能成语验证")
                logger.warning("🔄 当前使用基础检查（仅验证格式）")
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
            provider = self.context.get_using_provider()
            if not provider:
                logger.warning("⚠️ 未配置 LLM Provider，无法AI接龙")
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

    @filter.command("chengyu_start")
    async def start_chengyu(self, event: AstrMessageEvent):
        """开始成语接龙
        
        指令格式：/chengyu_start [开始成语]
        示例：/chengyu_start 龙飞凤舞
        """
        try:
            logger.info(f"🎮 收到成语接龙开始命令: {event.message_str}")
            logger.info(f"🎮 事件对象类型: {type(event)}")
            logger.info(f"🎮 事件对象属性: {dir(event)}")
            
            session_id = self.get_session_id(event)
            logger.info(f"🎮 会话ID: {session_id}")
            
            # 检查是否已有游戏在进行
            if session_id in self.active_sessions:
                logger.info(f"🎮 会话 {session_id} 已有游戏在进行")
                yield event.plain_result("🎮 成语接龙已在进行中！\n💡 使用 /chengyu_stop 结束当前游戏")
                return

            args = event.message_str.strip().split()[1:]  # 去掉命令本身
            logger.info(f"🎮 解析参数: {args}")
            
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
                # 没有指定开始成语，使用默认成语
                start_chengyu = "龙飞凤舞"  # 默认开始成语
                logger.info(f"🎮 使用默认开始成语: {start_chengyu}")

            # 创建游戏会话
            logger.info(f"🎮 创建游戏会话...")
            self.active_sessions[session_id] = {
                "current_chengyu": start_chengyu,
                "history": [start_chengyu],
                "user_count": 0,
                "ai_count": 1,
                "start_time": datetime.now().isoformat(),
                "last_player": "AI" if not args else "USER"
            }

            logger.info(f"🎮 会话 {session_id} 开始成语接龙，开始成语: {start_chengyu}")

            yield event.plain_result(
                f"🐉 成语接龙开始！\n"
                f"🎯 当前成语：{start_chengyu}\n"
                f"👤 请接以'{start_chengyu[-1]}'开头的成语！\n"
                f"🤖 AI会和你一起接龙\n"
                f"📝 使用 /chengyu_stop 结束游戏"
            )

        except Exception as e:
            logger.error(f"❌ 开始成语接龙失败: {e}", exc_info=True)
            yield event.plain_result(f"❌ 开始游戏失败：{str(e)}\n💡 请查看日志或稍后再试")

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

            game = self.active_sessions[session_id]
            user_id = event.get_sender_id()
            user_name = event.get_sender_name()

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
            game["user_count"] += 1
            game["last_player"] = "USER"

            logger.info(f"👤 用户 {user_name} 接龙成功: {message_text}")

            # 更新积分
            if session_id not in self.all_scores:
                self.all_scores[session_id] = {}
            if user_id not in self.all_scores[session_id]:
                self.all_scores[session_id][user_id] = {"name": user_name, "score": 0}
            self.all_scores[session_id][user_id]["score"] += 1

            yield event.plain_result(
                f"✅ {user_name} 接龙成功！\n"
                f"📝 成语：{message_text}\n"
                f"🏆 你的积分：{self.all_scores[session_id][user_id]['score']}\n"
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
                    game["ai_count"] += 1
                    game["last_player"] = "AI"

                    logger.info(f"🤖 AI接龙成功: {ai_chengyu}")

                    yield event.plain_result(
                        f"🤖 AI接龙：{ai_chengyu}\n"
                        f"👤 请接以'{ai_chengyu[-1]}'开头的成语！\n"
                        f"📊 当前轮数：用户 {game['user_count']} | AI {game['ai_count']}"
                    )
                else:
                    # AI重复了，用户获胜
                    yield event.plain_result(
                        f"🎉 恭喜！AI想到的成语'{ai_chengyu}'重复了！\n"
                        f"👑 {user_name} 获得胜利！\n"
                        f"📊 最终比分：用户 {game['user_count']} | AI {game['ai_count']}"
                    )
                    self._end_game(session_id)
            else:
                # AI接龙失败，用户获胜
                yield event.plain_result(
                    f"🎉 恭喜！AI接龙失败了！\n"
                    f"👑 {user_name} 获得胜利！\n"
                    f"🤖 AI说：{ai_reason}\n"
                    f"📊 最终比分：用户 {game['user_count']} | AI {game['ai_count']}"
                )
                self._end_game(session_id)

            # 保存数据
            self.save_data()

        except Exception as e:
            logger.error(f"处理成语输入失败: {e}")

    def _end_game(self, session_id: str):
        """结束游戏"""
        if session_id in self.active_sessions:
            game = self.active_sessions[session_id]
            
            # 保存游戏历史
            if session_id not in self.all_history:
                self.all_history[session_id] = []
            
            self.all_history[session_id].append({
                "start_time": game["start_time"],
                "end_time": datetime.now().isoformat(),
                "history": game["history"],
                "user_count": game["user_count"],
                "ai_count": game["ai_count"],
                "winner": game["last_player"]
            })
            
            # 只保留最近10次游戏记录
            self.all_history[session_id] = self.all_history[session_id][-10:]
            
            del self.active_sessions[session_id]
            logger.info(f"🎮 会话 {session_id} 游戏结束")

    @filter.command("chengyu_stop")
    async def stop_chengyu(self, event: AstrMessageEvent):
        """停止成语接龙"""
        try:
            session_id = self.get_session_id(event)
            
            if session_id not in self.active_sessions:
                yield event.plain_result("📴 当前没有进行中的成语接龙游戏")
                return

            game = self.active_sessions[session_id]
            self._end_game(session_id)
            self.save_data()
            
            yield event.plain_result(
                f"🛑 成语接龙已结束！\n"
                f"📊 本轮统计：用户 {game['user_count']} | AI {game['ai_count']}\n"
                f"📝 共接龙 {len(game['history'])} 个成语\n"
                f"💡 使用 /chengyu_start 开始新游戏"
            )

        except Exception as e:
            logger.error(f"停止成语接龙失败: {e}")
            yield event.plain_result("❌ 停止游戏失败")

    @filter.command("chengyu_score")
    async def show_scores(self, event: AstrMessageEvent):
        """显示积分榜"""
        try:
            session_id = self.get_session_id(event)
            
            if session_id not in self.all_scores or not self.all_scores[session_id]:
                yield event.plain_result("📊 当前会话还没有积分记录\n💡 使用 /chengyu_start 开始游戏")
                return

            # 按积分排序
            sorted_scores = sorted(
                self.all_scores[session_id].items(),
                key=lambda x: x[1]["score"],
                reverse=True
            )

            result = "🏆 成语接龙积分榜 🏆\n\n"
            for i, (user_id, data) in enumerate(sorted_scores[:10], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                result += f"{emoji} {data['name']}: {data['score']} 分\n"

            yield event.plain_result(result)

        except Exception as e:
            logger.error(f"显示积分榜失败: {e}")
            yield event.plain_result("❌ 获取积分榜失败")

    @filter.command("chengyu_help")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """🐉 成语接龙插件帮助 🐉

📋 指令列表：
• /chengyu_start [成语] - 开始接龙游戏
• /chengyu_stop - 结束当前游戏
• /chengyu_score - 查看积分榜
• /chengyu_help - 显示此帮助

🎮 游戏规则：
1. 使用四字成语进行接龙
2. 下一个成语的首字必须是上一个成语的尾字
3. 不能重复使用已用过的成语
4. AI会自动参与接龙
5. 每成功接龙一次得1分

💡 使用示例：
/chengyu_start 龙飞凤舞
然后输入：舞文弄墨
AI会自动接：墨守成规
你再接：规行矩步
...依此类推

🤖 智能功能：
• LLM验证成语有效性
• AI智能接龙对战
• 自动判断接龙正确性
• 积分统计和排行榜

开始你的成语接龙之旅吧！🚀"""

        yield event.plain_result(help_text)

    async def terminate(self):
        """插件终止时的清理工作"""
        try:
            self.save_data()
            logger.info("🔗 成语接龙插件已终止")
        except Exception as e:
            logger.error(f"插件终止时出错: {e}")

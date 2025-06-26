import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, Set, List
import sqlite3
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
        self.curr_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_file = os.path.join(self.curr_dir, "c.db")

        # 初始化数据库连接
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

        # 创建用户积分表和游戏历史表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_scores (
                session_id TEXT,
                user_id TEXT,
                user_name TEXT,
                score INTEGER,
                timestamp TEXT,
                date TEXT,
                PRIMARY KEY (session_id, user_id, timestamp)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                session_id TEXT,
                start_time TEXT,
                end_time TEXT,
                history TEXT,  -- JSON array of chengyu
                total_rounds INTEGER,
                participants INTEGER,
                PRIMARY KEY (session_id, start_time)
            )
        """)

        self.conn.commit()

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
        """从数据库加载数据"""
        try:
            # 加载用户积分数据
            self.user_scores = {}
            self.cursor.execute("""
                SELECT session_id, user_id, user_name, score, timestamp, date
                FROM user_scores
                ORDER BY timestamp DESC
            """)
            for row in self.cursor.fetchall():
                session_id, user_id, user_name, score, timestamp, date = row
                if session_id not in self.user_scores:
                    self.user_scores[session_id] = {}
                if user_id not in self.user_scores[session_id]:
                    self.user_scores[session_id][user_id] = {
                        "name": user_name,
                        "recent_games": []
                    }
                # 只保留最近3局
                if len(self.user_scores[session_id][user_id]["recent_games"]) < 3:
                    self.user_scores[session_id][user_id]["recent_games"].append({
                        "score": score,
                        "timestamp": timestamp,
                        "date": date
                    })

            # 加载游戏历史
            self.game_history = {}
            self.cursor.execute("""
                SELECT session_id, start_time, end_time, history, total_rounds, participants
                FROM game_history
                ORDER BY start_time DESC
            """)
            for row in self.cursor.fetchall():
                session_id, start_time, end_time, history, total_rounds, participants = row
                if session_id not in self.game_history:
                    self.game_history[session_id] = []
                # 只保留最近10局
                if len(self.game_history[session_id]) < 10:
                    self.game_history[session_id].append({
                        "start_time": start_time,
                        "end_time": end_time,
                        "history": json.loads(history),
                        "total_rounds": total_rounds,
                        "participants": participants
                    })

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.user_scores = {}
            self.game_history = {}

    def save_data(self):
        """保存数据到数据库"""
        try:
            # 保存用户积分数据
            for session_id, users in self.user_scores.items():
                for user_id, user_data in users.items():
                    for game in user_data["recent_games"]:
                        self.cursor.execute("""
                            INSERT OR REPLACE INTO user_scores
                            (session_id, user_id, user_name, score, timestamp, date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            session_id,
                            user_id,
                            user_data["name"],
                            game["score"],
                            game["timestamp"],
                            game["date"]
                        ))

            # 保存游戏历史
            for session_id, games in self.game_history.items():
                for game in games:
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO game_history
                        (session_id, start_time, end_time, history, total_rounds, participants)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        game["start_time"],
                        game["end_time"],
                        json.dumps(game["history"], ensure_ascii=False),
                        game["total_rounds"],
                        game["participants"]
                    ))

            self.conn.commit()

        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    def get_session_id(self, event: AstrMessageEvent) -> str:
        """获取会话ID - 群聊以group_id为单位，私聊以user_id为单位"""
        try:
            from astrbot.core.platform.message_type import MessageType

            # 使用 AstrBot 内置方法获取消息类型和相关ID
            message_type = event.get_message_type()

            if message_type == MessageType.GROUP_MESSAGE:
                # 群聊消息：使用群组ID作为会话ID，确保同群内所有成员共享同一会话
                group_id = event.get_group_id()
                return f"group_{group_id}"
            else:
                # 私聊消息：使用发送者ID作为会话ID
                user_id = event.get_sender_id()
                return f"user_{user_id}"
        except Exception as e:
            logger.error(f"获取会话ID失败: {e}")
            # 兜底方案：使用发送者ID
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
            r".*什么.*",  # 包含"什么"的不是成语
            r".*怎么.*",  # 包含"怎么"的不是成语
        ]

        for pattern in non_chengyu_patterns:
            if re.match(pattern, cleaned_text):
                return False

        return True

    async def generate_random_chengyu(self) -> str:
        """从数据库随机获取一个成语"""
        try:
            logger.info("🎲 从数据库随机获取成语...")
            self.cursor.execute(
                "SELECT word FROM idiom ORDER BY RANDOM() LIMIT 1")
            result = self.cursor.fetchone()

            if result:
                chengyu = result[0]
                logger.info(f"🎉 获取成功: '{chengyu}'")
                return chengyu
            else:
                logger.warning("⚠️ 数据库中未找到成语，使用默认成语")
                return "龙飞凤舞"

        except Exception as e:
            logger.error(f"❌ 获取随机成语失败: {e}")
            return "龙飞凤舞"

    async def is_valid_chengyu(self, text: str) -> tuple[bool, str]:
        """使用数据库检查是否为有效成语"""
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

        # 使用数据库验证成语
        is_valid, info = self.get_chengyu_info(cleaned_text)
        if is_valid:
            logger.info(f"✅ 数据库验证通过: {cleaned_text}")
            return True, "数据库验证通过"
        else:
            logger.info(f"❌ 数据库中未找到该成语: {cleaned_text}")
            return False, "未找到该成语"

    async def robot_jielong(self, last_chengyu: str) -> tuple[bool, str, str]:
        """使用数据库进行成语接龙"""
        logger.info(f"🤖 机器人开始接龙，上一个成语: '{last_chengyu}'")

        try:
            # 获取最后一个字的拼音作为接龙拼音
            last_valid, last_info = self.get_chengyu_info(last_chengyu)
            if not last_valid:
                return False, "接龙失败", "无法获取上一个成语的拼音信息"

            last_pinyin = last_info["last"]  # 最后一个字的拼音
            logger.info(f"🎯 需要接的拼音: '{last_pinyin}'")

            # 从数据库中随机获取一个以该拼音开头的成语
            chengyu_list = self.get_chengyu_by_first(last_pinyin)

            if chengyu_list:
                # 随机选择一个成语
                robot_chengyu = chengyu_list[0]  # 已经在SQL中随机排序了
                logger.info(f"🎉 数据库接龙成功: '{robot_chengyu}'")
                return True, robot_chengyu, "接龙成功"
            else:
                logger.warning(f"❌ 数据库中未找到以拼音'{last_pinyin}'开头的成语")
                return False, "接龙失败", f"找不到以拼音'{last_pinyin}'开头的成语"

        except Exception as e:
            logger.error(f"❌ 数据库接龙失败: {e}")
            return False, "接龙失败", str(e)

    def can_jielong(self, last_chengyu: str, new_chengyu: str) -> tuple[bool, str]:
        """检查能否接龙"""
        if not last_chengyu or not new_chengyu:
            return False, "成语为空"

        # 获取两个成语的信息
        last_valid, last_info = self.get_chengyu_info(last_chengyu)
        new_valid, new_info = self.get_chengyu_info(new_chengyu)

        if not last_valid or not new_valid:
            return False, "成语信息获取失败"

        # 获取最后一个字的拼音和新成语第一个字的拼音
        last_pinyin = last_info["last"]  # 最后一个字的拼音
        first_pinyin = new_info["first"]  # 第一个字的拼音

        if last_pinyin == first_pinyin:
            return True, "可以接龙"
        else:
            return False, f"无法接龙：'{last_chengyu}'的尾字拼音是'{last_pinyin}'，'{new_chengyu}'的首字拼音是'{first_pinyin}'"

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

    def get_chengyu_info(self, chengyu: str) -> tuple[bool, dict]:
        """从数据库获取成语信息"""
        try:
            self.cursor.execute(
                "SELECT word, pinyin, first, last, explanation FROM idiom WHERE word = ?",
                (chengyu,)
            )
            result = self.cursor.fetchone()

            if result:
                return True, {
                    "word": result[0],
                    "pinyin": result[1],
                    "first": result[2],
                    "last": result[3],
                    "explanation": result[4]
                }
            return False, {}

        except Exception as e:
            logger.error(f"查询数据库失败: {e}")
            return False, {}

    def get_chengyu_by_first(self, first_pinyin: str) -> List[str]:
        """根据首字拼音获取成语列表"""
        try:
            self.cursor.execute(
                "SELECT word FROM idiom WHERE first = ? ORDER BY RANDOM() LIMIT 10",
                (first_pinyin,)
            )
            results = self.cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"查询数据库失败: {e}")
            return []

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
                f"👤 请接以拼音'{self.get_chengyu_info(start_chengyu)[1]['last']}'开头的成语！\n"
                f"🤖 机器人会和你一起接龙\n"
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
                self.add_user_score(session_id, user_id,
                                    user_name, score["score"])

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
2. 下一个成语的首字拼音必须与上一个成语尾字拼音相同
3. 不能重复使用已用过的成语
4. AI会自动参与接龙
5. 每成功接龙一次得1分

💡 使用示例：
/c start          # 随机生成开始成语
/c start 龙飞凤舞  # 指定开始成语（假设"舞"的拼音是wu）
然后输入：无微不至（因为"无"的拼音也是wu）
AI会自动接：至理名言
你再接：言而有信
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
            can_connect, connect_reason = self.can_jielong(
                game["current_chengyu"], message_text)
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
            )

            robot_success, robot_chengyu, robot_reason = await self.robot_jielong(message_text)
            if robot_success:
                # 检查机器人成语是否重复
                if robot_chengyu not in game["history"]:
                    game["current_chengyu"] = robot_chengyu
                    game["history"].append(robot_chengyu)
                    game["last_player"] = "ROBOT"

                    logger.info(f"🤖 机器人接龙成功: {robot_chengyu}")

                    yield event.plain_result(
                        f"🤖 机器人接龙：{robot_chengyu}\n"
                        f"👤 请接以拼音'{self.get_chengyu_info(robot_chengyu)[1]['last']}'开头的成语！\n"
                        f"📊 当前轮数：{len(game['history'])-1} 轮"
                    )
                else:
                    # 机器人重复了，用户获胜
                    yield event.plain_result(
                        f"🎉 恭喜！机器人想到的成语'{robot_chengyu}'重复了！\n"
                        f"👑 {user_name} 获得胜利！\n"
                        f"📊 游戏结束，使用 /c stop 保存记录"
                    )
            else:
                # 机器人接龙失败，用户获胜
                yield event.plain_result(
                    f"🎉 恭喜！机器人接龙失败了！\n"
                    f"👑 {user_name} 获得胜利！\n"
                    f"🤖 机器人说：{robot_reason}\n"
                    f"📊 游戏结束，使用 /c stop 保存记录"
                )

        except Exception as e:
            logger.error(f"处理成语输入失败: {e}")

    async def terminate(self):
        """插件终止时的清理工作"""
        try:
            self.save_data()
            # 关闭数据库连接
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'conn'):
                self.conn.close()
            logger.info("🔗 成语接龙插件 v2.0 已终止")
        except Exception as e:
            logger.error(f"插件终止时出错: {e}")

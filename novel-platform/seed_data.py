"""种子数据 — 生成大量数据用于 JMeter 压力测试

运行方式：python seed_data.py

说明：
  - 创建 50 个测试用户（test_001 ~ test_050）
  - 创建 200 本小说（覆盖 8 个分类）
  - 每本小说 10~30 个章节，每章约 500~2000 字
  - 随机生成评论和收藏

生成完毕后可用以下账号登录：
  用户名: test_001 ~ test_050
  密码:   123456
"""

import random
import sys
import os

# 确保能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Novel, Chapter, Comment, Favorite
from app.utils import hash_password

app = create_app()

# ── 数据池 ──────────────────────────────────────────────

CATEGORIES = [
    "玄幻", "仙侠", "都市", "言情",
    "历史", "科幻", "悬疑", "游戏",
]

CHAPTER_TITLES = [
    "楔子", "初入江湖", "意外相遇", "暗流涌动", "风云突变",
    "真相大白", "绝处逢生", "峰回路转", "决战前夕", "大结局",
    "新的开始", "旧日回忆", "神秘来客", "危机四伏", "暗中调查",
    "冲出重围", "天降奇缘", "生死考验", "宿命对决", "归途",
    "远古传说", "秘境探险", "强者为尊", "一念之差", "破茧成蝶",
    "步步惊心", "恩怨情仇", "天道酬勤", "终章", "后记",
]

NOVEL_TEMPLATES = [
    ("{}之逆天改命", "一个平凡少年在{}的世界中，凭借不屈的意志和过人的智慧，一步步踏上巅峰的传奇故事。"),
    ("{}风云录", "{}世界风云变幻，各大势力明争暗斗，一个意外卷入其中的小人物，将如何搅动这潭深水？"),
    ("{}：绝世强者", "他曾是{}世界的最强者，却因一场阴谋重生回少年时代。这一次，他要守护所有珍视之人。"),
    ("{}传奇", "在{}的世界里，有一种传说叫做奇迹。而他，就是那个创造奇迹的人。"),
    ("{}之永恒传说", "当{}的世界面临前所未有的危机，一个被命运选中的少年站了出来，开启了永恒的传说。"),
]

CONTENT_TEMPLATES = """{}。

{}。天色渐晚，远处的天际泛着一抹残红。

他深吸一口气，心中暗自思忖：{}

就在这时，一阵脚步声从远处传来。{}

"来了吗？"他低声自语，眼中闪过一丝坚定。

无论是福是祸，既然已经走到这一步，就没有回头的道理。

{}。

风吹过，卷起地上的落叶，在空中打着旋儿。他知道，从这一刻起，一切都将不同。"""

CONTENT_FILLERS = [
    "这是一个寻常的日子，阳光正好，微风不燥",
    "没有人知道接下来会发生什么，就连他自己也不确定",
    "空气中弥漫着一股紧张的气息，仿佛暴风雨前的宁静",
    "过去的种种在脑海中闪过，如同走马灯一般",
    "他握紧了手中的武器，目光如炬，直视前方",
    "命运的齿轮已经开始转动，再也无法停下",
    "世间万物都有其规律，而打破规律的人，注定不凡",
    "这一战，不仅关乎个人荣辱，更牵动着无数人的命运",
]

CONTENT_MIDDLES = [
    "这一路走来，虽然有惊无险，但每一步都如履薄冰。",
    "无论是敌是友，此刻都不重要了，重要的是如何应对眼前的局面。",
    "实力才是这个世界的通行证，没有实力，一切都是空谈。",
    "他比任何人都清楚，接下来的每一步都至关重要。",
]

CONTENT_SPEECHES = [
    "无论你是谁，挡我路者，皆为敌人！",
    "我等这一天已经很久了，来吧！",
    "你以为我会退缩吗？不，这才刚刚开始。",
    "命运从来不会眷顾弱者，而我已经不再是弱者了。",
    "这一战，不是你死，就是我亡！",
]

CONTENT_ENDINGS = [
    "无论如何，他已经做好了准备，迎接即将到来的一切",
    "新的篇章即将开启，而他已经不再是当初那个懵懂少年",
    "路漫漫其修远兮，吾将上下而求索",
    "一切才刚刚开始，而他已经迈出了最关键的一步",
    "前方的路虽然未知，但他相信，只要坚持，就一定能看到曙光",
]


def generate_chapter_content(chapter_num: int, total_chapters: int) -> str:
    """生成一章内容（500~2000 字）"""
    parts = []
    for _ in range(random.randint(3, 8)):
        filler = random.choice(CONTENT_FILLERS)
        middle = random.choice(CONTENT_MIDDLES)
        speech = random.choice(CONTENT_SPEECHES)
        ending = random.choice(CONTENT_ENDINGS)
        part = CONTENT_TEMPLATES.format(filler, middle, speech, middle, ending)
        parts.append(part)
    content = "\n\n".join(parts)

    # 调节长度
    target_len = random.randint(500, 2000)
    while len(content) < target_len:
        extra = random.choice(CONTENT_FILLERS) + "。" + random.choice(CONTENT_MIDDLES)
        content += "\n\n" + extra
    if len(content) > 3000:
        content = content[:3000]

    return content


def seed():
    """主流程：生成种子数据"""
    with app.app_context():
        print("[INFO] 正在清空旧数据...")
        # 按依赖顺序删除
        Favorite.query.delete()
        Comment.query.delete()
        Chapter.query.delete()
        Novel.query.delete()
        User.query.delete()
        db.session.commit()

        # ── 1. 创建用户 ──
        print("[INFO] 创建用户...")
        users = []
        for i in range(1, 51):
            u = User(
                username=f"test_{i:03d}",
                password_hash=hash_password("123456"),
                email=f"test_{i:03d}@example.com",
            )
            users.append(u)
        db.session.add_all(users)
        db.session.commit()
        print(f"  [OK] 已创建 {len(users)} 个用户(密码: 123456)")

        # ── 2. 创建小说 ──
        print("[INFO] 创建小说...")
        novels = []
        for i in range(1, 201):
            category = random.choice(CATEGORIES)
            tmpl_name, tmpl_desc = random.choice(NOVEL_TEMPLATES)
            title = tmpl_name.format(category) + f"-{i}"
            description = tmpl_desc.format(category)
            author = random.choice(users)
            novel = Novel(
                title=title,
                author_id=author.id,
                description=description,
                category=category,
                status="published",
                word_count=0,
            )
            novels.append(novel)
        db.session.add_all(novels)
        db.session.commit()
        print(f"  [OK] 已创建 {len(novels)} 本小说")

        # ── 3. 创建章节 ──
        print("[INFO] 创建章节（这可能需要一些时间）...")
        chapter_count = 0
        for novel in novels:
            num_chapters = random.randint(10, 30)
            for ch in range(1, num_chapters + 1):
                title = random.choice(CHAPTER_TITLES)
                if ch == 1:
                    title = "第一章 " + title
                elif ch == num_chapters:
                    title = "第{}章 ".format(ch) + random.choice(["大结局", "终章", "后记"])
                else:
                    title = "第{}章 ".format(ch) + title

                content = generate_chapter_content(ch, num_chapters)
                wc = len(content.replace(" ", "").replace("\n", ""))
                chapter = Chapter(
                    novel_id=novel.id,
                    title=title,
                    content=content,
                    chapter_number=ch,
                    word_count=wc,
                )
                db.session.add(chapter)
                novel.word_count = (novel.word_count or 0) + wc
                chapter_count += 1

            # 每 20 本批量提交一次
            if novels.index(novel) % 20 == 0:
                db.session.commit()
                print(f"  ... 已创建约 {chapter_count} 个章节")

        db.session.commit()
        print(f"  [OK] 已创建 {chapter_count} 个章节")

        # ── 4. 创建评论 ──
        print("[INFO] 创建评论...")
        comment_count = 0
        chapters = Chapter.query.all()
        for _ in range(3000):
            user = random.choice(users)
            chapter = random.choice(chapters)
            novel_id = chapter.novel_id
            comment = Comment(
                user_id=user.id,
                novel_id=novel_id,
                chapter_id=chapter.id,
                content=random.choice([
                    "写得真好！期待更新！",
                    "加油，作者大大！",
                    "这个情节太精彩了！",
                    "每天都来追更，赞一个！",
                    "人物刻画很到位，喜欢！",
                    "有些地方可以再详细一点~",
                    "这一章信息量很大啊！",
                    "作者辛苦了，支持！",
                    "感觉剧情要高潮了！",
                    "文笔很好，故事引人入胜！",
                    "什么时候更新下一章啊？",
                    "这个设定很有意思！",
                    "一口气看完，太爽了！",
                    "强烈推荐！值得一看！",
                    "有些悬念设置得很巧妙！",
                ]),
            )
            db.session.add(comment)
            comment_count += 1
            if comment_count % 500 == 0:
                db.session.commit()
                print(f"  ... 已创建 {comment_count} 条评论")

        db.session.commit()
        print(f"  [OK] 已创建 {comment_count} 条评论")

        # ── 5. 创建收藏 ──
        print("[INFO] 创建收藏...")
        fav_count = 0
        for user in users:
            # 每人收藏 5~20 本
            sample = random.sample(novels, random.randint(5, 20))
            for novel in sample:
                fav = Favorite(user_id=user.id, novel_id=novel.id)
                db.session.add(fav)
                fav_count += 1
        db.session.commit()
        print(f"  [OK] 已创建 {fav_count} 条收藏")

        print("\n" + "=" * 50)
        print(" 种子数据生成完毕！")
        print("=" * 50)
        print(f"  用户:    {len(users)}")
        print(f"  小说:    {len(novels)}")
        print(f"  章节:    {chapter_count}")
        print(f"  评论:    {comment_count}")
        print(f"  收藏:    {fav_count}")
        print("=" * 50)
        print("  测试账号: test_001 ~ test_050")
        print("  密  码:  123456")
        print("=" * 50)


if __name__ == "__main__":
    seed()
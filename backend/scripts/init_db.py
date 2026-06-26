#!/usr/bin/env python3
"""
Database initialization script.

Usage:
    cd backend
    python scripts/init_db.py          # Create all tables
    python scripts/init_db.py --seed   # Create tables + insert sample data
"""
import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine, async_session
from app.models.session import Base
from app.models.message import Message  # noqa: F401
from app.models.session import Session  # noqa: F401


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] All tables created.")


async def seed_sample_data():
    """Insert 5 high-quality sample discussion sessions with guest lineups."""
    from datetime import datetime, timezone
    import json
    import uuid

    now = datetime.now(timezone.utc)

    # ── 5 Sample Sessions ──────────────────────────────────────
    samples = [
        {
            "id": str(uuid.uuid4()),
            "topic": "远程办公是否应该成为互联网公司的默认工作模式？",
            "guests": [
                {"id": "moderator", "name": "陈锐", "title": "资深商业主持人", "stance": "保持中立，引导深度讨论", "avatar": "🎤", "color": "#F59E0B"},
                {"id": "expert_0", "name": "张明远", "title": "组织行为学教授", "stance": "支持混合办公，强调数据驱动的管理决策", "avatar": "📚", "color": "#3B82F6"},
                {"id": "expert_1", "name": "李思涵", "title": "硅谷科技公司CTO", "stance": "远程先行者，认为办公室是过时的概念", "avatar": "💻", "color": "#10B981"},
                {"id": "expert_2", "name": "王晓峰", "title": "人力资源管理咨询合伙人", "stance": "关注员工心理健康与团队凝聚力，主张平衡", "avatar": "🧠", "color": "#EF4444"},
            ],
            "status": "completed",
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "topic": "AI 编码助手会取代初级程序员吗？",
            "guests": [
                {"id": "moderator", "name": "林悦", "title": "科技媒体主编", "stance": "客观呈现多方观点，追问关键分歧", "avatar": "🎤", "color": "#F59E0B"},
                {"id": "expert_0", "name": "赵鹏", "title": "AI 研究院首席科学家", "stance": "认为 AI 将重塑而非取代，程序员角色升维", "avatar": "🤖", "color": "#8B5CF6"},
                {"id": "expert_1", "name": "陈果", "title": "某大厂技术培训负责人", "stance": "初级岗位确实缩水，但复合型人才更稀缺", "avatar": "🎓", "color": "#06B6D4"},
                {"id": "expert_2", "name": "刘洋", "title": "独立开发者 & 技术博主", "stance": "用 AI 一人生产力已超过小团队，门槛正在消失", "avatar": "🛠️", "color": "#EC4899"},
            ],
            "status": "completed",
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "topic": "中国新能源汽车品牌的全球化战略：机遇还是陷阱？",
            "guests": [
                {"id": "moderator", "name": "周庭", "title": "财经频道首席主持人", "stance": "中立，以数据和案例引导嘉宾交锋", "avatar": "🎤", "color": "#F59E0B"},
                {"id": "expert_0", "name": "秦风", "title": "汽车产业战略分析师", "stance": "出海是必然选择，但需警惕地缘政治风险", "avatar": "🚗", "color": "#3B82F6"},
                {"id": "expert_1", "name": "苏敏", "title": "国际贸易法合伙人", "stance": "欧盟反补贴调查只是开始，合规成本将飙升", "avatar": "⚖️", "color": "#EF4444"},
                {"id": "expert_2", "name": "何志远", "title": "新能源车企海外事业部VP", "stance": "一线实战经验表明，品牌信任建立比技术输出更难", "avatar": "🌍", "color": "#10B981"},
            ],
            "status": "completed",
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "topic": "35岁真的是程序员的职业终点吗？",
            "guests": [
                {"id": "moderator", "name": "方雅", "title": "职场播客主持人", "stance": "以同理心引导讨论，关注人的故事", "avatar": "🎤", "color": "#F59E0B"},
                {"id": "expert_0", "name": "黄志强", "title": "某头部互联网公司HRD", "stance": "年龄焦虑被夸大，企业真正淘汰的是不愿成长的人", "avatar": "👔", "color": "#3B82F6"},
                {"id": "expert_1", "name": "马骁", "title": "42岁转行成功的资深架构师", "stance": "亲身经历证明技术深度+行业认知远胜年龄标签", "avatar": "🏛️", "color": "#F59E0B"},
                {"id": "expert_2", "name": "吴瑾", "title": "职业规划与生涯教育专家", "stance": "问题不在35岁而在25-35岁期间是否有意识构建能力护城河", "avatar": "🧭", "color": "#8B5CF6"},
            ],
            "status": "completed",
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "topic": "开源模型 vs 闭源模型：AI 发展的两条道路谁能胜出？",
            "guests": [
                {"id": "moderator", "name": "韩冰", "title": "深度科技评论员", "stance": "中立但犀利，拒绝和稀泥式结论", "avatar": "🎤", "color": "#F59E0B"},
                {"id": "expert_0", "name": "郑凯", "title": "开源 AI 基金会技术负责人", "stance": "开源是唯一能避免 AI 被巨头垄断的道路", "avatar": "🐧", "color": "#10B981"},
                {"id": "expert_1", "name": "沈楠", "title": "闭源大模型公司产品VP", "stance": "闭源才能保证安全、性能与商业可持续性", "avatar": "🔒", "color": "#3B82F6"},
                {"id": "expert_2", "name": "丁然", "title": "AI 安全与对齐研究员", "stance": "无论开源闭源，安全对齐是共同的底线", "avatar": "🛡️", "color": "#EF4444"},
            ],
            "status": "completed",
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
    ]

    async with async_session() as db:
        for s in samples:
            session = Session(
                id=s["id"],
                topic=s["topic"],
                guest_ids=json.dumps(s["guests"], ensure_ascii=False),
                status=s["status"],
                created_at=datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")),
                completed_at=datetime.fromisoformat(s["completed_at"].replace("Z", "+00:00")),
            )
            db.add(session)

        await db.commit()

    print(f"[OK] {len(samples)} sample sessions seeded.")
    for s in samples:
        names = [g["name"] for g in s["guests"][1:]]
        print(f"     📋 {s['topic'][:40]}...")
        print(f"        👥 {', '.join(names)}")


async def main():
    parser = argparse.ArgumentParser(description="AI Roundtable DB Init")
    parser.add_argument("--seed", action="store_true", help="Insert sample data after creating tables")
    args = parser.parse_args()

    await create_tables()

    if args.seed:
        await seed_sample_data()


if __name__ == "__main__":
    asyncio.run(main())

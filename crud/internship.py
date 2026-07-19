# crud/internship.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from models.internship import InternshipCategory, Internship


# ---------- 分类 ----------
async def get_categories(db: AsyncSession):
    """获取所有岗位分类"""
    stmt = select(InternshipCategory).order_by(InternshipCategory.id)
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------- 岗位列表 ----------
async def get_internship_list(
    db: AsyncSession,
    category_id: int | None = None,
    province: str | None = None,
    education: str | None = None,
    skip: int = 0,
    limit: int = 10,
):
    """多条件筛选岗位列表"""
    stmt = select(Internship)

    if category_id is not None:
        stmt = stmt.where(Internship.category_id == category_id)
    if province is not None:
        stmt = stmt.where(Internship.province == province)
    if education is not None and education.strip():
        if education == "专科":
            stmt = stmt.where(
                or_(
                    Internship.education == "专科及以上",
                    Internship.education == "本科及以上",
                    Internship.education == "硕士及以上",
                )
            )
        elif education == "本科":
            stmt = stmt.where(
                or_(
                    Internship.education == "本科及以上",
                    Internship.education == "硕士及以上",
                )
            )
        elif education == "硕士":
            stmt = stmt.where(Internship.education == "硕士及以上")

    stmt = stmt.order_by(Internship.publish_time.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_internship_count(
    db: AsyncSession,
    category_id: int | None = None,
    province: str | None = None,
    education: str | None = None,
) -> int:
    """获取符合筛选条件的总岗位数"""
    stmt = select(func.count(Internship.id))

    if category_id is not None:
        stmt = stmt.where(Internship.category_id == category_id)
    if province is not None:
        stmt = stmt.where(Internship.province == province)
    if education is not None and education.strip():
        if education == "专科":
            stmt = stmt.where(
                or_(
                    Internship.education == "专科及以上",
                    Internship.education == "本科及以上",
                    Internship.education == "硕士及以上",
                )
            )
        elif education == "本科":
            stmt = stmt.where(
                or_(
                    Internship.education == "本科及以上",
                    Internship.education == "硕士及以上",
                )
            )
        elif education == "硕士":
            stmt = stmt.where(Internship.education == "硕士及以上")

    result = await db.execute(stmt)
    return result.scalar_one()


# ---------- 岗位详情 ----------
async def get_internship_detail(db: AsyncSession, internship_id: int) -> Internship | None:
    stmt = select(Internship).where(Internship.id == internship_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increase_internship_views(db: AsyncSession, internship: Internship):
    """增加岗位浏览量"""
    internship.views += 1
    await db.commit()


# ---------- 相关推荐 ----------
async def get_related_internships(
    db: AsyncSession,
    current_id: int,
    category_id: int | None,
    limit: int = 5,
):
    """获取同类岗位推荐（按浏览量和发布时间排序）"""
    stmt = select(Internship).where(Internship.id != current_id)

    if category_id is not None:
        stmt = stmt.where(Internship.category_id == category_id)

    stmt = stmt.order_by(Internship.views.desc(), Internship.publish_time.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
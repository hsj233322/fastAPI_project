import csv
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base
from models.internship import Internship, InternshipCategory

DATABASE_URL = "mysql+aiomysql://myuser:123456@localhost:3306/internship_app?charset=utf8mb4"

CATEGORY_KEYWORDS = [
    ("技术开发", ["工程师", "开发", "软件", "后端", "前端", "编程", "代码", "Java", "Python", "Go", "C++", ".NET", "Node", "React", "Vue", "iOS", "Android", "客户端", "全栈"]),
    ("数据分析", ["数据", "算法", "统计", "BI", "数据分析师", "数据挖掘", "数据标注", "机器学习", "深度学习", "AI", "人工智能"]),
    ("测试运维", ["测试", "QA", "自动化", "运维", "DevOps", "SRE", "网络安全", "安全测试", "渗透测试"]),
    ("产品设计", ["产品", "设计", "UI", "UX", "交互", "视觉", "美工", "原型", "服装设计"]),
    ("运营市场", ["运营", "市场", "营销", "销售", "推广", "电商", "新媒体", "内容", "直播", "客服"]),
    ("职能管理", ["管理", "管培生", "行政", "人力", "HR", "财务", "会计", "助理", "文员", "内勤"]),
    ("教育培训", ["教育", "培训", "教师", "讲师", "教辅", "编辑", "教研"]),
    ("金融投资", ["金融", "银行", "证券", "投资", "基金", "保险", "理财"]),
    ("房地产", ["房产", "物业", "建筑", "施工", "房屋", "地产", "工程"]),
    ("医疗健康", ["医疗", "医院", "医生", "护士", "健康", "制药", "生物"]),
    ("制造加工", ["机械", "制造", "生产", "工艺", "模具", "装配", "质检"]),
]

def classify_position(title: str) -> str:
    for category_name, keywords in CATEGORY_KEYWORDS:
        if any(keyword in title for keyword in keywords):
            return category_name
    return "其他"

def parse_salary(salary_str: str):
    if not salary_str or salary_str == "-":
        return None, None
    parts = salary_str.split("-")
    if len(parts) == 2:
        try:
            return int(float(parts[0])), int(float(parts[1]))
        except ValueError:
            return None, None
    return None, None

def parse_headcount(count_str: str):
    if not count_str or count_str == "-":
        return 0
    try:
        return int(count_str)
    except ValueError:
        return 0

def parse_datetime(dt_str: str):
    if not dt_str:
        return datetime.now()
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d")
        except ValueError:
            return datetime.now()

async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("数据库表已创建")
    
    async with async_session() as db:
        categories = {}
        for name, _ in CATEGORY_KEYWORDS:
            existing = await db.execute(
                InternshipCategory.__table__.select().where(InternshipCategory.category_name == name)
            )
            cat = existing.scalar_one_or_none()
            if not cat:
                cat = InternshipCategory(category_name=name, sort_order=len(categories))
                db.add(cat)
                await db.flush()
            categories[name] = cat.id
        
        other_cat = await db.execute(
            InternshipCategory.__table__.select().where(InternshipCategory.category_name == "其他")
        )
        other_cat = other_cat.scalar_one_or_none()
        if not other_cat:
            other_cat = InternshipCategory(category_name="其他", sort_order=len(categories))
            db.add(other_cat)
            await db.flush()
        categories["其他"] = other_cat.id
        
        await db.commit()
        print(f"已创建 {len(categories)} 个分类")
    
    async with async_session() as db:
        with open('ncss_intern_jobs_20260718_120440.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            inserted = 0
            skipped = 0
            
            for row in reader:
                position_id = row['职位ID'].strip()
                
                existing = await db.execute(
                    Internship.__table__.select().where(Internship.position_id == position_id)
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue
                
                title = row['岗位名称'].strip()
                category_name = classify_position(title)
                category_id = categories.get(category_name, categories["其他"])
                
                salary_min, salary_max = parse_salary(row['月薪范围(k)'])
                headcount = parse_headcount(row['招聘人数'])
                publish_time = parse_datetime(row['发布时间'])
                
                internship = Internship(
                    position_id=position_id,
                    title=title,
                    company_name=row['单位名称'].strip(),
                    province=row['省份'].strip(),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    headcount=headcount,
                    education=row['学历要求'].strip() if row['学历要求'].strip() else None,
                    major=row['专业要求'].strip() if row['专业要求'].strip() else None,
                    company_type=row['单位性质'].strip() if row['单位性质'].strip() else None,
                    company_scale=row['单位规模'].strip() if row['单位规模'].strip() else None,
                    tags=row['福利标签'].strip() if row['福利标签'].strip() else None,
                    description=None,
                    views=0,
                    publish_time=publish_time,
                    category_id=category_id,
                )
                db.add(internship)
                inserted += 1
                
                if inserted % 50 == 0:
                    await db.commit()
                    print(f"已插入 {inserted} 条数据")
            
            await db.commit()
            print(f"\n数据导入完成！")
            print(f"插入: {inserted} 条")
            print(f"跳过（重复）: {skipped} 条")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
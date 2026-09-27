from database import engine
from models import Base

# 删除所有表并重建（会清空数据）
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print("数据库重建完成！")
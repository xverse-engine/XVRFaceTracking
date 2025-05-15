
## 如果现在alembicw文件夹不存在，需要先创建一个，就必须执行 alembic init
# alembic init /shared_data/alembic

## 如果为了自动做初始化，丢弃之前所有的改动，则可以用 revision
# alembic revision --autogenerate -m "Initial migration"

## 如果db的修改 和 alembic/version 中的修改不同，就会导致alembic操作异常。最简单的办法，是删除alembic_version 这个表. sqlite比较简单，手动操作也ok


# 这个操作的问题在于，历史的操作记录会被全部清空，但是数据库本身还在。如果出现了：ERROR [alembic.util.messaging] Can't locate revision identified by 'xxxxx' 的报错，可以执行一下
# python /app/app/db/del_alembic_version.py

# # Let the DB start
# python /app/app/db/backend_pre_start.py

# # Run migrations
# alembic upgrade head

# # Create initial data in DB
# python /app/app/db/initial_data.py


python3 /app/app/main.py
<div align="center">
    <img src="http://47.94.172.250:33334/static/frontend/head_portrait/logo@2x.png?t=1542252961.100895" width="150px">
    <br>
    <strong>LuffyBackend</strong>
</div>

# 开发环境

* Python (3.6.2)
* Django (1.11.18)
* Mysql (5.6)
* Redis (4.0)

## 使用虚拟环境(virturalenv)

```
pip3 install virtualenv

virtualenv env
source env/bin/activate

pip install -r requirements.txt

```

## 建库语句

```sql
CREATE database luffy_play DEFAULT charset utf8 COLLATE utf8_general_ci;
```

## 启动项目

```
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动
python manage.py runserver 0.0.0.0:8000
```

## 导入数据

```

为你准备了脱敏数据 `init.sql`

$ mysql -uUSERNAME -pPASSWORD luffy_play < SQLPATH

```

## 常见问题




import hashlib

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, Group, PermissionsMixin,
)
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe


class CourseCategory(models.Model):
    """课程大类, e.g 前端  后端..."""
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = "课程大类"
        verbose_name_plural = "课程大类"


class CourseSubCategory(models.Model):
    """课程子类, e.g python linux """
    category = models.ForeignKey("CourseCategory")
    name = models.CharField(max_length=64, unique=True, verbose_name="课程子类")
    hide = models.BooleanField("是否隐藏", default=False, help_text="打对勾️即隐藏")

    def __str__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = "课程子类"
        verbose_name_plural = "课程子类"


class DegreeCourse(models.Model):
    """学位课程"""
    name = models.CharField(max_length=128, unique=True, verbose_name="学位课程")
    course_img = models.CharField(max_length=255, verbose_name="缩略图")
    brief = models.TextField(verbose_name="学位课程简介", )
    level_choices = ((0, '初级'), (1, '中级'), (2, '高级'))
    level = models.SmallIntegerField(choices=level_choices, default=1)
    total_scholarship = models.PositiveIntegerField(verbose_name="总奖学金(贝里)", default=40000)
    # homework_scholarship = models.PositiveIntegerField(verbose_name="作业奖学金(贝里)", default=30000)
    # cycle_scholarship = models.PositiveIntegerField(verbose_name="周期奖学金(贝里)", default=10000)
    mentor_compensation_bonus = models.PositiveIntegerField(verbose_name="本课程的导师辅导费用(贝里)", default=15000)
    period = models.PositiveIntegerField(verbose_name="建议学习周期(days)", default=150)  # 为了计算学位奖学金
    prerequisite = models.TextField(verbose_name="课程先修要求", max_length=1024)
    course_type_choices = ((0, '学位课程'), (1, '面授同步班'),)
    course_type = models.SmallIntegerField(choices=course_type_choices)
    teachers = models.ManyToManyField("Teacher", verbose_name="课程讲师")

    degreecourse_price_policy = GenericRelation("PricePolicy")
    order_details = GenericRelation("OrderDetail", related_name="degree_course", )

    def __str__(self):
        return self.name


class Scholarship(models.Model):
    """学位课程奖学金"""
    degree_course = models.ForeignKey("DegreeCourse")
    time_percent = models.PositiveSmallIntegerField(verbose_name="奖励档位(时间百分比)", help_text="只填百分值，如80,代表80%")
    value = models.PositiveIntegerField(verbose_name="奖学金数额")

    def __str__(self):
        return "%s:%s" % (self.degree_course, self.value)


class Course(models.Model):
    """课程"""
    name = models.CharField(max_length=128, unique=True, verbose_name="模块")
    course_img = models.CharField(max_length=255)
    sub_category = models.ForeignKey("CourseSubCategory")
    course_type_choices = ((0, '付费'), (1, 'VIP专享'), (2, '学位课程'))
    course_type = models.SmallIntegerField(choices=course_type_choices)
    degree_course = models.ForeignKey("DegreeCourse", blank=True, null=True, help_text="若是学位课程，此处关联学位表")
    brief = models.TextField(verbose_name="课程概述", max_length=2048)
    # outline = models.TextField(verbose_name="课程大纲")
    level_choices = ((0, '初级'), (1, '中级'), (2, '高级'))
    level = models.SmallIntegerField(choices=level_choices, default=1)
    pub_date = models.DateField(verbose_name="发布日期", blank=True, null=True)
    period = models.PositiveIntegerField(verbose_name="建议学习周期(days)", default=7)
    order = models.IntegerField("课程顺序", help_text="从上一个课程数字往后排")
    attachment_path = models.CharField(max_length=128, verbose_name="课件路径", blank=True, null=True)
    status_choices = ((0, '上线'), (1, '下线'), (2, '预上线'))
    status = models.SmallIntegerField(choices=status_choices, default=0)
    template_id = models.SmallIntegerField("前端模板id", default=1)

    order_details = GenericRelation("OrderDetail", related_query_name="course")
    price_policy = GenericRelation("PricePolicy")  # 用于GenericForeignKey反向查询，不会生成表字段，切勿删除，如有疑问请联系老村长

    def __str__(self):
        return "%s(%s)" % (self.name, self.get_course_type_display())

    def save(self, *args, **kwargs):
        if self.course_type == 2:
            if not self.degree_course:
                raise ValueError("学位课程必须关联对应的学位表")
        super(Course, self).save(*args, **kwargs)


class CourseDetail(models.Model):
    """课程详情页内容"""
    course = models.OneToOneField("Course")
    course_img = models.CharField(max_length=255, verbose_name="课程详情展示图(推荐课程)", null=True, blank=True)
    pc_cover = models.CharField(max_length=255, verbose_name="PC列表封面图", blank=True, null=True)
    h5_cover = models.CharField(max_length=255, verbose_name="M站列表封面图", blank=True, null=True)
    hours = models.IntegerField("课时", help_text="共多少小时")
    numbers = models.PositiveSmallIntegerField("课时数", help_text="共多少个课时")
    course_slogan = models.CharField(max_length=125, blank=True, null=True)
    video_brief_link = models.CharField(max_length=255, blank=True, null=True)
    pc_content = models.TextField(verbose_name="PC详情介绍", help_text="放置html元素", blank=True, null=True)
    h5_content = models.TextField(verbose_name="H5详情介绍", help_text="放置html元素", blank=True, null=True)
    why_study = models.TextField(verbose_name="为什么学习这门课程")
    what_to_study_brief = models.TextField(verbose_name="我将学到哪些内容")
    career_improvement = models.TextField(verbose_name="此项目如何有助于我的职业生涯")
    prerequisite = models.TextField(verbose_name="课程先修要求", max_length=1024)
    teacher = models.ForeignKey("Teacher", verbose_name="课程讲师")

    def __str__(self):
        return "%s" % self.course


class CourseOutline(models.Model):
    """课程大纲"""
    course_detail = models.ForeignKey("CourseDetail")
    title = models.CharField(max_length=128)
    order = models.PositiveSmallIntegerField(default=1)
    # 前端显示顺序

    content = models.TextField("内容", max_length=2048)

    def __str__(self):
        return "%s" % self.title

    class Meta:
        unique_together = ('course_detail', 'title')


class CourseChapter(models.Model):
    """课程章节"""
    course = models.ForeignKey("Course", related_name='coursechapters')
    chapter = models.SmallIntegerField(verbose_name="第几章", default=1)
    name = models.CharField(max_length=128)
    summary = models.TextField(verbose_name="章节介绍", blank=True, null=True)
    is_create = models.BooleanField(verbose_name="是否创建题库进度", default=True)
    pub_date = models.DateField(verbose_name="发布日期", auto_now_add=True)

    class Meta:
        unique_together = ("course", 'chapter')
        ordering = ["chapter", ]

    def __str__(self):
        return "%s:(第%s章)%s" % (self.course, self.chapter, self.name)


class Teacher(models.Model):
    """讲师、导师表"""
    name = models.CharField(max_length=32)
    role_choices = ((0, '讲师'), (1, '导师'))
    role = models.SmallIntegerField(choices=role_choices, default=0)
    title = models.CharField(max_length=64, verbose_name="职位、职称")
    signature = models.CharField(max_length=255, help_text="导师签名", blank=True, null=True)
    image = models.CharField(max_length=128)
    brief = models.TextField(max_length=1024)

    def __str__(self):
        return self.name


class PricePolicy(models.Model):
    """价格与有课程效期表"""
    content_type = models.ForeignKey(ContentType)  # 关联course or degree_course
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # course = models.ForeignKey("Course")
    valid_period_choices = ((1, '1天'), (3, '3天'),
                            (7, '1周'), (14, '2周'),
                            (30, '1个月'),
                            (60, '2个月'),
                            (90, '3个月'),
                            (120, '4个月'),
                            (180, '6个月'), (210, '12个月'),
                            (540, '18个月'), (720, '24个月'),
                            (722, '24个月'), (723, '24个月'),
                            (10000, '永久有效'),
                            )
    valid_period = models.SmallIntegerField(choices=valid_period_choices)
    price = models.FloatField()
    used = models.BooleanField(default=False, verbose_name="是否使用")  # 是否启用该套课程价格

    class Meta:
        unique_together = ("content_type", 'object_id', "valid_period")

    def __str__(self):
        return "%s(%s)%s" % (self.content_object, self.get_valid_period_display(), self.price)


class CourseSection(models.Model):
    """课时目录"""
    chapter = models.ForeignKey("CourseChapter", related_name='coursesections')
    name = models.CharField(max_length=128)
    order = models.PositiveSmallIntegerField(verbose_name="课时排序", help_text="建议每个课时之间空1至2个值，以备后续插入课时")
    section_type_choices = ((0, '文档'), (1, '练习'), (2, '视频'))
    section_type = models.SmallIntegerField(default=2, choices=section_type_choices)
    section_link = models.CharField(max_length=255, blank=True, null=True, help_text="若是video，填vid,若是文档，填link")
    video_time = models.CharField(verbose_name="视频时长", blank=True, null=True, max_length=32)  # 仅在前端展示使用
    pub_date = models.DateTimeField(verbose_name="发布时间", auto_now_add=True)
    free_trail = models.BooleanField("是否可试看", default=False)
    is_flash = models.BooleanField(verbose_name="是否使用FLASH播放", default=False)
    player_choices = ((0, "CC"), (1, "POLYV"), (2, "ALI"))
    player = models.SmallIntegerField(choices=player_choices, default=1, help_text="视频播放器选择")

    def course_chapter(self):
        return self.chapter.chapter

    def course_name(self):
        return self.chapter.course.name

    class Meta:
        unique_together = ('chapter', 'section_link')
        ordering = ["order", ]

    def __str__(self):
        return "%s-%s" % (self.chapter, self.name)


class Homework(models.Model):
    chapter = models.ForeignKey("CourseChapter")
    title = models.CharField(max_length=128, verbose_name="作业题目")
    order = models.PositiveSmallIntegerField("作业顺序", help_text="同一课程的每个作业之前的order值间隔1-2个数")
    homework_type_choices = ((0, '作业'), (1, '模块通关考核'))
    homework_type = models.SmallIntegerField(choices=homework_type_choices, default=0)
    requirement = models.TextField(verbose_name="作业需求")
    threshold = models.TextField(max_length=1024, verbose_name="踩分点")
    recommend_period = models.PositiveSmallIntegerField("推荐完成周期(天)", default=7)
    scholarship_value = models.PositiveSmallIntegerField("为该作业分配的奖学金(贝里)")
    note = models.TextField(blank=True, null=True)
    enabled = models.BooleanField(default=True, help_text="本作业如果后期不需要了，不想让学员看到，可以设置为False")

    class Meta:
        unique_together = ("chapter", "title")

    def __str__(self):
        return "%s - %s" % (self.chapter, self.title)


class CourseSchedule(models.Model):
    """课程进度计划表,针对学位课程，每开通一个模块，就为这个学员生成这个模块的推荐学习计划表，后面的奖惩均按此表进行"""
    study_record = models.ForeignKey("StudyRecord")
    homework = models.ForeignKey("Homework")
    recommend_date = models.DateTimeField("推荐交作业日期")

    def __str__(self):
        return "%s - %s - %s " % (self.study_record, self.homework, self.recommend_date)

    class Meta:
        unique_together = ('study_record', 'homework')


class EnrolledCourse(models.Model):
    """已报名课程,不包括学位课程"""
    account = models.ForeignKey("Account")
    course = models.ForeignKey("Course", limit_choices_to=~Q(course_type=2))
    enrolled_date = models.DateTimeField(auto_now_add=True)
    valid_begin_date = models.DateField(verbose_name="有效期开始自")
    valid_end_date = models.DateField(verbose_name="有效期结束至")
    status_choices = ((0, '已开通'), (1, '已过期'))
    status = models.SmallIntegerField(choices=status_choices, default=0)
    order_detail = models.OneToOneField("OrderDetail")  # 使订单购买后支持 课程评价

    # order = models.ForeignKey("Order",blank=True,null=True)

    def __str__(self):
        return "%s:%s" % (self.account, self.course)

        # class Meta: 一个课程到期了，可以重新购买，所以不能联合唯一
        #     unique_together = ('account', 'course')


class DegreeRegistrationForm(models.Model):
    """学位课程报名表"""
    enrolled_degree = models.OneToOneField("EnrolledDegreeCourse")
    current_company = models.CharField(max_length=64, null=True)
    current_position = models.CharField(max_length=64, null=True)
    current_salary = models.IntegerField(null=True)
    work_experience_choices = ((0, "应届生"),
                               (1, "1年"),
                               (2, "2年"),
                               (3, "3年"),
                               (4, "4年"),
                               (5, "5年"),
                               (6, "6年"),
                               (7, "7年"),
                               (8, "8年"),
                               (9, "9年"),
                               (10, "10年"),
                               (11, "超过10年"),
                               )
    work_experience = models.IntegerField(null=True)
    open_module = models.BooleanField("是否开通第1模块", default=True)
    stu_specified_mentor = models.CharField("学员自行指定的导师名", max_length=32, blank=True, null=True)
    study_plan_choices = ((0, "1-2小时/天"),
                          (1, "2-3小时/天"),
                          (2, "3-5小时/天"),
                          (3, "5小时+/天"),
                          )
    study_plan = models.SmallIntegerField(choices=study_plan_choices, default=1)
    why_take_this_course = models.TextField("报此课程原因", max_length=1024, null=True)
    why_choose_us = models.TextField("为何选路飞", max_length=1024, null=True)
    your_expectation = models.TextField("你的期待", max_length=1024, null=True)
    hide = models.BooleanField("不在前端页面显示此条评价", default=False)
    memo = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "%s" % self.enrolled_degree


class EnrolledDegreeCourse(models.Model):
    """已报名的学位课程"""
    account = models.ForeignKey("Account")
    degree_course = models.ForeignKey("DegreeCourse")
    enrolled_date = models.DateTimeField(auto_now_add=True)
    service_period = models.PositiveSmallIntegerField(verbose_name="服务周期")
    valid_begin_date = models.DateField(verbose_name="有效期开始自", blank=True, null=True)  # 开通第一个模块时，再添加课程有效期，2年
    valid_end_date = models.DateField(verbose_name="有效期结束至", blank=True, null=True)
    status_choices = (
        (0, '在学中'),
        (1, '休学中'),
        (2, '已毕业'),
        (3, '超时结业'),
        (4, '报名成功(未开始学习)'),
        (5, '已放弃学习'),
        (6, '休学申请中'),
    )
    study_status = models.SmallIntegerField(choices=status_choices, default=4)
    mentor = models.ForeignKey("Account", verbose_name="导师", related_name='my_students',
                               blank=True, null=True, limit_choices_to={'role': 1})
    mentor_fee_balance = models.PositiveIntegerField("导师费用余额", help_text="这个学员的导师费用，每有惩罚，需在此字段同时扣除")
    order_detail = models.OneToOneField("OrderDetail")  # 使订单购买后支持填写报名表

    honor_choices = (
        (0, "优秀学员"),
        (1, "结业学员"),
        # (2, "优秀组长"),
    )
    honor = models.SmallIntegerField(choices=honor_choices, blank=True, null=True, verbose_name="学员荣誉职称")
    # grade = models.ForeignKey("Grade", verbose_name="分配的班级", blank=True, null=True)
    # group = models.ForeignKey("GradeGroup", verbose_name="分配的小组", blank=True, null=True)

    def __str__(self):
        return "%s:%s" % (self.account, self.degree_course)

    class Meta:
        unique_together = ('account', 'degree_course')


class Order(models.Model):
    """订单"""
    payment_type_choices = ((0, '微信'), (1, '支付宝'), (2, '优惠码'), (3, '贝里'), (4, '银联'))
    payment_type = models.SmallIntegerField(choices=payment_type_choices)
    payment_number = models.CharField(max_length=128, verbose_name="支付第3方订单号", null=True, blank=True)
    order_number = models.CharField(max_length=128, verbose_name="订单号", unique=True)  # 考虑到订单合并支付的问题
    account = models.ForeignKey("Account")
    actual_amount = models.FloatField(verbose_name="实付金额")
    status_choices = ((0, '交易成功'), (1, '待支付'), (2, '退费申请中'), (3, '已退费'), (4, '主动取消'), (5, '超时取消'))
    status = models.SmallIntegerField(choices=status_choices, verbose_name="状态")
    order_type_choices = ((0, '用户下单'), (1, '线下班创建'),)
    order_type = models.SmallIntegerField(choices=order_type_choices, default=0, verbose_name="订单类型")
    date = models.DateTimeField(auto_now_add=True, verbose_name="订单生成时间")
    pay_time = models.DateTimeField(blank=True, null=True, verbose_name="付款时间")
    cancel_time = models.DateTimeField(blank=True, null=True, verbose_name="订单取消时间")
    memo = models.CharField(max_length=255, null=True, blank=True, help_text="存储`json`格式")

    def __str__(self):
        return "%s" % self.order_number


class OrderDetail(models.Model):
    """订单详情"""
    order = models.ForeignKey("Order")
    content_type = models.ForeignKey(ContentType)  # 可关联普通课程或学位
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    original_price = models.FloatField("课程原价")
    price = models.FloatField("折后价格")
    content = models.CharField(max_length=255, blank=True, null=True)  # ？
    valid_period_display = models.CharField("有效期显示", max_length=32)  # 在订单页显示
    valid_period = models.PositiveIntegerField("有效期(days)")  # 课程有效期
    memo = models.CharField(max_length=255, blank=True, null=True)

    # def __str__(self):
    #     return "%s - %s - %s" % (self.order, self.content_type, self.price)

    class Meta:
        # unique_together = ("order", 'course')
        unique_together = ("order", 'content_type', 'object_id')


class StudyRecord(models.Model):
    """学位课程的模块学习进度
       报名学位课程后，每个模块会立刻生成一条学习纪录
    """
    enrolled_degree_course = models.ForeignKey("EnrolledDegreeCourse")
    course_module = models.ForeignKey("Course", verbose_name="学位模块", limit_choices_to={'course_type': 2})
    open_date = models.DateField(blank=True, null=True, verbose_name="开通日期")
    end_date = models.DateField(blank=True, null=True, verbose_name="完成日期")
    status_choices = ((2, '在学'), (1, '未开通'), (0, '已完成'))
    status = models.SmallIntegerField(choices=status_choices, default=1)

    class Meta:
        unique_together = ('enrolled_degree_course', 'course_module')

    def __str__(self):
        return '%s-%s' % (self.enrolled_degree_course, self.course_module)

    def save(self, *args, **kwargs):
        if self.course_module.degree_course_id != self.enrolled_degree_course.degree_course_id:
            raise ValueError("学员要开通的模块必须与其报名的学位课程一致！")

        super(StudyRecord, self).save(*args, **kwargs)


class AccountManager(BaseUserManager):
    def create_user(self, username, mobile, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not username:
            raise ValueError('Username cannot be null')

        user = self.model(
            username=username,
            mobile=mobile,
            # name=name,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, mobile=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(username,
                                password=password,
                                mobile=mobile,
                                # name=name,
                                )
        user.is_superuser = True
        user.is_active = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, PermissionsMixin):
    username = models.CharField("用户名", max_length=64, unique=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        blank=True,
        null=True
    )
    # 与第3方交互用户信息时，用这个uid,以避免泄露敏感用户信息
    uid = models.CharField(max_length=64, unique=True)
    password = models.CharField('password', max_length=128,
                                help_text=mark_safe('''<a class='btn-link' href='password'>重置密码</a>'''))
    is_active = models.BooleanField(default=True, verbose_name="账户状态")
    is_staff = models.BooleanField(verbose_name='staff status', default=False, help_text='决定着用户是否可登录管理后台')
    head_img = models.CharField(max_length=256, default='/static/frontend/head_portrait/logo@2x.png',
                                verbose_name="个人头像")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    class Meta:
        verbose_name = '账户信息'
        verbose_name_plural = "账户信息"
        # permissions = []

    def save(self, *args, **kwargs):
        if not self.pk:
            # This code only happens if the objects is not in the database yet. Otherwise it would have pk
            m = hashlib.md5()
            m.update(self.username.encode(encoding="utf-8"))
            self.uid = m.hexdigest()
        super(Account, self).save(*args, **kwargs)

    objects = AccountManager()

    def __str__(self):
        return "%s" % (self.username, )


class Province(models.Model):
    """
    省份表
    """
    code = models.IntegerField(verbose_name="省代码", unique=True)
    name = models.CharField(max_length=64, verbose_name="省名称", unique=True)

    def __str__(self):
        return "{} - {}".format(self.code, self.name)

    class Meta:
        verbose_name = "省"
        verbose_name_plural = verbose_name


class City(models.Model):
    """
    城市表
    """
    code = models.IntegerField(verbose_name="市", unique=True)
    name = models.CharField(max_length=64, verbose_name="市名称")  # 城市名可能有重复
    province = models.ForeignKey("Province")

    def __str__(self):
        return "{} - {}".format(self.code, self.name)

    class Meta:
        verbose_name = "市"
        verbose_name_plural = verbose_name


class Industry(models.Model):
    """
    行业表
    """
    code = models.IntegerField(verbose_name="行业代码", unique=True)
    name = models.CharField(max_length=64, verbose_name="行业名称")

    def __str__(self):
        return "{} - {}".format(self.code, self.name)

    class Meta:
        verbose_name = "行业信息"
        verbose_name_plural = verbose_name


class Profession(models.Model):
    """
    职位表，与行业表外键关联
    """
    code = models.IntegerField(verbose_name="职位代码")
    name = models.CharField(max_length=64, verbose_name="职位名称")
    industry = models.ForeignKey("Industry")

    def __str__(self):
        return "{} - {}".format(self.code, self.name)

    class Meta:
        unique_together = ("code", "industry")
        verbose_name = "职位信息"
        verbose_name_plural = verbose_name

from typing import TypedDict, Optional, Annotated, Literal, Union
from typing import get_type_hints, get_origin, get_args
import json
from datetime import datetime


# ==================== 1. Annotated 用法 ====================

# Annotated 可以给类型添加元数据(metadata)
class UserProfile(TypedDict):
    # 基础字段
    user_id: Annotated[int, "用户唯一标识符"]
    username: Annotated[str, "用户名，3-20个字符"]
    email: Annotated[str, "电子邮箱地址"]

    # 带验证规则的字段
    age: Annotated[int, "年龄，必须在0-150之间"]
    phone: Annotated[str, "手机号，格式: 13800138000"]

    # 带默认值说明的字段
    score: Annotated[float, "用户积分，默认0.0"]


def annotated_example():
    """Annotated 使用示例"""
    print("\n" + "=" * 50)
    print("【Annotated 用法示例】")
    print("=" * 50)

    # 创建用户
    user: UserProfile = {
        'user_id': 1001,
        'username': 'zhangsan',
        'email': 'zhangsan@langgraph_example.com',
        'age': 25,
        'phone': '13800138000',
        'score': 100.5
    }

    # 获取类型提示（包含 Annotated 信息）
    hints = get_type_hints(UserProfile, include_extras=True)

    print("\n字段类型和说明:")
    for field_name, field_type in hints.items():
        # 检查是否是 Annotated 类型
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            actual_type = args[0]  # 实际类型
            metadata = args[1:]  # 元数据
            print(f"  {field_name}: {actual_type.__name__} - {metadata[0] if metadata else '无说明'}")
        else:
            print(f"  {field_name}: {field_type.__name__}")

    print(f"\n用户信息: {user['username']}, 积分: {user['score']}")
    return user


# ==================== 2. 必需和可选字段（兼容版本）====================

# 方法1: 使用 total=False 让所有字段可选
class AllOptionalUser(TypedDict, total=False):
    """所有字段都可选"""
    id: int
    username: str
    email: str
    phone: str
    avatar: str


# 方法2: 组合使用（推荐）
class UserRequired(TypedDict):
    """必需字段"""
    id: int
    username: str


class UserOptional(TypedDict, total=False):
    """可选字段"""
    email: str
    phone: str
    avatar: str
    bio: str


class User(UserRequired, UserOptional):
    """组合必需和可选字段"""
    pass


# 方法3: 使用 Optional 表示可以是 None
class UserWithNone(TypedDict):
    """某些字段可以是 None"""
    id: int
    username: str
    email: str
    phone: Optional[str]  # 可以是 str 或 None
    avatar: Optional[str]  # 可以是 str 或 None


def optional_fields_example():
    """可选字段示例"""
    print("\n" + "=" * 50)
    print("【必需和可选字段示例】")
    print("=" * 50)

    # 只提供必需字段
    user1: User = {
        'id': 1,
        'username': 'alice'
    }
    print(f"\n用户1 (仅必需字段): {user1}")

    # 提供所有字段
    user2: User = {
        'id': 2,
        'username': 'bob',
        'email': 'bob@langgraph_example.com',
        'phone': '13900139000',
        'avatar': 'avatar.jpg',
        'bio': '这是我的简介'
    }
    print(f"用户2 (包含可选字段): {user2}")

    # 安全地访问可选字段
    email = user1.get('email', '未提供')
    print(f"\n用户1的邮箱: {email}")

    email2 = user2.get('email', '未提供')
    print(f"用户2的邮箱: {email2}")

    # 使用 Optional 的例子
    user3: UserWithNone = {
        'id': 3,
        'username': 'charlie',
        'email': 'charlie@langgraph_example.com',
        'phone': None,  # 明确设置为 None
        'avatar': None
    }
    print(f"\n用户3 (使用 None): {user3}")

    # 检查是否为 None
    if user3['phone'] is None:
        print("用户3未设置手机号")


# ==================== 3. Literal 类型 ====================

class OrderStatus(TypedDict):
    order_id: str
    status: Literal['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    payment_method: Literal['credit_card', 'alipay', 'wechat', 'cash']


class OrderOptional(TypedDict, total=False):
    """订单可选字段"""
    tracking_number: str
    notes: str


class Order(OrderStatus, OrderOptional):
    """完整的订单信息"""
    pass


def literal_example():
    """Literal 类型示例"""
    print("\n" + "=" * 50)
    print("【Literal 类型示例】")
    print("=" * 50)

    # 创建订单
    order: Order = {
        'order_id': 'ORD-001',
        'status': 'processing',  # 只能是指定的几个值
        'payment_method': 'alipay',
        'tracking_number': 'SF1234567890'
    }

    print(f"\n订单号: {order['order_id']}")
    print(f"状态: {order['status']}")
    print(f"支付方式: {order['payment_method']}")
    print(f"快递单号: {order.get('tracking_number', '暂无')}")

    # 状态更新函数
    def update_order_status(
            order: Order,
            new_status: Literal['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    ) -> Order:
        order['status'] = new_status
        return order

    # 更新状态
    updated_order = update_order_status(order, 'shipped')
    print(f"更新后状态: {updated_order['status']}")

    # 状态到中文的映射
    status_map = {
        'pending': '待处理',
        'processing': '处理中',
        'shipped': '已发货',
        'delivered': '已送达',
        'cancelled': '已取消'
    }
    print(f"状态(中文): {status_map[updated_order['status']]}")


# ==================== 4. 继承和组合 ====================

class Timestamp(TypedDict):
    """时间戳混入"""
    created_at: str
    updated_at: str


class Identifiable(TypedDict):
    """可标识混入"""
    id: int


class SoftDelete(TypedDict, total=False):
    """软删除混入"""
    deleted_at: Optional[str]
    is_deleted: bool


class Article(Identifiable, Timestamp, SoftDelete):
    """文章 - 继承多个 TypedDict"""
    title: str
    content: str
    author: str
    tags: list[str]


class Comment(Identifiable, Timestamp):
    """评论 - 继承多个 TypedDict"""
    article_id: int
    user_id: int
    content: str


class CommentOptional(TypedDict, total=False):
    """评论可选字段"""
    likes: int
    parent_id: Optional[int]


class FullComment(Comment, CommentOptional):
    """完整评论"""
    pass


def inheritance_example():
    """继承示例"""
    print("\n" + "=" * 50)
    print("【继承和组合示例】")
    print("=" * 50)

    # 创建文章
    article: Article = {
        'id': 1,
        'title': 'Python TypedDict 教程',
        'content': '这是一篇关于 TypedDict 的教程...',
        'author': '张三',
        'tags': ['Python', 'TypedDict', '教程'],
        'created_at': '2024-01-01 10:00:00',
        'updated_at': '2024-01-01 10:00:00',
        'is_deleted': False
    }

    # 创建评论
    comment: FullComment = {
        'id': 101,
        'article_id': 1,
        'user_id': 1001,
        'content': '写得很好！',
        'created_at': '2024-01-01 11:00:00',
        'updated_at': '2024-01-01 11:00:00',
        'likes': 5,
        'parent_id': None  # 顶级评论
    }

    print(f"\n文章: {article['title']}")
    print(f"作者: {article['author']}")
    print(f"标签: {', '.join(article['tags'])}")
    print(f"创建时间: {article['created_at']}")
    print(f"已删除: {'是' if article.get('is_deleted', False) else '否'}")

    print(f"\n评论ID: {comment['id']}")
    print(f"内容: {comment['content']}")
    print(f"点赞数: {comment.get('likes', 0)}")
    print(f"评论时间: {comment['created_at']}")


# ==================== 5. Union 类型 ====================

class TextMessage(TypedDict):
    type: Literal['text']
    content: str


class ImageMessage(TypedDict):
    type: Literal['image']
    url: str
    width: int
    height: int


class ImageMessageOptional(TypedDict, total=False):
    """图片消息可选字段"""
    thumbnail: str
    size: int  # 文件大小(字节)


class FullImageMessage(ImageMessage, ImageMessageOptional):
    """完整图片消息"""
    pass


class VideoMessage(TypedDict):
    type: Literal['video']
    url: str
    duration: int  # 秒


class VideoMessageOptional(TypedDict, total=False):
    """视频消息可选字段"""
    thumbnail: str
    size: int
    resolution: str  # 例如: "1920x1080"


class FullVideoMessage(VideoMessage, VideoMessageOptional):
    """完整视频消息"""
    pass


# 消息可以是以上任意一种类型
Message = Union[TextMessage, FullImageMessage, FullVideoMessage]


def union_example():
    """Union 类型示例"""
    print("\n" + "=" * 50)
    print("【Union 类型示例】")
    print("=" * 50)

    # 创建不同类型的消息
    messages: list[Message] = [
        {'type': 'text', 'content': '你好！'},
        {
            'type': 'image',
            'url': 'https://example.com/pic.jpg',
            'width': 1920,
            'height': 1080,
            'thumbnail': 'https://example.com/pic_thumb.jpg',
            'size': 1024000
        },
        {
            'type': 'video',
            'url': 'https://example.com/video.mp4',
            'duration': 120,
            'resolution': '1920x1080'
        }
    ]

    # 处理不同类型的消息
    for i, msg in enumerate(messages, 1):
        print(f"\n消息 {i}:")
        if msg['type'] == 'text':
            print(f"  类型: 文本")
            print(f"  内容: {msg['content']}")
        elif msg['type'] == 'image':
            print(f"  类型: 图片")
            print(f"  URL: {msg['url']}")
            print(f"  尺寸: {msg['width']}x{msg['height']}")
            if 'size' in msg:
                print(f"  大小: {msg['size'] / 1024:.1f} KB")
        elif msg['type'] == 'video':
            print(f"  类型: 视频")
            print(f"  URL: {msg['url']}")
            print(f"  时长: {msg['duration']}秒")
            if 'resolution' in msg:
                print(f"  分辨率: {msg['resolution']}")


# ==================== 6. 数据验证 ====================

class ValidationError(Exception):
    """验证错误"""
    pass


class UserRegistration(TypedDict):
    username: Annotated[str, "用户名，3-20个字符"]
    password: Annotated[str, "密码，至少8个字符"]
    email: Annotated[str, "有效的邮箱地址"]
    age: Annotated[int, "年龄，18-100岁"]


class UserRegistrationOptional(TypedDict, total=False):
    """注册可选字段"""
    phone: str
    referral_code: str


class FullUserRegistration(UserRegistration, UserRegistrationOptional):
    """完整注册信息"""
    pass


def validate_user_registration(data: FullUserRegistration) -> bool:
    """验证用户注册数据"""
    errors = []

    # 验证用户名
    if not (3 <= len(data['username']) <= 20):
        errors.append("用户名必须是3-20个字符")

    # 验证密码
    if len(data['password']) < 8:
        errors.append("密码至少需要8个字符")

    # 验证邮箱（简单验证）
    if '@' not in data['email'] or '.' not in data['email']:
        errors.append("邮箱格式不正确")

    # 验证年龄
    if not (18 <= data['age'] <= 100):
        errors.append("年龄必须在18-100岁之间")

    # 验证可选字段
    if 'phone' in data and data['phone']:
        if not data['phone'].isdigit() or len(data['phone']) != 11:
            errors.append("手机号格式不正确")

    if errors:
        raise ValidationError("验证失败:\n  - " + "\n  - ".join(errors))

    return True


def validation_example():
    """数据验证示例"""
    print("\n" + "=" * 50)
    print("【数据验证示例】")
    print("=" * 50)

    # 有效的数据
    valid_data: FullUserRegistration = {
        'username': 'zhangsan',
        'password': 'password123',
        'email': 'zhangsan@langgraph_example.com',
        'age': 25,
        'phone': '13800138000'
    }

    try:
        validate_user_registration(valid_data)
        print("\n✓ 数据验证通过")
        print(f"  用户名: {valid_data['username']}")
        print(f"  邮箱: {valid_data['email']}")
        print(f"  手机: {valid_data.get('phone', '未提供')}")
    except ValidationError as e:
        print(f"\n✗ {e}")

    # 无效的数据
    invalid_data: FullUserRegistration = {
        'username': 'ab',  # 太短
        'password': '123',  # 太短
        'email': 'invalid-email',  # 格式错误
        'age': 15,  # 太小
        'phone': '123'  # 格式错误
    }

    try:
        validate_user_registration(invalid_data)
    except ValidationError as e:
        print(f"\n✗ {e}")


# ==================== 7. JSON 序列化/反序列化 ====================

class Product(TypedDict):
    id: int
    name: str
    price: float
    in_stock: bool
    tags: list[str]


class ProductOptional(TypedDict, total=False):
    """产品可选字段"""
    description: str
    category: str
    discount: float


class FullProduct(Product, ProductOptional):
    """完整产品信息"""
    pass


def to_json(data: dict) -> str:
    """将 TypedDict 转换为 JSON 字符串"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def from_json(json_str: str) -> dict:
    """从 JSON 字符串创建字典"""
    return json.loads(json_str)


def json_example():
    """JSON 序列化示例"""
    print("\n" + "=" * 50)
    print("【JSON 序列化/反序列化示例】")
    print("=" * 50)

    # 创建产品
    product: FullProduct = {
        'id': 1,
        'name': 'iPhone 15 Pro',
        'price': 7999.0,
        'in_stock': True,
        'tags': ['手机', '苹果', '5G'],
        'description': '最新款苹果手机',
        'category': '数码产品',
        'discount': 0.95
    }

    # 转换为 JSON
    json_str = to_json(product)
    print("\n序列化为 JSON:")
    print(json_str)

    # 从 JSON 恢复
    restored_product: FullProduct = from_json(json_str)
    print("\n从 JSON 恢复:")
    print(f"  产品: {restored_product['name']}")
    print(f"  价格: ¥{restored_product['price']}")
    print(f"  库存: {'有货' if restored_product['in_stock'] else '缺货'}")
    print(f"  标签: {', '.join(restored_product['tags'])}")
    print(f"  描述: {restored_product.get('description', '无')}")

    # 批量处理
    products: list[FullProduct] = [
        {
            'id': 1,
            'name': 'iPhone 15',
            'price': 5999.0,
            'in_stock': True,
            'tags': ['手机'],
            'category': '数码'
        },
        {
            'id': 2,
            'name': 'iPad Pro',
            'price': 6799.0,
            'in_stock': False,
            'tags': ['平板'],
            'category': '数码'
        }
    ]

    products_json = to_json(products)
    print("\n批量产品 JSON:")
    print(products_json)


# ==================== 8. 实际项目: API 响应 ====================

class APIError(TypedDict):
    """API 错误响应"""
    code: int
    message: str


class APIErrorOptional(TypedDict, total=False):
    """错误可选字段"""
    details: str
    field: str  # 哪个字段出错


class FullAPIError(APIError, APIErrorOptional):
    """完整错误信息"""
    pass


class Pagination(TypedDict):
    """分页信息"""
    page: int
    page_size: int
    total: int
    total_pages: int


class APIResponseBase(TypedDict):
    """API 基础响应"""
    success: bool


class APIResponseOptional(TypedDict, total=False):
    """API 可选字段"""
    data: dict
    error: FullAPIError
    pagination: Pagination
    message: str


class APIResponse(APIResponseBase, APIResponseOptional):
    """API 完整响应"""
    pass


class UserData(TypedDict):
    """用户数据"""
    id: int
    username: str
    email: str
    role: Literal['admin', 'user', 'guest']


def create_success_response(data: dict, pagination: Optional[Pagination] = None) -> APIResponse:
    """创建成功响应"""
    response: APIResponse = {'success': True, 'data': data}
    if pagination:
        response['pagination'] = pagination
    return response


def create_error_response(code: int, message: str, details: Optional[str] = None) -> APIResponse:
    """创建错误响应"""
    error: FullAPIError = {'code': code, 'message': message}
    if details:
        error['details'] = details

    return {'success': False, 'error': error}


def api_example():
    """API 响应示例"""
    print("\n" + "=" * 50)
    print("【API 响应示例】")
    print("=" * 50)

    # 成功响应
    user_data: UserData = {
        'id': 1001,
        'username': 'zhangsan',
        'email': 'zhangsan@langgraph_example.com',
        'role': 'admin'
    }

    pagination: Pagination = {
        'page': 1,
        'page_size': 10,
        'total': 100,
        'total_pages': 10
    }

    success_response = create_success_response(user_data, pagination)
    print("\n成功响应:")
    print(json.dumps(success_response, ensure_ascii=False, indent=2))

    # 错误响应
    error_response = create_error_response(
        code=404,
        message='用户不存在',
        details='找不到ID为9999的用户'
    )
    print("\n错误响应:")
    print(json.dumps(error_response, ensure_ascii=False, indent=2))

    # 表单验证错误
    validation_error: FullAPIError = {
        'code': 400,
        'message': '表单验证失败',
        'field': 'email',
        'details': '邮箱格式不正确'
    }

    validation_response: APIResponse = {
        'success': False,
        'error': validation_error
    }
    print("\n表单验证错误响应:")
    print(json.dumps(validation_response, ensure_ascii=False, indent=2))


# ==================== 9. 实际项目: 配置管理 ====================

class DatabaseConfig(TypedDict):
    """数据库必需配置"""
    host: str
    port: int
    database: str
    username: str
    password: str


class DatabaseConfigOptional(TypedDict, total=False):
    """数据库可选配置"""
    pool_size: int
    timeout: int
    charset: str


class FullDatabaseConfig(DatabaseConfig, DatabaseConfigOptional):
    """完整数据库配置"""
    pass


class RedisConfig(TypedDict):
    """Redis 必需配置"""
    host: str
    port: int
    db: int


class RedisConfigOptional(TypedDict, total=False):
    """Redis 可选配置"""
    password: str
    max_connections: int


class FullRedisConfig(RedisConfig, RedisConfigOptional):
    """完整 Redis 配置"""
    pass


class AppConfig(TypedDict):
    """应用配置"""
    app_name: str
    debug: bool
    secret_key: str
    database: FullDatabaseConfig
    redis: FullRedisConfig


class AppConfigOptional(TypedDict, total=False):
    """应用可选配置"""
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
    max_upload_size: int  # MB


class FullAppConfig(AppConfig, AppConfigOptional):
    """完整应用配置"""
    pass


def config_example():
    """配置管理示例"""
    print("\n" + "=" * 50)
    print("【配置管理示例】")
    print("=" * 50)

    # 应用配置
    config: FullAppConfig = {
        'app_name': 'MyApp',
        'debug': True,
        'secret_key': 'your-secret-key-here',
        'log_level': 'DEBUG',
        'max_upload_size': 100,
        'database': {
            'host': 'localhost',
            'port': 3306,
            'database': 'myapp_db',
            'username': 'root',
            'password': 'password',
            'pool_size': 10,
            'timeout': 30,
            'charset': 'utf8mb4'
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': 'redis_password',
            'max_connections': 50
        }
    }

    print(f"\n应用名称: {config['app_name']}")
    print(f"调试模式: {'开启' if config['debug'] else '关闭'}")
    print(f"日志级别: {config.get('log_level', 'INFO')}")
    print(f"最大上传大小: {config.get('max_upload_size', 10)} MB")

    print(f"\n数据库配置:")
    db_config = config['database']
    print(f"  地址: {db_config['host']}:{db_config['port']}")
    print(f"  数据库: {db_config['database']}")
    print(f"  连接池大小: {db_config.get('pool_size', 5)}")
    print(f"  字符集: {db_config.get('charset', 'utf8')}")

    print(f"\nRedis配置:")
    redis_config = config['redis']
    print(f"  地址: {redis_config['host']}:{redis_config['port']}")
    print(f"  数据库: {redis_config['db']}")
    print(f"  最大连接数: {redis_config.get('max_connections', 10)}")


# ==================== 10. 实际项目: 数据转换 ====================

class RawData(TypedDict):
    """原始数据格式（例如从CSV读取）"""
    user_id: str
    user_name: str
    user_email: str
    user_age: str


class RawDataOptional(TypedDict, total=False):
    """原始数据可选字段"""
    user_phone: str
    user_city: str


class FullRawData(RawData, RawDataOptional):
    """完整原始数据"""
    pass


class CleanData(TypedDict):
    """清洗后的数据格式"""
    id: int
    name: str
    email: str
    age: int


class CleanDataOptional(TypedDict, total=False):
    """清洗后可选字段"""
    phone: str
    city: str


class FullCleanData(CleanData, CleanDataOptional):
    """完整清洗数据"""
    pass


def transform_data(raw: FullRawData) -> FullCleanData:
    """数据转换函数"""
    clean: FullCleanData = {
        'id': int(raw['user_id']),
        'name': raw['user_name'].strip(),
        'email': raw['user_email'].lower().strip(),
        'age': int(raw['user_age'])
    }

    # 处理可选字段
    if 'user_phone' in raw:
        clean['phone'] = raw['user_phone'].strip()

    if 'user_city' in raw:
        clean['city'] = raw['user_city'].strip()

    return clean


def data_transform_example():
    """数据转换示例"""
    print("\n" + "=" * 50)
    print("【数据转换示例】")
    print("=" * 50)

    # 原始数据（例如从 CSV 读取）
    raw_users: list[FullRawData] = [
        {
            'user_id': '1',
            'user_name': ' 张三 ',
            'user_email': 'ZHANG@EXAMPLE.COM',
            'user_age': '25',
            'user_phone': '13800138000',
            'user_city': '北京'
        },
        {
            'user_id': '2',
            'user_name': '李四',
            'user_email': 'Li@Example.com  ',
            'user_age': '30',
            'user_city': '上海'
        },
    ]

    print("\n原始数据:")
    for raw in raw_users:
        print(f"  {raw}")

    # 转换数据
    clean_users: list[FullCleanData] = [transform_data(raw) for raw in raw_users]

    print("\n清洗后数据:")
    for user in clean_users:
        print(f"  ID: {user['id']}, 姓名: {user['name']}, "
              f"邮箱: {user['email']}, 年龄: {user['age']}, "
              f"城市: {user.get('city', '未知')}")


# ==================== 11. 类型守卫和消息处理 ====================

def is_text_message(msg: Message) -> bool:
    """类型守卫: 判断是否为文本消息"""
    return msg.get('type') == 'text'


def is_image_message(msg: Message) -> bool:
    """类型守卫: 判断是否为图片消息"""
    return msg.get('type') == 'image'


def is_video_message(msg: Message) -> bool:
    """类型守卫: 判断是否为视频消息"""
    return msg.get('type') == 'video'


def process_message(msg: Message) -> str:
    """处理消息的统一接口"""
    if is_text_message(msg):
        # 这里 IDE 会知道 msg 是 TextMessage 类型
        text_msg = msg  # type: TextMessage
        return f"文本消息: {text_msg['content']}"

    elif is_image_message(msg):
        # 这里 IDE 会知道 msg 是 ImageMessage 类型
        image_msg = msg  # type: FullImageMessage
        result = f"图片消息: {image_msg['url']} ({image_msg['width']}x{image_msg['height']})"
        if 'size' in image_msg:
            result += f" - {image_msg['size'] / 1024:.1f}KB"
        return result

    elif is_video_message(msg):
        # 这里 IDE 会知道 msg 是 VideoMessage 类型
        video_msg = msg  # type: FullVideoMessage
        result = f"视频消息: {video_msg['url']} (时长: {video_msg['duration']}秒)"
        if 'resolution' in video_msg:
            result += f" - {video_msg['resolution']}"
        return result

    else:
        return "未知消息类型"


def get_message_summary(messages: list[Message]) -> dict:
    """获取消息统计摘要"""
    summary = {
        'total': len(messages),
        'text': 0,
        'image': 0,
        'video': 0
    }

    for msg in messages:
        if is_text_message(msg):
            summary['text'] += 1
        elif is_image_message(msg):
            summary['image'] += 1
        elif is_video_message(msg):
            summary['video'] += 1

    return summary


def type_guard_example():
    """类型守卫示例"""
    print("\n" + "=" * 50)
    print("【类型守卫示例】")
    print("=" * 50)

    messages: list[Message] = [
        {'type': 'text', 'content': 'Hello World'},
        {'type': 'text', 'content': '你好'},
        {
            'type': 'image',
            'url': 'pic1.jpg',
            'width': 800,
            'height': 600,
            'size': 102400
        },
        {'type': 'image', 'url': 'pic2.jpg', 'width': 1920, 'height': 1080},
        {
            'type': 'video',
            'url': 'video.mp4',
            'duration': 60,
            'resolution': '1920x1080'
        }
    ]

    print("\n处理消息:")
    for i, msg in enumerate(messages, 1):
        result = process_message(msg)
        print(f"  {i}. {result}")

    # 统计摘要
    summary = get_message_summary(messages)
    print(f"\n消息统计:")
    print(f"  总数: {summary['total']}")
    print(f"  文本: {summary['text']}")
    print(f"  图片: {summary['image']}")
    print(f"  视频: {summary['video']}")


# ==================== 12. 实际项目: 购物车系统 ====================

class CartItem(TypedDict):
    """购物车商品"""
    product_id: int
    name: str
    price: float
    quantity: int


class CartItemOptional(TypedDict, total=False):
    """购物车商品可选字段"""
    discount: float  # 折扣 0-1
    image: str


class FullCartItem(CartItem, CartItemOptional):
    """完整购物车商品"""
    pass


class ShoppingCart(TypedDict):
    """购物车"""
    user_id: int
    items: list[FullCartItem]


class ShoppingCartOptional(TypedDict, total=False):
    """购物车可选字段"""
    coupon_code: str
    shipping_address: str


class FullShoppingCart(ShoppingCart, ShoppingCartOptional):
    """完整购物车"""
    pass


def calculate_cart_total(cart: FullShoppingCart) -> dict:
    """计算购物车总价"""
    subtotal = 0.0

    for item in cart['items']:
        item_price = item['price'] * item['quantity']

        # 应用折扣
        if 'discount' in item:
            item_price *= item['discount']

        subtotal += item_price

    # 优惠券（示例：固定减10元）
    coupon_discount = 10.0 if cart.get('coupon_code') else 0.0

    total = subtotal - coupon_discount

    return {
        'subtotal': round(subtotal, 2),
        'coupon_discount': round(coupon_discount, 2),
        'total': round(total, 2)
    }


def shopping_cart_example():
    """购物车系统示例"""
    print("\n" + "=" * 50)
    print("【购物车系统示例】")
    print("=" * 50)

    # 创建购物车
    cart: FullShoppingCart = {
        'user_id': 1001,
        'items': [
            {
                'product_id': 1,
                'name': 'iPhone 15',
                'price': 5999.0,
                'quantity': 1,
                'discount': 0.95,  # 95折
                'image': 'iphone15.jpg'
            },
            {
                'product_id': 2,
                'name': 'AirPods Pro',
                'price': 1999.0,
                'quantity': 2,
                'image': 'airpods.jpg'
            },
            {
                'product_id': 3,
                'name': '保护壳',
                'price': 99.0,
                'quantity': 1
            }
        ],
        'coupon_code': 'SAVE10',
        'shipping_address': '北京市朝阳区xxx路xxx号'
    }

    print(f"\n用户 {cart['user_id']} 的购物车:")
    print(f"\n商品列表:")
    for item in cart['items']:
        discount_text = f" (折扣: {item['discount'] * 100:.0f}%)" if 'discount' in item else ""
        print(f"  - {item['name']}: ¥{item['price']} x {item['quantity']}{discount_text}")

    # 计算总价
    summary = calculate_cart_total(cart)
    print(f"\n价格明细:")
    print(f"  小计: ¥{summary['subtotal']}")
    if summary['coupon_discount'] > 0:
        print(f"  优惠券: -¥{summary['coupon_discount']}")
    print(f"  总计: ¥{summary['total']}")

    if 'shipping_address' in cart:
        print(f"\n配送地址: {cart['shipping_address']}")


# ==================== 主函数 ====================

def main():
    """运行所有高级示例"""

    print("=" * 60)
    print(" " * 10 + "Python TypedDict 高级用法（兼容版）")
    print("=" * 60)

    # 1. Annotated
    annotated_example()

    # 2. 可选字段
    optional_fields_example()

    # 3. Literal
    literal_example()

    # 4. 继承
    inheritance_example()

    # 5. Union
    union_example()

    # 6. 数据验证
    validation_example()

    # 7. JSON 序列化
    json_example()

    # 8. API 响应
    api_example()

    # 9. 配置管理
    config_example()

    # 10. 数据转换
    data_transform_example()

    # 11. 类型守卫
    type_guard_example()

    # 12. 购物车系统
    shopping_cart_example()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

    # 总结
    print("\n💡 总结要点:")
    print("1. 使用 total=False 定义所有可选字段")
    print("2. 组合继承: 分别定义必需和可选字段，然后组合")
    print("3. Optional[T] 表示可以是 T 或 None")
    print("4. Literal 限制字段值为特定选项")
    print("5. Union 表示多种类型选择")
    print("6. Annotated 添加元数据和文档")
    print("7. 使用 .get() 安全访问可选字段")


if __name__ == '__main__':
    main()
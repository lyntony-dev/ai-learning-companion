
"""

typeDict的基本用法
"""
from typing import TypedDict, Optional

# ==================== 1. 基础定义 ====================

# 方式1: 使用 class 语法定义(推荐)
class Person(TypedDict):
    name: str          # 必需字段
    age: int           # 必需字段
    email: str         # 必需字段


# 方式2: 使用函数语法定义
PersonDict = TypedDict('PersonDict', {
    'name': str,
    'age': int,
    'email': str
})


# ==================== 2. 可选字段 ====================

# 使用 total=False 让所有字段都可选
class OptionalPerson(TypedDict, total=False):
    name: str
    age: int
    email: str


# 使用 NotRequired 让部分字段可选(Python 3.11+)
# 如果是 Python 3.8-3.10,使用 Optional 或继承两个类
class Student(TypedDict):
    name: str                    # 必需
    age: int                     # 必需
    grade: Optional[str]         # 可以是 str 或 None


# 更好的方式:分别定义必需和可选字段
class Employee(TypedDict):
    name: str
    position: str

class EmployeeOptional(TypedDict, total=False):
    department: str
    salary: float

# 组合使用
class FullEmployee(Employee, EmployeeOptional):
    pass


# ==================== 3. 创建和使用 ====================

def basic_usage():
    """基础用法示例"""
    
    # 创建一个 Person 字典
    person: Person = {
        'name': '张三',
        'age': 25,
        'email': 'zhangsan@langgraph_example.com'
    }
    
    # 访问数据(就像普通字典一样)
    print(f"姓名: {person['name']}")
    print(f"年龄: {person['age']}")
    print(f"邮箱: {person['email']}")
    
    # 修改数据
    person['age'] = 26
    print(f"修改后年龄: {person['age']}")
    
    # 添加新键(TypedDict 不会阻止,但类型检查器会警告)
    # person['phone'] = '12345'  # 类型检查器会提示错误
    
    return person


# ==================== 4. 遍历操作 ====================

def iterate_dict():
    """遍历字典示例"""
    
    person: Person = {
        'name': '李四',
        'age': 30,
        'email': 'lisi@langgraph_example.com'
    }
    
    # 遍历键
    print("\n遍历键:")
    for key in person.keys():
        print(f"  {key}")
    
    # 遍历值
    print("\n遍历值:")
    for value in person.values():
        print(f"  {value}")
    
    # 遍历键值对
    print("\n遍历键值对:")
    for key, value in person.items():
        print(f"  {key}: {value}")


# ==================== 5. 嵌套 TypedDict ====================

class Address(TypedDict):
    street: str
    city: str
    country: str


class PersonWithAddress(TypedDict):
    name: str
    age: int
    address: Address  # 嵌套另一个 TypedDict


def nested_example():
    """嵌套示例"""
    
    person: PersonWithAddress = {
        'name': '王五',
        'age': 28,
        'address': {
            'street': '中关村大街1号',
            'city': '北京',
            'country': '中国'
        }
    }
    
    # 访问嵌套数据
    print(f"\n姓名: {person['name']}")
    print(f"城市: {person['address']['city']}")
    print(f"完整地址: {person['address']['street']}, "
          f"{person['address']['city']}, {person['address']['country']}")


# ==================== 6. 函数参数和返回值 ====================

def create_person(name: str, age: int, email: str) -> Person:
    """创建并返回一个 Person 字典"""
    return {
        'name': name,
        'age': age,
        'email': email
    }


def print_person_info(person: Person) -> None:
    """打印人员信息"""
    print(f"\n=== 人员信息 ===")
    print(f"姓名: {person['name']}")
    print(f"年龄: {person['age']}")
    print(f"邮箱: {person['email']}")


def update_person_age(person: Person, new_age: int) -> Person:
    """更新年龄并返回新字典"""
    updated_person = person.copy()  # 创建副本
    updated_person['age'] = new_age
    return updated_person


# ==================== 7. 常用操作 ====================

def common_operations():
    """常用字典操作"""
    
    person: Person = {
        'name': '赵六',
        'age': 35,
        'email': 'zhaoliu@langgraph_example.com'
    }
    
    # 检查键是否存在
    if 'name' in person:
        print(f"\n姓名存在: {person['name']}")
    
    # 使用 get 方法(更安全,避免 KeyError)
    age = person.get('age', 0)  # 如果不存在返回默认值 0
    print(f"年龄: {age}")
    
    # 获取所有键
    keys = list(person.keys())
    print(f"所有键: {keys}")
    
    # 获取所有值
    values = list(person.values())
    print(f"所有值: {values}")
    
    # 复制字典
    person_copy = person.copy()
    print(f"复制的字典: {person_copy}")
    
    # 更新字典
    person.update({'age': 36})
    print(f"更新后年龄: {person['age']}")


# ==================== 8. 列表中使用 TypedDict ====================

def list_of_typed_dicts():
    """TypedDict 列表示例"""
    
    # 创建多个 Person
    people: list[Person] = [
        {'name': '张三', 'age': 25, 'email': 'zhangsan@langgraph_example.com'},
        {'name': '李四', 'age': 30, 'email': 'lisi@langgraph_example.com'},
        {'name': '王五', 'age': 28, 'email': 'wangwu@langgraph_example.com'},
    ]
    
    print("\n=== 人员列表 ===")
    for i, person in enumerate(people, 1):
        print(f"{i}. {person['name']}, {person['age']}岁, {person['email']}")
    
    # 筛选年龄大于 27 的人
    adults = [p for p in people if p['age'] > 27]
    print(f"\n年龄大于27岁的人数: {len(adults)}")
    
    # 按年龄排序
    sorted_people = sorted(people, key=lambda p: p['age'])
    print("\n按年龄排序:")
    for person in sorted_people:
        print(f"  {person['name']}: {person['age']}岁")


# ==================== 9. 实际应用示例 ====================

class Product(TypedDict):
    id: int
    name: str
    price: float
    stock: int


class Order(TypedDict):
    order_id: str
    customer_name: str
    products: list[Product]
    total_amount: float


def shopping_example():
    """购物系统示例"""
    
    # 创建商品
    products: list[Product] = [
        {'id': 1, 'name': 'iPhone 15', 'price': 5999.0, 'stock': 10},
        {'id': 2, 'name': 'iPad Pro', 'price': 6799.0, 'stock': 5},
        {'id': 3, 'name': 'AirPods', 'price': 1299.0, 'stock': 20},
    ]
    
    # 创建订单
    order: Order = {
        'order_id': 'ORD-2024-001',
        'customer_name': '张三',
        'products': [products[0], products[2]],  # 购买 iPhone 和 AirPods
        'total_amount': 5999.0 + 1299.0
    }
    
    # 打印订单信息
    print("\n=== 订单详情 ===")
    print(f"订单号: {order['order_id']}")
    print(f"客户: {order['customer_name']}")
    print(f"商品:")
    for product in order['products']:
        print(f"  - {product['name']}: ¥{product['price']}")
    print(f"总金额: ¥{order['total_amount']}")


# ==================== 主函数 ====================

def main():
    """运行所有示例"""
    
    print("=" * 50)
    print("Python TypedDict 完整教程")
    print("=" * 50)
    
    # 1. 基础用法
    print("\n【1. 基础用法】")
    person = basic_usage()
    
    # 2. 遍历操作
    print("\n【2. 遍历操作】")
    iterate_dict()
    
    # 3. 嵌套示例
    print("\n【3. 嵌套 TypedDict】")
    nested_example()
    
    # 4. 函数使用
    print("\n【4. 在函数中使用】")
    new_person = create_person('孙七', 22, 'sunqi@langgraph_example.com')
    print_person_info(new_person)
    
    updated = update_person_age(new_person, 23)
    print(f"更新后年龄: {updated['age']}")
    
    # 5. 常用操作
    print("\n【5. 常用操作】")
    common_operations()
    
    # 6. 列表操作
    print("\n【6. TypedDict 列表】")
    list_of_typed_dicts()
    
    # 7. 实际应用
    print("\n【7. 实际应用示例】")
    shopping_example()


if __name__ == '__main__':
    main()
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime, timezone

class CategoryType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

@dataclass
class CategoryRule:
    fieldToMatch: str
    condition: str
    value: Any
    # ruleLogic: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fieldToMatch": self.fieldToMatch,
            "condition": self.condition,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryRule':
        return CategoryRule(
            fieldToMatch=data["fieldToMatch"],
            condition=data["condition"],
            value=data["value"],
        )

@dataclass
class Category:
    userId: str
    name: str
    type: CategoryType
    categoryId: str = field(default_factory=lambda: f"cat_{uuid4()}")
    parentCategoryId: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = field(default_factory=list)
    createdAt: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
    updatedAt: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = CategoryType(self.type)
        if self.rules and isinstance(self.rules, list) and len(self.rules) > 0:
            self.rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in self.rules]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "categoryId": self.categoryId,
            "userId": self.userId,
            "name": self.name,
            "type": self.type.value,
            "parentCategoryId": self.parentCategoryId,
            "icon": self.icon,
            "color": self.color,
            "rules": [rule.to_dict() for rule in self.rules],
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        rules_data = data.get("rules", [])
        parsed_rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in rules_data]
        parsed_rules = [r for r in parsed_rules if isinstance(r, CategoryRule) or isinstance(r, dict)]
        parsed_rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in parsed_rules]

        return Category(
            userId=data["userId"],
            name=data["name"],
            type=CategoryType(data["type"]) if isinstance(data["type"], str) else data["type"],
            categoryId=data.get("categoryId", f"cat_{uuid4()}"),
            parentCategoryId=data.get("parentCategoryId"),
            icon=data.get("icon"),
            color=data.get("color"),
            rules=[r for r in parsed_rules if isinstance(r, CategoryRule)],
            createdAt=data.get("createdAt", int(datetime.now(timezone.utc).timestamp() * 1000)),
            updatedAt=data.get("updatedAt", int(datetime.now(timezone.utc).timestamp() * 1000)),
        )

@dataclass
class CategoryCreate:
    name: str
    type: CategoryType
    parentCategoryId: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = CategoryType(self.type)
        if self.rules and isinstance(self.rules, list) and len(self.rules) > 0:
             self.rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in self.rules]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "parentCategoryId": self.parentCategoryId,
            "icon": self.icon,
            "color": self.color,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryCreate':
        rules_data = data.get("rules", [])
        parsed_rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in rules_data]
        parsed_rules = [r for r in parsed_rules if isinstance(r, CategoryRule) or isinstance(r, dict)]
        parsed_rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in parsed_rules]

        return CategoryCreate(
            name=data["name"],
            type=CategoryType(data["type"]) if isinstance(data["type"], str) else data["type"],
            parentCategoryId=data.get("parentCategoryId"),
            icon=data.get("icon"),
            color=data.get("color"),
            rules=[r for r in parsed_rules if isinstance(r, CategoryRule)],
        )

@dataclass
class CategoryUpdate:
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    parentCategoryId: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: Optional[List[CategoryRule]] = None

    def __post_init__(self):
        if self.type is not None and isinstance(self.type, str):
            self.type = CategoryType(self.type)
        if self.parentCategoryId == "":
            self.parentCategoryId = None
        if self.rules and isinstance(self.rules, list) and len(self.rules) > 0:
            self.rules = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in self.rules]

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for f in self.__dataclass_fields__:
            f_value = getattr(self, f)
            if f_value is not None:
                if f == "type" and isinstance(f_value, CategoryType):
                    data[f] = f_value.value
                elif f == "rules" and isinstance(f_value, list):
                    data[f] = [r.to_dict() for r in f_value]
                else:
                    data[f] = f_value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryUpdate':
        kwargs = {}
        if "name" in data and data["name"] is not None:
            kwargs["name"] = data["name"]
        if "type" in data and data["type"] is not None:
            kwargs["type"] = CategoryType(data["type"]) if isinstance(data["type"], str) else data["type"]
        if "parentCategoryId" in data:
            kwargs["parentCategoryId"] = None if data["parentCategoryId"] == "" else data["parentCategoryId"]
        if "icon" in data and data["icon"] is not None:
            kwargs["icon"] = data["icon"]
        if "color" in data and data["color"] is not None:
            kwargs["color"] = data["color"]
        if "rules" in data and data["rules"] is not None:
            rules_data = data.get("rules", [])
            parsed_rules_temp = [CategoryRule.from_dict(r) if isinstance(r, dict) else r for r in rules_data]
            kwargs["rules"] = [r for r in parsed_rules_temp if isinstance(r, CategoryRule)]
        
        return CategoryUpdate(**kwargs) 
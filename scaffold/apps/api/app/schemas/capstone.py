"""结课项目 (F) API schema (DESIGN §4)。

重设计:立项向导 + 个性化清单。
  - GET  project:读项目状态(无项目→向导态,返回作业说明);
  - POST project:学生立项(goal/audience/difficulty)→ 生成项目卡 + 个性化清单;
  - PATCH item:勾选/取消清单项 → 派生里程碑状态。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectCard(BaseModel):
    """立项收敛后的项目卡。"""

    title: str = ""
    scope: str = ""
    tech_stack: list[str] = Field(default_factory=list)


class ChecklistItemView(BaseModel):
    """一条可勾选清单项。"""

    id: str
    text: str
    checked: bool = False


class ProjectMilestone(BaseModel):
    """里程碑视图:作业说明 + 个性化清单 + 派生状态。"""

    milestone_id: str
    name: str
    status: str  # not_started | in_progress | passed
    deliverable: str = ""  # 通用交付要求(来自课程包)
    hint: str = ""  # 完成提示(来自课程包)
    items: list[ChecklistItemView] = Field(default_factory=list)  # 立项后生成


class CapstoneProjectResponse(BaseModel):
    course_pack_id: str
    capstone_name: str
    has_project: bool = False  # 是否已立项
    card: ProjectCard | None = None  # 已立项才有
    milestones: list[ProjectMilestone] = Field(default_factory=list)
    current_milestone_id: str = ""
    passed_count: int = 0
    total: int = 0
    all_passed: bool = False
    overview: str = ""  # 项目总体说明(来自课程包)
    background: str = ""  # 项目背景/场景(来自课程包)
    final_deliverable: str = ""  # 结课最终交付物(来自课程包)


class CreateProjectRequest(BaseModel):
    learner_id: str = "demo_user"
    goal: str  # 想做一个什么 Agent
    audience: str = ""  # 面向谁 / 什么场景
    difficulty: str = ""  # 预期难点(选填)


class ToggleItemRequest(BaseModel):
    learner_id: str = "demo_user"
    checked: bool

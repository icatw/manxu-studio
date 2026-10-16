# 领域模型

## 实体关系

```text
Project
  ├── StoryVersion
  ├── CharacterAsset ── AssetVersion
  ├── LocationAsset ─── AssetVersion
  └── Episode
        ├── StoryboardPanel
        │     ├── PanelVersion
        │     └── GenerationTask ── GeneratedAsset
        ├── Page（规划 proposed）
        │     └── PageSlot → PanelVersion
        └── LetteringObject（规划 proposed）
```

已交付实体支撑 L1（连载分镜/画格）。`Page` / `PageSlot` / `LetteringObject` 为成稿层规划对象，见 [路线图](../product/roadmap-complete-comic.md)；**未 confirmed 前不建表、不实现 API。**

## 实体

### Project

故事项目。字段包括 `id`、`title`、`synopsis`、`genre`、`art_style`、`aspect_ratio`、`status`、时间戳。

### StoryVersion

故事梗概/剧本的不可变修订。字段包括 `project_id`、`content`、`version`、`created_at`。项目可指向当前版本。

### CharacterAsset / LocationAsset

结构化角色或场景设定。字段包括 `project_id`、名称、描述、视觉特征、确认状态、当前版本引用。

### AssetVersion

角色/场景设定或参考图的修订。记录内容快照、参考图资产 ID、版本号和来源。已有分镜记录生成时引用的设定版本，不随设定更新而静默改变。

### Episode

项目中的故事单元。首版可以只有一个默认单元，但数据模型支持多个单元。字段包括 `project_id`、标题、摘要、排序和状态。

### StoryboardPanel

有序分镜。字段包括 `episode_id`、序号、场景引用、景别、角度、构图、动作、情绪、对白、剧情作用、提示词、审阅状态。

### PanelVersion

分镜内容与图像选择的版本快照，记录引用的故事/角色/场景版本以及人工修改和模型生成来源。

### GenerationTask

一次文本或图像生成任务。字段包括目标实体、任务类型、供应商、模型、输入快照、提示词版本、状态、错误摘要、开始/结束时间和产物引用。

### GeneratedAsset

生成或上传的文件元数据。保存对象存储键、MIME、尺寸、哈希、来源任务和创建时间；不把短时签名 URL 当作永久数据。

### Page / PageSlot（规划）

一话内有序「页」或条漫段落。槽位引用 `PanelVersion`（而非临时 URL）。重绘出新 PanelVersion 时，默认槽位可改挂新版本而保留页序与几何。

### LetteringObject（规划）

气泡、旁白等文字对象：文案、几何、样式持久化；归属 Page 或 Slot；与底图像分层。成稿导出时再栅格合成。对白真源以此为准，不以模型绘字为唯一来源。

## 生命周期

- 资产和分镜状态：`draft` → `in_review` → `approved`。
- 生成任务状态：`queued` → `running` → `succeeded` / `failed`（无 `cancelled`；见现行契约）。
- 失败可产生新的重试任务；历史任务和已生成资产保留。
- 用户确认某版本后，后续生成显式引用该版本。

## 一致性约束

- 同一 Episode 内分镜序号唯一且可重排。
- 项目内资产 ID 不能被其他项目的分镜引用。
- 一个生成任务只负责一个目标对象/操作，避免整页局部失败无法恢复。
- 当前版本变化不覆盖历史版本或历史任务输入快照。
- （规划）同一 Episode 内 Page 序号唯一；Slot 只引用本项目 PanelVersion；Lettering 不孤立于已删 Page。

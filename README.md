# SpoolCloud

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Donkie/SpoolCloud/assets/2332094/4e6e80ac-c7be-4ad2-9a33-dedc1b5ba30e">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/Donkie/SpoolCloud/assets/2332094/3c120b3a-1422-42f6-a16b-8d5a07c33000">
  <img alt="Icon of a filament spool" src="https://github.com/Donkie/SpoolCloud/assets/2332094/3c120b3a-1422-42f6-a16b-8d5a07c33000">
</picture>

<br/>

_高效管理您的 3D 打印耗材库存_

SpoolCloud 是一个基于 [Spoolman](https://github.com/Donkie/Spoolman) 开发的自托管 3D 打印耗材管理服务。在保留原版强大功能的基础上，我们增加了多用户支持、邀请码注册系统以及增强的通知功能，旨在为团队和个人用户提供更安全、更便捷的耗材管理体验。

它作为一个中心化的数据库，可以无缝集成 [OctoPrint](https://octoprint.org/) 和 [Klipper](https://www.klipper3d.org/)/[Moonraker](https://moonraker.readthedocs.io/en/latest/) 等主流 3D 打印软件。连接后，它会随着打印进度自动更新线盘重量，让您实时掌握耗材使用情况。

## ✨ 新增特性

SpoolCloud 在原版基础上增加了以下核心功能：

*   **👥 多用户系统**：完整的用户认证体系，支持用户注册、登录。
*   **🔑 邀请码注册**：内置邀请码系统，管理员可生成邀请码以控制用户注册，适合私有化部署。
*   **📢 增强通知系统**：
    *   支持多种通知渠道：**Server酱**、**Bark**、**Synology Chat**。
    *   **动态配置**：针对不同渠道提供专属配置界面（如 API Key, Device Key 等）。
    *   **一键测试**：配置页面内置测试按钮，确保通知服务正常工作。
*   **🛡️ 权限管理**：区分管理员和普通用户权限。

## 🚀 核心功能

*   **耗材管理**：全面记录耗材类型、制造商和单个线盘的信息。
*   **Bambu Lab 集成**：支持 Bambu Lab 耗材预设。
*   **API 集成**：提供完整的 REST API。
*   **实时更新**：通过 WebSocket 实时推送线盘更新。
*   **中央数据库**：自动同步 SpoolmanDB 的制造商和耗材数据。
*   **多数据库支持**：支持 SQLite, PostgreSQL, MySQL 和 CockroachDB。
*   **多打印机管理**：同时处理来自多台打印机的线盘更新。

## 📸 截图

**Web 客户端预览：**
![image](https://github.com/xxx/SpoolCloud/assets/xxx/xxx)

## �️ 快速开始

### 开发环境设置

#### 前置要求
- Python 3.11+
- Node.js 18+
- npm

#### 后端开发

```bash
# 安装依赖
pip install -e .

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
SPOOLCLOUD_ALLOW_REGISTRATION=true \
SPOOLCLOUD_DB_TYPE=sqlite \
SPOOLCLOUD_DB_URL=sqlite+aiosqlite:///spoolcloud.db \
uvicorn spoolcloud.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 前端开发

```bash
cd client

# 安装依赖
npm install

# 启动开发服务器
VITE_APIURL=/api/v1 npm run dev
```

前端访问地址：`http://localhost:5173`

#### 默认账号
首次启动后，您可以使用以下账号登录（如果已初始化）：
- **用户名**: `admin`
- **密码**: `admin`

## � 集成支持

SpoolCloud 支持与以下系统集成：
* [Moonraker](https://moonraker.readthedocs.io/en/latest/configuration/#spoolcloud) (Fluidd, KlipperScreen, Mainsail 等)
* OctoPrint
* OctoEverywhere
* Home Assistant

## 📄 许可证

本项目遵循 MIT 许可证。

---
*本项目基于 [Spoolman](https://github.com/Donkie/Spoolman) 二次开发。*

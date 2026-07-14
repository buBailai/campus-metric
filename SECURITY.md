# Security Policy

## Reporting a vulnerability

请不要在公开 Issue 中提交 API Key、账号密码、数据库、教师或学生信息、证书图片等敏感材料。

发现安全问题时，请通过 GitHub 仓库所有者的公开联系方式私下报告，并提供最小化的复现步骤。确认问题后会尽快发布修复版本和更新包。

## Deployment guidance

- 首次部署时创建独立管理员账号和高强度密码。
- 不要把 `.env`、`instance/`、`uploads/` 或备份目录提交到 Git。
- 学校正式部署应通过防火墙、反向代理或内网限制管理端访问。
- 使用 AI 能力前，应确认所选服务商的数据处理政策符合学校要求。

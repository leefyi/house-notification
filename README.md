# house-notification

深圳保租房/公租房公告监控。每日自动检查深圳市住建局网站新公告，通过 Bark 推送到 iPhone。

## 工作原理

1. GitHub Actions 每天 3 次（09:00 / 13:00 / 17:00 CST）自动运行
2. 抓取住建局通知公告页前 3 页
3. 关键词过滤保租房/公租房相关公告
4. 与缓存比对，发现新公告即推送
5. 无新公告时推送确认信息，网站异常时推送告警

## 快速开始

### 1. Fork 或 clone 本项目

### 2. 安装 Bark

iPhone 在 App Store 搜索 "Bark" 安装，打开后复制 device key。

### 3. 配置 Secret

到 repo `Settings > Secrets and variables > Actions` 添加：

| Secret | 值 |
|--------|-----|
| `BARK_DEVICE_KEY` | 你的 Bark device key |

### 4. 启用 Actions

到 repo `Actions` 页面启用 workflow，可手动 `Run workflow` 测试一次。

## 项目结构

```
.github/workflows/check.yml   # 定时任务
src/scraper.py                 # 爬虫主程序（纯 Python stdlib，无第三方依赖）
CONTEXT.md                     # 领域术语表
docs/adr/                      # 架构决策记录
```

## 关键词

监控公告标题包含以下关键词的公告：

- 保租房
- 公租房
- 认租
- 保障性租赁住房
- 公共租赁住房
- 配租

## 通知示例

**新公告：**
> 🏠 保租房/公租房新公告
> 深圳市住房保障署关于面向高层次人才配租保障性租赁住房有关事项的通告
> 26-04-24

**无新公告：**
> ✅ 住房监控正常
> 检查完毕，暂无新公告
> 13:00

**异常：**
> ⚠️ 住房监控异常
> 网站抓取失败: ...

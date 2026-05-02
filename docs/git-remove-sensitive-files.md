# Git 彻底删除敏感文件/目录的方法

## 问题背景

在开发过程中，不小心将包含敏感信息的文件或目录（如 `download/` 目录）提交并推送到了远程仓库。即使后续删除并提交，这些文件仍然存在于 Git 历史记录中，任何人都可以通过查看历史版本获取这些内容。

本文档记录如何**彻底从 Git 历史记录中删除**敏感文件或目录。

---

## ⚠️ 重要警告

**执行以下操作前，请务必备份本地文件！**

虽然 `--cached` 参数的理论作用是"只从 Git 索引中删除，保留本地文件"，但 `git filter-branch` 在重写历史时会将工作目录重置到新的提交状态，导致本地文件被删除。

特别是在执行清理命令（`git reflog expire` 和 `git gc --prune=now`）后，文件将从 Git 历史中**永久删除且不可恢复**。

**建议操作顺序**：
1. 先手动备份需要保留的文件到 Git 仓库之外的目录
2. 执行 filter 操作
3. 再将备份的文件复制回来（如果需要）

---

## 解决方案

### 方法一：git filter-branch（适用于提交数量较少的情况）

#### 1. 从所有历史记录中删除文件/目录

```bash
# 删除目录
git filter-branch --force --index-filter 'git rm -rf --cached --ignore-unmatch <目录名>' --prune-empty -- --all

# 删除单个文件
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch <文件路径>' --prune-empty -- --all
```

参数说明：
- `--force`：强制执行，覆盖备份
- `--index-filter`：指定要执行的命令
- `--cached`：只从索引中删除，保留本地文件
- `--ignore-unmatch`：如果文件不存在也不报错
- `--prune-empty`：删除空提交
- `-- --all`：应用到所有分支

#### 2. 添加到 .gitignore 防止再次提交

```bash
echo "<目录名>/" >> .gitignore
git add .gitignore
git commit -m "Add <目录名> to gitignore"
```

#### 3. 强制推送到远程仓库

```bash
git push --force
```

> ⚠️ **警告**：强制推送会重写远程历史，团队协作时需提前通知其他成员。

#### 4. 清理本地残留

```bash
# 删除 filter-branch 创建的备份引用
git for-each-ref --format='%(refname)' refs/original/ | xargs -n 1 git update-ref -d

# 过期所有 reflog
git reflog expire --expire=now --all

# 立即垃圾回收
git gc --prune=now --aggressive
```

---

### 方法二：git filter-repo（推荐，适用于大型仓库）

`git filter-repo` 是 `git filter-branch` 的现代替代品，速度更快、更安全。

#### 安装

```bash
# Windows (使用 pip)
pip install git-filter-repo

# macOS
brew install git-filter-repo

# Linux
pip install git-filter-repo
```

#### 使用

```bash
# 删除目录
git filter-repo --path <目录名> --invert-paths

# 删除文件
git filter-repo --path <文件路径> --invert-paths
```

#### 推送

```bash
git push --force
```

---

### 方法三：BFG Repo-Cleaner（适用于大型仓库）

BFG 是专门用于清理 Git 仓库的工具，速度非常快。

#### 下载

从 [BFG 官网](https://rtyley.github.io/bfg-repo-cleaner/) 下载 jar 文件。

#### 使用

```bash
# 删除目录
java -jar bfg.jar --delete-folders <目录名>

# 删除文件
java -jar bfg.jar --delete-files <文件名>

# 清理并推送
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

---

## 实际案例

### 问题描述
项目中不小心推送了 `download/` 目录，需要彻底删除。

### 执行步骤

```bash
# 1. 从历史记录中删除
git filter-branch --force --index-filter 'git rm -rf --cached --ignore-unmatch download' --prune-empty -- --all

# 2. 添加到 gitignore
echo "download/" >> .gitignore
git add .gitignore
git commit -m "Add download to gitignore"

# 3. 强制推送
git push --force

# 4. 清理本地残留
git for-each-ref --format='%(refname)' refs/original/ | xargs -n 1 git update-ref -d
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## 注意事项

### 1. 强制推送的影响

强制推送 (`--force`) 会重写远程仓库历史。如果有其他人已经 clone 了仓库，他们需要：

```bash
# 其他成员需要执行
git fetch origin
git reset --hard origin/main
```

或者重新 clone 仓库。

### 2. 敏感信息的后续处理

即使从 Git 历史中删除了敏感信息，仍然存在泄露风险：

- **GitHub 缓存**：GitHub 可能会缓存仓库快照，建议联系 GitHub 支持
- **Fork 仓库**：如果仓库被 Fork，其他仓库仍可能包含敏感信息
- **本地副本**：其他人的本地仓库仍有历史记录

**强烈建议**：
- 更换所有泄露的密钥、密码、令牌
- 如果泄露的是 API Key，立即撤销并重新生成

### 3. 预防措施

在 `.gitignore` 中添加常见的敏感文件：

```gitignore
# 敏感配置
.env
.env.local
*.pem
*.key
credentials.json

# 下载/临时文件
download/
temp/
tmp/
```

使用 Git Hooks 检查敏感信息：

```bash
# pre-commit hook 示例
#!/bin/sh
if git diff --cached --name-only | grep -E '\.env|\.pem|\.key'; then
    echo "ERROR: 检测到敏感文件，禁止提交"
    exit 1
fi
```

---

## 方法对比

| 方法 | 速度 | 安全性 | 适用场景 |
|------|------|--------|----------|
| git filter-branch | 慢 | 中等 | 提交数量少，简单场景 |
| git filter-repo | 快 | 高 | 推荐，大多数场景 |
| BFG Repo-Cleaner | 最快 | 高 | 大型仓库，批量删除 |

---

## 参考资料

- [git filter-branch 官方文档](https://git-scm.com/docs/git-filter-branch)
- [git filter-repo 官方仓库](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [GitHub: 从历史记录中删除敏感数据](https://docs.github.com/zh/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
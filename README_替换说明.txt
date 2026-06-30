这是一组 Windows 批处理脚本修复文件。

为什么要替换：
原始 .bat 文件中含有中文字符，并且部分中文字符位于 Windows CMD 预解析的括号代码块内。
在某些中文 Windows / 代码页环境中，CMD 会在切换到 UTF-8 之前错误解析这些字符，导致窗口一闪而过或报“命令语法不正确”。

如何替换：
1. 解压本压缩包。
2. 把里面所有 .bat 文件复制到 D:\cs2_spread_radar_v1。
3. Windows 提示“文件已存在，是否替换”时，选择“替换目标中的文件”。
4. 原有 .py、.env、data、logs、.venv 不要删除。
5. 先在命令行窗口中运行：
   init_catalog.bat
   这样可以保留报错信息。
6. 如果出现任何错误，复制终端从“Starting catalog initialization...”开始的完整内容。

说明：
这些 .bat 文件已改为 ASCII-only，并且直接调用 .venv\Scripts\python.exe，
不再依赖 activate.bat，也避免中文批处理解析问题。

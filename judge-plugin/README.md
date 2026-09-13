# judge-plugin —— 禁止选手自行控制优化等级的 GCC 插件

`no_opt_pragma.so` 会在编译期拦截以下两种写法，命中即**编译错误**（判题侧表现为 CE）：

- `#pragma GCC optimize ...`（含 `push_options` / `pop_options`）
- `__attribute__((optimize(...)))`

> 为什么不用正则扫描源码？因为选手可以用 `_Pragma("GCC optimize(\"O3\")")`
> 或宏拼接绕过文本匹配。本插件在 **GIMPLE pass** 中检查，此时预处理早已完成，
> 所有等价写法都会被归一化到同一个 `optimize` 属性上，无法绕过。

---

## 1. 构建（必须在评测服务器上执行）

插件头文件版本必须与**评测时实际调用的编译器**严格一致，因此禁止把别处编好的
`.so` 拷过来用。

```bash
# 1) 装与 g++ 同版本的插件开发头文件（把 14 换成你的实际版本）
sudo apt install -y g++-14 gcc-14-plugin-dev

# 2) 确认头文件目录存在
g++ -print-file-name=plugin      # 例如 /usr/lib/gcc/x86_64-linux-gnu/14/plugin

# 3) 构建
cd judge-plugin
make CXX=g++-14                  # 若评测用的就是系统默认 g++，直接 make 即可
```

产物：`no_opt_pragma.so`

## 2. 安装到沙箱可见的路径

go-judge 默认把宿主机的 `/usr`、`/lib`、`/bin` 等 bind mount 进沙箱，
所以放在 `/usr/local/...` 下即可被编译器直接访问，**不需要 `copyIn`**。

```bash
sudo install -d /usr/local/lib/oj
sudo install -m 0644 no_opt_pragma.so /usr/local/lib/oj/
```

## 3. 接入 judge.py

在 `service/app/services/judge.py` 的 `LANGUAGES` 里给 `cpp` 与 `c` 都加上
`-fplugin=<绝对路径>`：

```python
"compile": ["g++", "-O2", "-std=c++14",
            "-fplugin=/usr/local/lib/oj/no_opt_pragma.so",
            "main.cpp", "-o", "main"],
```

**C 语言也要加**——`#pragma GCC optimize` 在 C 里同样可用。

建议同时在 `service/app/core/config.py` 增加一项便于开关的配置，并在应用启动时
做一次探针编译：一旦插件加载失败就自动降级为不启用，避免「所有 C/C++ 提交全部
CE」的全站事故。

## 4. 验证

```bash
PLUG=/usr/local/lib/oj/no_opt_pragma.so

# 正常代码：应编译成功
printf '#include <cstdio>\nint main(){printf("hi\\n");}\n' > ok.cpp
g++ -O2 -fplugin=$PLUG ok.cpp -o /dev/null && echo PASS

# 应当报错：error: optimize attribute or pragma is not allowed
printf '#pragma GCC optimize("O3")\nint main(){return 0;}\n' > bad.cpp
g++ -O2 -fplugin=$PLUG bad.cpp -o /dev/null   # 期望非 0 退出码
```

判题侧验证：提交上述 `bad.cpp`，状态应为 `compile_error`，`error_message` 含
`optimize attribute or pragma is not allowed`。

## 5. 已知边界

| 项目 | 说明 |
|------|------|
| `#pragma GCC target(...)` / `__attribute__((target(...)))` | **不在拦截范围**。若要一并约束，可在编译命令固定微架构基线（如 `-march=x86-64`）或扩展本插件 |
| `-O0` 编译 | 实测同样生效，无需担心 |
| 兼容性 | 参考 pass 名为 `ssa`；GCC 11+ 的 `execute(function *)` 签名，GCC 14/16 均验证通过 |

## 6. 排错

| 现象 | 原因 |
|------|------|
| `cannot load plugin ... version mismatch` | `.so` 与当前 GCC 版本不符 → 在本机重新 `make` |
| 所有 C/C++ 提交突然全 CE | 插件路径在沙箱内不可见或文件缺失 → 用第 2 节路径重新安装 |
